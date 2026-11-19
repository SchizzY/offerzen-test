"""Control and inspect the stock worker.

    python -m scripts.stock_worker status          # paused? how far behind?
    python -m scripts.stock_worker pause           # stop applying stock (orders still accepted)
    python -m scripts.stock_worker resume          # catch up on the backlog
    python -m scripts.stock_worker wait [--timeout 30]   # block until caught up

The pause flag lives in Postgres, so it works across processes and restarts.
"""

import argparse
import sys
import time

from sqlalchemy import func, select

from app.db import SessionLocal
from app.models.event import ConsumerOffset
from app.models.order import Order
from app.stock_worker import CONSUMER, backlog, set_paused


def status() -> dict:
    with SessionLocal() as session:
        offset = session.get(ConsumerOffset, CONSUMER)
        pending = session.scalar(
            select(func.count()).select_from(Order).where(Order.status == "pending")
        )
        return {
            "paused": bool(offset and offset.paused),
            "last_event_id": offset.last_event_id if offset else 0,
            "backlog": backlog(session),
            "pending_orders": pending,
        }


def print_status(s: dict) -> None:
    state = "PAUSED" if s["paused"] else "running"
    print(f"Stock worker: {state}   applied through event #{s['last_event_id']}   "
          f"backlog: {s['backlog']} event(s)   pending orders: {s['pending_orders']}")


def wait(timeout: float) -> bool:
    """Wait until the worker has applied every event. False on timeout or if paused."""
    deadline = time.monotonic() + timeout
    while True:
        s = status()
        if s["backlog"] == 0:
            return True
        if s["paused"] or time.monotonic() >= deadline:
            return False
        time.sleep(0.25)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=["status", "pause", "resume", "wait"])
    parser.add_argument("--timeout", type=float, default=30)
    args = parser.parse_args()

    if args.command == "pause":
        set_paused(True)
        print("Stock worker paused: orders are still accepted, stock waits.")
    elif args.command == "resume":
        set_paused(False)
        print("Stock worker resumed: catching up.")
    elif args.command == "wait":
        caught_up = wait(args.timeout)
        print_status(status())
        return 0 if caught_up else 1
    print_status(status())
    return 0


if __name__ == "__main__":
    sys.exit(main())
