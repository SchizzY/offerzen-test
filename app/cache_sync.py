"""Keep Valkey in step with Postgres, which is the source of truth for orders.

Orders created while Valkey was down, or lost when Valkey restarts empty, are
copied back in once it is reachable again. Progress is a watermark (highest order
id copied) stored in Valkey itself: if Valkey loses its data, the watermark goes
with it and the next pass recopies everything.

Each pass re-checks a small window below the watermark, because ids are assigned
at insert but rows become visible at commit, so a lower id can commit just after
a higher one. Re-writing an order is idempotent, so overlap is harmless.
"""

import asyncio
import logging
import os

from fastapi.concurrency import run_in_threadpool
from sqlalchemy.exc import SQLAlchemyError

from app.cache import Valkey, get_valkey
from app.controllers.order_controller import ORDER_CACHE_TTL, CacheDown, order_cache_key
from app.db import SessionLocal
from app.resources.order_resource import OrderResource
from app.schemas.order import Order

logger = logging.getLogger(__name__)

SYNC_INTERVAL = float(os.getenv("CACHE_SYNC_INTERVAL", 5))
WATERMARK_KEY = "orders:cache_synced_through"
BATCH_SIZE = 500
LOOKBACK = 50


def _orders_after(after_id: int, limit: int) -> list[Order]:
    with SessionLocal() as session:
        rows = OrderResource(session).list_after(after_id, limit)
        return [Order.model_validate(row) for row in rows]


async def sync_once(cache: Valkey) -> int:
    """Copy orders above the watermark (minus LOOKBACK) into Valkey. Returns count."""
    watermark = int(await cache.get(WATERMARK_KEY) or 0)
    after = max(watermark - LOOKBACK, 0)
    copied = 0
    while True:
        orders = await run_in_threadpool(_orders_after, after, BATCH_SIZE)
        if not orders:
            break
        async with cache.pipeline(transaction=False) as pipe:
            for order in orders:
                pipe.set(order_cache_key(order.order_ref), order.model_dump_json(), ex=ORDER_CACHE_TTL)
            pipe.set(WATERMARK_KEY, max(watermark, orders[-1].id))
            await pipe.execute()
        after = orders[-1].id
        copied += sum(1 for order in orders if order.id > watermark)
    return copied


async def run_forever() -> None:
    cache_was_down = False
    while True:
        try:
            copied = await sync_once(get_valkey())
            if cache_was_down:
                logger.info("Valkey back; resynced %d orders from Postgres", copied)
            elif copied:
                logger.info("Synced %d orders into Valkey", copied)
            cache_was_down = False
        except CacheDown:
            if not cache_was_down:
                logger.warning("Valkey unreachable; cache sync paused, orders use Postgres")
            cache_was_down = True
        except SQLAlchemyError as err:
            logger.warning("Postgres unreachable; cache sync paused (%s)", err.__class__.__name__)
        except Exception:
            logger.exception("Cache sync pass failed")
        await asyncio.sleep(SYNC_INTERVAL)
