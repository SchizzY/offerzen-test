"""Reset the local environment to a clean, seeded state for testing.

    poetry run python -m scripts.reset             # asks for confirmation
    poetry run python -m scripts.reset --yes       # no prompt
    poetry run python -m scripts.reset --dry-run   # show what would change

- Deletes every order and order event, restarts ids at 1, and rewinds every
  consumer (the stock worker) to the start, unpaused.
- Restores products to exactly the seed list (stock and prices); removes extras.
- Deletes the example consumer's cursor file (event ids restart too).
- Deletes order:* keys and the cache-sync watermark from Valkey, so cached
  order_refs don't cause 409s and the sync loop starts over from id 1.

Refuses to run unless DATABASE_URL points at localhost.
"""

import argparse
import asyncio
import sys

from sqlalchemy import delete, func, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import make_url

from app.cache import VALKEY_URL, valkey_client
from app.cache_sync import WATERMARK_KEY
from app.controllers.order_controller import order_cache_key
from app.db import DATABASE_URL, SessionLocal
from app.models.order import Order
from app.models.product import Product
from app.seed import PRODUCTS
from scripts.consume_orders import CURSOR_FILE

LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}
ORDER_KEY_PATTERN = order_cache_key("*")


def check_local() -> None:
    host = make_url(DATABASE_URL).host
    if host not in LOCAL_HOSTS:
        sys.exit(f"Refusing to reset: DATABASE_URL host is {host!r}, not local.")


async def order_keys() -> list[str]:
    async with valkey_client() as cache:
        keys = [key async for key in cache.scan_iter(match=ORDER_KEY_PATTERN, count=500)]
        return keys + ([WATERMARK_KEY] if await cache.exists(WATERMARK_KEY) else [])


async def delete_keys(keys: list[str]) -> int:
    if not keys:
        return 0
    async with valkey_client() as cache:
        return await cache.delete(*keys)


def reset_database() -> tuple[int, int]:
    seed_skus = [p["sku"] for p in PRODUCTS]
    with SessionLocal() as session:
        # Lock the consumers' offsets FIRST: the stock worker locks its offset
        # row and then reads orders/order_events, so taking the locks in the
        # same order (rather than truncating first) can't deadlock with it.
        session.execute(
            text("UPDATE consumer_offsets SET last_event_id = 0, paused = false")
        )
        orders = session.scalar(select(func.count()).select_from(Order))
        session.execute(text("TRUNCATE orders, order_events RESTART IDENTITY"))
        removed = session.execute(
            delete(Product).where(Product.sku.not_in(seed_skus))
        ).rowcount
        stmt = insert(Product).values(PRODUCTS)
        session.execute(
            stmt.on_conflict_do_update(
                index_elements=["sku"],
                set_={
                    "name": stmt.excluded.name,
                    "price_cents": stmt.excluded.price_cents,
                    "stock": stmt.excluded.stock,
                },
            )
        )
        session.commit()
    return orders, removed


def describe() -> None:
    seed = {p["sku"]: p for p in PRODUCTS}
    with SessionLocal() as session:
        orders = session.scalar(select(func.count()).select_from(Order))
        products = session.execute(select(Product.sku, Product.stock, Product.price_cents)).all()
    print(f"Orders to delete: {orders}")
    for sku, stock, price in sorted(products):
        target = seed.get(sku)
        if target is None:
            print(f"  {sku}: not in seed list, would be removed")
        else:
            changes = [
                f"{field} {old} -> {target[key]}"
                for field, key, old in (("stock", "stock", stock), ("price", "price_cents", price))
                if old != target[key]
            ]
            if changes:
                print(f"  {sku}: {', '.join(changes)}")
    missing = set(seed) - {sku for sku, _, _ in products}
    for sku in sorted(missing):
        print(f"  {sku}: missing, would be inserted")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--yes", action="store_true", help="skip the confirmation prompt")
    parser.add_argument("--dry-run", action="store_true", help="show what would change, change nothing")
    args = parser.parse_args()

    check_local()
    db = make_url(DATABASE_URL)
    print(f"Database: {db.host}:{db.port}/{db.database}   Valkey: {VALKEY_URL}")

    keys = asyncio.run(order_keys())
    if args.dry_run:
        describe()
        print(f"Valkey keys to delete: {len(keys)}")
        return

    if not args.yes and input("Delete all orders and reset products? [y/N] ").strip().lower() != "y":
        sys.exit("Aborted.")

    orders, removed = reset_database()
    CURSOR_FILE.unlink(missing_ok=True)  # event ids restart at 1
    deleted = asyncio.run(delete_keys(keys))
    print(f"Deleted {orders} orders (ids restart at 1)")
    print(f"Restored {len(PRODUCTS)} products to seed stock and prices; removed {removed} extra")
    print(f"Deleted {deleted} order keys from Valkey")
    print("Cleared the example consumer's cursor")


if __name__ == "__main__":
    main()
