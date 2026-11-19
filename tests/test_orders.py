"""Orders intake: duplicates count once, no false 409s, prices fixed at order time."""

import threading
from concurrent.futures import ThreadPoolExecutor

from valkey import Valkey

from tests.conftest import TEST_VALKEY_URL
from tests.helpers import count_orders, order, place, set_price, wait_for_stock_worker


def test_concurrent_duplicates_count_once(client):
    """Unhappy path 1: the same order_ref submitted several times at once."""
    items = [{"sku": "BAN-001", "qty": 2}]
    submissions = 6
    barrier = threading.Barrier(submissions)

    def submit(_):
        barrier.wait()  # release every request at the same instant
        return place(client, "DUP-1", items).status_code

    with ThreadPoolExecutor(max_workers=submissions) as pool:
        codes = sorted(pool.map(submit, range(submissions)))

    assert codes == [201] + [409] * (submissions - 1)
    assert count_orders("DUP-1") == 1


def test_duplicate_with_different_body_is_still_rejected(client):
    assert place(client, "DUP-2", [{"sku": "BAN-001", "qty": 1}]).status_code == 201
    response = place(client, "DUP-2", [{"sku": "CHS-001", "qty": 5}])

    assert response.status_code == 409
    assert order("DUP-2").items[0]["sku"] == "BAN-001"  # the original is untouched


def test_stale_pending_claim_does_not_cause_a_false_409(client):
    """A request that crashed after claiming the ref in Valkey but before
    committing leaves a `pending` claim behind. That isn't proof the order
    exists, so a retry must succeed rather than get 409 for the claim's TTL."""
    Valkey.from_url(TEST_VALKEY_URL).set("order:CRASHED-1", "pending", ex=30)

    first = place(client, "CRASHED-1", [{"sku": "BAN-001", "qty": 1}])
    again = place(client, "CRASHED-1", [{"sku": "BAN-001", "qty": 1}])

    assert first.status_code == 201
    assert again.status_code == 409  # a real duplicate is still caught
    assert count_orders("CRASHED-1") == 1


def test_prices_are_fixed_at_order_time(client):
    response = place(client, "PRICE-1", [{"sku": "BAN-001", "qty": 2}])
    assert response.status_code == 201
    assert response.json()["items"][0]["unit_price_cents"] == 2499
    assert response.json()["total_cents"] == 4998
    wait_for_stock_worker()

    set_price("BAN-001", 9999)  # the price changes after the order

    later = client.get(f"/orders/{response.json()['id']}").json()
    assert later["items"][0]["unit_price_cents"] == 2499
    assert later["total_cents"] == 4998
    assert place(client, "PRICE-2", [{"sku": "BAN-001", "qty": 1}]).json()["total_cents"] == 9999
