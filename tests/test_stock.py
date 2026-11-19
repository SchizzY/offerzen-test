"""Stock: applied by the worker after acceptance, exactly once, never negative."""

import threading
import time

from sqlalchemy.orm import Session

from app.db import engine
from app.models.event import ORDER_ACCEPTED, append_event
from app.models.order import Order
from app.stock_worker import set_paused
from tests.helpers import event_types, order, place, stock, wait_for_stock_worker


def test_orders_accepted_while_stock_is_down_then_catch_up(client):
    """Unhappy path 2: the stock side is interrupted, then catches up."""
    bananas, milk = stock("BAN-001"), stock("MLK-001")

    set_paused(True)
    try:
        refs = [f"PAUSED-{n}" for n in range(3)]
        for ref in refs:
            response = place(client, ref, [{"sku": "BAN-001", "qty": 1}, {"sku": "MLK-001", "qty": 2}])
            assert response.status_code == 201
            assert response.json()["status"] == "pending"

        time.sleep(0.6)  # several poll intervals: a running worker would have acted
        assert [order(ref).status for ref in refs] == ["pending"] * 3
        assert (stock("BAN-001"), stock("MLK-001")) == (bananas, milk)
    finally:
        set_paused(False)

    wait_for_stock_worker()
    assert [order(ref).status for ref in refs] == ["confirmed"] * 3
    assert (stock("BAN-001"), stock("MLK-001")) == (bananas - 3, milk - 6)  # exactly once
    assert event_types(order(refs[0]).id) == ["order_accepted", "order_fulfilled"]


def test_short_stock_is_partially_fulfilled_and_never_negative(client):
    avocados = stock("AVO-001")
    place(client, "SHORT-1", [{"sku": "AVO-001", "qty": avocados + 5}, {"sku": "BAN-001", "qty": 1}])
    place(client, "SHORT-2", [{"sku": "RCE-001", "qty": 2}])  # none in stock
    wait_for_stock_worker()

    partial, none = order("SHORT-1"), order("SHORT-2")
    assert partial.status == "partially_fulfilled"
    assert [line["fulfilled_qty"] for line in partial.items] == [avocados, 1]
    assert partial.total_cents == avocados * 4499 + 2499  # charged only for what was supplied
    assert none.status == "unfulfilled"
    assert none.total_cents == 0
    assert stock("AVO-001") == 0 and stock("RCE-001") == 0

    assert client.get("/products/AVO-001/stock").json()["stock"] == 0
    assert client.get("/products/NOPE-001/stock").status_code == 404


def test_slow_writer_cannot_make_the_worker_skip_an_event(client):
    """Regression: event ids are assigned at insert but visible at commit, so
    without serialised appends a slow transaction's event could commit after a
    later one and be skipped forever (its order stuck `pending`)."""
    slow = Session(engine)
    slow_order = Order(
        order_ref="SLOW-1", customer_id="c1", total_cents=2499,
        items=[{"sku": "BAN-001", "qty": 1, "unit_price_cents": 2499, "line_total_cents": 2499}],
    )
    slow.add(slow_order)
    slow.flush()
    append_event(slow, slow_order.id, ORDER_ACCEPTED, {"order_ref": "SLOW-1"})  # holds the log lock

    fast = {}
    thread = threading.Thread(target=lambda: fast.update(response=place(client, "FAST-1", [{"sku": "BAN-001", "qty": 1}])))
    thread.start()
    time.sleep(0.5)
    assert thread.is_alive(), "the fast order must wait for the slow one to commit"

    slow.commit()
    slow.close()
    thread.join(timeout=10)
    assert fast["response"].status_code == 201

    wait_for_stock_worker()
    assert order("SLOW-1").status == "confirmed"
    assert order("FAST-1").status == "confirmed"
