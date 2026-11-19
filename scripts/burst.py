"""Seed products, then fire a burst of concurrent orders, including duplicate order_refs.

    poetry run python -m scripts.burst            # against http://127.0.0.1:8000
    API_URL=http://host:8000 poetry run python -m scripts.burst

Every request is released at the same moment, so duplicates race each other.
Passes (exit 0) when each order_ref was created exactly once, every duplicate got
409, and - once the stock worker has caught up - stock went down by exactly what
was fulfilled for the created orders, and never below zero.
"""

import json
import os
import random
import sys
import threading
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor

from sqlalchemy import select

from app.db import SessionLocal
from app.models.order import Order
from app.models.product import Product
from app.seed import seed_products
from scripts.stock_worker import wait as wait_for_stock_worker

API_URL = os.getenv("API_URL", f"http://127.0.0.1:{os.getenv('API_PORT', 8000)}").rstrip("/")
RUN = f"BURST-{int(time.time())}"

# (order_ref suffix, items, times to send). Same ref + same body = client retry.
ORDERS = [
    ("A", [{"sku": "BAN-001", "qty": 2}, {"sku": "MLK-001", "qty": 1}], 3),
    ("B", [{"sku": "APL-001", "qty": 1}], 1),
    ("C", [{"sku": "EGG-001", "qty": 1}, {"sku": "BRD-001", "qty": 2}], 4),
    ("D", [{"sku": "COF-001", "qty": 1}], 1),
    ("E", [{"sku": "RCE-001", "qty": 1}], 2),  # no stock -> fulfilled 0, charged 0
    ("F", [{"sku": "AVO-001", "qty": 1}, {"sku": "AVO-001", "qty": 1}], 1),
]
# Same ref as A but a different body: must still be rejected, not merged.
CONFLICTING = ("A", [{"sku": "CHS-001", "qty": 5}])


def build_requests() -> list[tuple[str, list[dict]]]:
    reqs = [(f"{RUN}-{ref}", items) for ref, items, times in ORDERS for _ in range(times)]
    reqs.append((f"{RUN}-{CONFLICTING[0]}", CONFLICTING[1]))
    random.shuffle(reqs)
    return reqs


def post_order(order_ref: str, items: list[dict], barrier: threading.Barrier) -> tuple[int, dict]:
    body = json.dumps({"order_ref": order_ref, "customer_id": "burst", "items": items}).encode()
    req = urllib.request.Request(
        f"{API_URL}/orders", data=body, method="POST",
        headers={"content-type": "application/json"},
    )
    barrier.wait()
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.load(resp)
    except urllib.error.HTTPError as err:
        return err.code, json.loads(err.read() or b"{}")


def stock_levels() -> dict[str, int]:
    with SessionLocal() as session:
        return dict(session.execute(select(Product.sku, Product.stock)).all())


def main() -> int:
    try:
        urllib.request.urlopen(f"{API_URL}/health", timeout=5)
    except (urllib.error.URLError, OSError) as err:
        print(f"API not reachable at {API_URL}: {err}")
        return 1

    inserted = seed_products()
    print(f"Seeded products: {inserted} inserted, the rest already existed")

    reqs = build_requests()
    before = stock_levels()
    barrier = threading.Barrier(len(reqs))
    print(f"Firing {len(reqs)} requests at once ({len(ORDERS)} distinct order_refs, run {RUN})\n")

    with ThreadPoolExecutor(max_workers=len(reqs)) as pool:
        futures = [pool.submit(post_order, ref, items, barrier) for ref, items in reqs]
        results = [(ref, items, f.result()) for (ref, items), f in zip(reqs, futures)]

    by_ref: dict[str, list[int]] = defaultdict(list)
    for ref, items, (code, body) in results:
        by_ref[ref].append(code)
        detail = body.get("status") or body.get("detail")
        print(f"  {code}  {ref:<22} {detail}")

    if not wait_for_stock_worker(timeout=30):
        print("\nStock worker is paused or behind; stock checks skipped.")
        print("Run: python -m scripts.stock_worker resume")
        return 1
    after = stock_levels()

    created_refs = sorted({ref for ref, _, (code, _) in results if code == 201})
    expected_deduction: Counter[str] = Counter()
    with SessionLocal() as session:
        for order in session.scalars(select(Order).where(Order.order_ref.in_(created_refs))):
            print(f"  {order.order_ref:<22} -> {order.status}, charged {order.total_cents} cents")
            for line in order.items:
                expected_deduction[line["sku"]] += line["fulfilled_qty"] or 0

    print(f"\nStatus codes: {dict(Counter(code for _, _, (code, _) in results))}")
    failures = []
    for ref, codes in sorted(by_ref.items()):
        created, dupes = codes.count(201), codes.count(409)
        ok = created == 1 and dupes == len(codes) - 1
        print(f"  {'ok  ' if ok else 'FAIL'} {ref:<22} sent {len(codes)}, created {created}, 409 x{dupes}")
        if not ok:
            failures.append(ref)

    stock_failures = []
    for sku in sorted(set(before) | set(after)):
        actual = before.get(sku, 0) - after.get(sku, 0)
        if actual != expected_deduction[sku]:
            stock_failures.append(sku)
            print(f"  FAIL stock {sku}: deducted {actual}, expected {expected_deduction[sku]}")
    negative = sorted(sku for sku, stock in after.items() if stock < 0)
    if negative:
        stock_failures += negative
        print(f"  FAIL stock went negative: {negative}")
    if not stock_failures:
        print("  ok   stock deducted exactly once per created order, never below zero")
    failures += stock_failures

    print("\nPASS" if not failures else f"\nFAIL: {failures}")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
