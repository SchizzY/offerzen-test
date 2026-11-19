"""Stock worker: applies accepted orders to stock, from the order_events log.

Intake only records an order and its order_accepted event; this worker does the
stock side afterwards, so orders are accepted even while stock is paused or
failing. It reads events in id order (first come, first served) from its saved
position in consumer_offsets, and for each order, in ONE transaction:

    - locks the order and its products (products in SKU order: no deadlocks)
    - fulfils each line with what is on the shelf: min(requested, available)
    - deducts exactly that, so stock never goes negative
    - prices the order on what was fulfilled and sets its status
    - appends an order_fulfilled event for consumers
    - advances its offset past the event

Because the deduction and the offset move together, an event is applied exactly
once: a crash before commit leaves both untouched and the event is retried.

Pausing (consumer_offsets.paused) simulates the stock side being unavailable.
Events queue up meanwhile; on resume the worker works through the backlog.
"""

import logging
import os
from typing import Literal

from fastapi.concurrency import run_in_threadpool
from sqlalchemy import func, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app import event_bus
from app.db import SessionLocal
from app.models.event import ORDER_ACCEPTED, ORDER_FULFILLED, ConsumerOffset, OrderEvent, append_event
from app.models.order import Order
from app.models.product import Product

logger = logging.getLogger(__name__)

CONSUMER = "stock"
POLL_INTERVAL = float(os.getenv("STOCK_WORKER_POLL", 1))

def _fulfil(session: Session, order_id: int) -> None:
    order = session.get(Order, order_id, with_for_update=True)
    if order is None or order.status != "pending":
        return  # deleted, or already fulfilled: nothing to do

    skus = sorted({line["sku"] for line in order.items})
    stock = dict(
        session.execute(
            select(Product.sku, Product.stock)
            .where(Product.sku.in_(skus))
            .order_by(Product.sku)
            .with_for_update()
        ).all()
    )
    before = dict(stock)

    lines = []
    for line in order.items:
        fulfilled = min(line["qty"], max(stock.get(line["sku"], 0), 0))
        stock[line["sku"]] = stock.get(line["sku"], 0) - fulfilled
        lines.append(
            {**line, "fulfilled_qty": fulfilled, "line_total_cents": line["unit_price_cents"] * fulfilled}
        )

    for sku in skus:
        if sku in stock and stock[sku] != before.get(sku):
            session.execute(update(Product).where(Product.sku == sku).values(stock=stock[sku]))

    requested = sum(line["qty"] for line in lines)
    fulfilled = sum(line["fulfilled_qty"] for line in lines)
    order.items = lines
    order.total_cents = sum(line["line_total_cents"] for line in lines)
    order.status = (
        "confirmed" if fulfilled == requested
        else "unfulfilled" if fulfilled == 0
        else "partially_fulfilled"
    )
    if order.status != "confirmed":
        short = {l["sku"]: l["qty"] - l["fulfilled_qty"] for l in lines if l["fulfilled_qty"] < l["qty"]}
        logger.info("Order %s %s; short: %s", order.order_ref, order.status, short)

    # Tell consumers what was actually supplied and charged, in the same
    # transaction as the stock change.
    append_event(
        session,
        order.id,
        ORDER_FULFILLED,
        {
            "order_id": order.id,
            "order_ref": order.order_ref,
            "customer_id": order.customer_id,
            "status": order.status,
            "items": lines,
            "total_cents": order.total_cents,
        },
    )


def process_next() -> int | Literal["paused", "idle"]:
    """Apply the next event. Returns its id, or 'paused' / 'idle'."""
    with SessionLocal() as session:
        offset = session.scalar(
            select(ConsumerOffset).where(ConsumerOffset.consumer == CONSUMER).with_for_update()
        )
        if offset is None:
            offset = ConsumerOffset(consumer=CONSUMER, last_event_id=0, paused=False)
            session.add(offset)
            session.flush()
        if offset.paused:
            return "paused"

        event = session.scalar(
            select(OrderEvent)
            .where(OrderEvent.id > offset.last_event_id)
            .order_by(OrderEvent.id)
            .limit(1)
        )
        if event is None:
            session.commit()
            return "idle"

        if event.type == ORDER_ACCEPTED:
            _fulfil(session, event.order_id)
        offset.last_event_id = event.id
        session.commit()
        return event.id


def backlog(session: Session) -> int:
    """Events the stock worker hasn't applied yet."""
    last = session.scalar(
        select(ConsumerOffset.last_event_id).where(ConsumerOffset.consumer == CONSUMER)
    ) or 0
    return session.scalar(select(func.count()).select_from(OrderEvent).where(OrderEvent.id > last))


def set_paused(paused: bool) -> None:
    with SessionLocal() as session:
        offset = session.get(ConsumerOffset, CONSUMER)
        if offset is None:
            session.add(ConsumerOffset(consumer=CONSUMER, last_event_id=0, paused=paused))
        else:
            offset.paused = paused
        session.commit()


async def run_forever() -> None:
    was_paused = False
    while True:
        try:
            applied = 0
            while True:
                result = await run_in_threadpool(process_next)
                if isinstance(result, int):
                    applied += 1
                    continue
                if result == "paused" and not was_paused:
                    logger.warning("Stock worker paused; orders are queued in order_events")
                if result != "paused" and was_paused:
                    logger.info("Stock worker resumed")
                was_paused = result == "paused"
                break
            if applied:
                logger.info("Stock worker applied %d event(s)", applied)
                event_bus.publish()  # order_fulfilled events for SSE streams
        except SQLAlchemyError as err:
            logger.warning("Stock worker: Postgres unavailable (%s); retrying", err.__class__.__name__)
        except Exception:
            logger.exception("Stock worker pass failed")
        await event_bus.wait(POLL_INTERVAL)
