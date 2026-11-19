"""A tiny "other system" that consumes the order event stream and prints it.

    poetry run python -m scripts.consume_orders                # resume where it left off
    poetry run python -m scripts.consume_orders --from-start   # replay everything
    poetry run python -m scripts.consume_orders --exit-after-idle 5

It reads GET /events/stream (Server-Sent Events) and saves the id of the last
event it handled to a cursor file, so stopping and restarting it neither misses
nor repeats events. If the connection drops it reconnects with Last-Event-ID.
Delivery is at-least-once, so events at or below the cursor are skipped.
"""

import argparse
import json
import os
import socket
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

API_URL = os.getenv("API_URL", f"http://127.0.0.1:{os.getenv('API_PORT', 8000)}").rstrip("/")
CURSOR_FILE = Path(__file__).resolve().parent.parent / ".order_consumer_cursor"


def load_cursor() -> int:
    try:
        return int(CURSOR_FILE.read_text().strip() or 0)
    except (FileNotFoundError, ValueError):
        return 0


def save_cursor(event_id: int) -> None:
    tmp = CURSOR_FILE.with_suffix(".tmp")
    tmp.write_text(str(event_id))
    tmp.replace(CURSOR_FILE)  # atomic: never a half-written cursor


def money(cents: int) -> str:
    return f"{cents / 100:,.2f}"


def describe(event_type: str, event: dict) -> str:
    p = event["payload"]
    ref = p.get("order_ref", "?")
    if event_type == "order_accepted":
        items = ", ".join(f"{i['qty']}x {i['sku']}" for i in p.get("items", []))
        return f"ACCEPTED   {ref:<24} customer {p.get('customer_id')}   {items}   total {money(p.get('total_cents', 0))}"
    if event_type == "order_fulfilled":
        items = ", ".join(f"{i.get('fulfilled_qty')}/{i['qty']} {i['sku']}" for i in p.get("items", []))
        return f"FULFILLED  {ref:<24} {p.get('status'):<20} supplied {items}   charged {money(p.get('total_cents', 0))}"
    return f"{event_type.upper():<10} {ref}"


class Consumer:
    """Holds the cursor so it stays current even when a read times out or the
    connection drops mid-stream (the next connect must resume from here)."""

    def __init__(self, cursor: int) -> None:
        self.cursor = cursor

    def handle(self, event_id: int, event_type: str, data: str) -> None:
        if event_id <= self.cursor:
            return  # already processed (at-least-once delivery)
        print(f"#{event_id:<5} {describe(event_type, json.loads(data))}", flush=True)
        save_cursor(event_id)
        self.cursor = event_id


def consume(consumer: Consumer, idle_timeout: float | None) -> None:
    """Read the stream until it ends, goes idle, or drops."""
    req = urllib.request.Request(
        f"{API_URL}/events/stream",
        headers={"Accept": "text/event-stream", "Last-Event-ID": str(consumer.cursor)},
    )
    # The server pings every 15s, so a read timeout above that means "dead";
    # with --exit-after-idle we use the (shorter) idle time instead.
    with urllib.request.urlopen(req, timeout=idle_timeout or 30) as resp:
        event_id, event_type, data = None, "message", []
        for raw in resp:
            line = raw.decode("utf-8").rstrip("\r\n")
            if line == "":  # blank line: dispatch the event
                if event_id is not None and data:
                    consumer.handle(int(event_id), event_type, "\n".join(data))
                event_id, event_type, data = None, "message", []
            elif line.startswith(":"):
                continue  # comment / keep-alive
            else:
                field, _, value = line.partition(":")
                value = value[1:] if value.startswith(" ") else value
                if field == "id":
                    event_id = value
                elif field == "event":
                    event_type = value
                elif field == "data":
                    data.append(value)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--from-start", action="store_true", help="ignore the saved cursor and replay everything")
    parser.add_argument("--exit-after-idle", type=float, metavar="SECONDS",
                        help="stop after this long with no events (default: run until Ctrl+C)")
    args = parser.parse_args()

    consumer = Consumer(0 if args.from_start else load_cursor())
    print(f"Consuming {API_URL}/events/stream after event #{consumer.cursor}  "
          f"(cursor file: {CURSOR_FILE.name})", flush=True)
    backoff = 1.0
    try:
        while True:
            try:
                consume(consumer, args.exit_after_idle)
                print(f"Stream closed by the server; reconnecting from #{consumer.cursor}", flush=True)
                backoff = 1.0
            except (socket.timeout, TimeoutError):
                if args.exit_after_idle:
                    print(f"No events for {args.exit_after_idle:g}s; stopping at event #{consumer.cursor}.")
                    return 0
            except (urllib.error.URLError, ConnectionError, OSError) as err:
                print(f"Stream unavailable ({err}); reconnecting in {backoff:g}s from #{consumer.cursor}", flush=True)
                time.sleep(backoff)
                backoff = min(backoff * 2, 10)
    except KeyboardInterrupt:
        print(f"\nStopped at event #{consumer.cursor}; next run resumes from there.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
