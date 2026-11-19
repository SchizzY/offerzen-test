"""Unhappy path 2: the stock side is interrupted, orders keep coming, stock catches up.

    poetry run python -m scripts.stock_outage          # API must be running

1. Pause the stock worker (the stock side "goes down").
2. Submit orders: everyday ones, rice (none in stock), and more avocados than
   are left.
3. Check: every order accepted (201), all still pending, stock untouched, and
   the backlog holds them.
4. Resume the worker and wait for it to catch up.
5. Check: backlog empty, and every order's status, supplied quantities, charge
   and the stock levels match a first-come-first-served replay of the orders
   against the starting stock. Nothing missed, nothing twice, nothing below 0.

The worker is always resumed at the end, even if a check fails.
Exit 0 on PASS, 1 on FAIL.
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request

from sqlalchemy import select

from app.db import SessionLocal
from app.models.order import Order
from app.models.product import Product
from app.stock_worker import set_paused
from scripts.stock_worker import status as worker_status
from scripts.stock_worker import wait as wait_for_worker

API_URL = os.getenv("API_URL", f"http://127.0.0.1:{os.getenv('API_PORT', 8000)}").rstrip("/")
RUN = f"OUTAGE-{int(time.time())}"
QUIET_PERIOD = 2.0  # seconds to give a (wrongly) running worker the chance to act

failures: list[str] = []


def check(ok: bool, message: str) -> None:
    print(f"  {'ok  ' if ok else 'FAIL'} {message}")
    if not ok:
        failures.append(message)


def stock_levels() -> dict[str, int]:
    with SessionLocal() as session:
        return dict(session.execute(select(Product.sku, Product.stock)).all())


def post_order(order_ref: str, items: list[dict]) -> tuple[int, dict]:
    body = json.dumps({"order_ref": order_ref, "customer_id": "outage", "items": items}).encode()
    req = urllib.request.Request(
        f"{API_URL}/orders", data=body, method="POST",
        headers={"content-type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, json.load(resp)
    except urllib.error.HTTPError as err:
        return err.code, json.loads(err.read() or b"{}")


def build_orders(stock: dict[str, int]) -> list[tuple[str, list[dict]]]:
    avocados_left = max(stock.get("AVO-001", 0), 0)
    return [
        (f"{RUN}-1", [{"sku": "BAN-001", "qty": 2}, {"sku": "MLK-001", "qty": 1}]),
        (f"{RUN}-2", [{"sku": "BRD-001", "qty": 1}, {"sku": "EGG-001", "qty": 1}]),
        (f"{RUN}-3", [{"sku": "RCE-001", "qty": 2}]),  # none in stock
        (f"{RUN}-4", [{"sku": "AVO-001", "qty": avocados_left + 5}, {"sku": "BAN-001", "qty": 1}]),
        (f"{RUN}-5", [{"sku": "COF-001", "qty": 1}]),
    ]


def replay(orders: list[tuple[str, list[dict]]], stock: dict[str, int], prices: dict[str, int]):
    """What the worker should do: first come, first served, never below zero."""
    shelf = {sku: max(units, 0) for sku, units in stock.items()}
    deducted: dict[str, int] = {}
    expected = {}
    for ref, items in orders:
        lines = []
        for item in items:
            supplied = min(item["qty"], shelf.get(item["sku"], 0))
            shelf[item["sku"]] = shelf.get(item["sku"], 0) - supplied
            deducted[item["sku"]] = deducted.get(item["sku"], 0) + supplied
            lines.append((item["sku"], item["qty"], supplied))
        requested = sum(q for _, q, _ in lines)
        supplied = sum(s for _, _, s in lines)
        expected[ref] = {
            "status": "confirmed" if supplied == requested
            else "unfulfilled" if supplied == 0 else "partially_fulfilled",
            "supplied": [s for _, _, s in lines],
            "charged": sum(prices[sku] * s for sku, _, s in lines),
        }
    return expected, deducted


def main() -> int:
    try:
        urllib.request.urlopen(f"{API_URL}/health", timeout=5)
    except (urllib.error.URLError, OSError) as err:
        print(f"API not reachable at {API_URL}: {err}")
        return 1

    # Start from a quiet worker so earlier orders can't interfere.
    set_paused(False)
    if not wait_for_worker(timeout=30):
        print("Stock worker didn't drain its backlog before the test; aborting.")
        return 1

    before = stock_levels()
    with SessionLocal() as session:
        prices = dict(session.execute(select(Product.sku, Product.price_cents)).all())
    orders = build_orders(before)
    expected, deducted = replay(orders, before, prices)

    try:
        print("\n1. Stock side goes down (worker paused)")
        set_paused(True)
        s = worker_status()
        check(s["paused"], "stock worker is paused")

        print(f"\n2. Submitting {len(orders)} orders while stock is down")
        created = {}
        for ref, items in orders:
            code, body = post_order(ref, items)
            created[ref] = body.get("id")
            summary = ", ".join(f"{i['qty']}x {i['sku']}" for i in items)
            print(f"  {code}  {ref:<20} {body.get('status') or body.get('detail')}   ({summary})")
            check(code == 201, f"{ref} accepted")

        time.sleep(QUIET_PERIOD)
        print(f"\n3. During the outage ({QUIET_PERIOD:g}s later)")
        with SessionLocal() as session:
            statuses = dict(session.execute(
                select(Order.order_ref, Order.status).where(Order.order_ref.like(f"{RUN}-%"))
            ).all())
        check(all(st == "pending" for st in statuses.values()) and len(statuses) == len(orders),
              f"all {len(orders)} orders still pending: {sorted(set(statuses.values()))}")
        during = stock_levels()
        check(during == before, "stock untouched while the worker is paused")
        s = worker_status()
        check(s["backlog"] == len(orders), f"backlog holds the orders: {s['backlog']} event(s) waiting")

        print("\n4. Stock side comes back (worker resumed)")
        set_paused(False)
        started = time.monotonic()
        caught_up = wait_for_worker(timeout=30)
        check(caught_up, f"caught up in {time.monotonic() - started:.2f}s, backlog 0")
    finally:
        set_paused(False)  # never leave stock paused

    print("\n5. After catch-up")
    with SessionLocal() as session:
        rows = {o.order_ref: o for o in session.scalars(select(Order).where(Order.order_ref.like(f"{RUN}-%")))}
    for ref, _ in orders:
        order, want = rows.get(ref), expected[ref]
        if order is None:
            check(False, f"{ref} exists")
            continue
        supplied = [line["fulfilled_qty"] for line in order.items]
        ok = order.status == want["status"] and supplied == want["supplied"] and order.total_cents == want["charged"]
        check(ok, f"{ref:<20} {order.status:<20} supplied {supplied}, charged {order.total_cents} cents")

    after = stock_levels()
    changed = sorted(sku for sku in before if before[sku] != after.get(sku))
    for sku in changed:
        print(f"       {sku}: {before[sku]} -> {after[sku]}")
    check(all(after.get(sku) == before[sku] - deducted.get(sku, 0) for sku in before),
          "stock went down by exactly what was supplied (nothing missed, nothing twice)")
    check(all(units >= 0 for units in after.values()), "no stock below zero")

    print("\nPASS" if not failures else f"\nFAIL ({len(failures)} check(s) failed)")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
