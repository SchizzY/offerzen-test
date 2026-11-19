"""In-process "something was appended to order_events" signal.

Only a wake-up hint for things that read the log (the stock worker, SSE
streams): they still read Postgres, and they also poll, so a missed signal
(e.g. another process wrote the event) only costs one poll interval.
"""

import asyncio

_waiters: set[asyncio.Future] = set()


def publish() -> None:
    """Wake everything currently waiting. Call from the event loop thread."""
    for waiter in list(_waiters):
        if not waiter.done():
            waiter.set_result(None)


async def wait(timeout: float) -> None:
    """Return on the next publish(), or after `timeout` seconds."""
    waiter = asyncio.get_running_loop().create_future()
    _waiters.add(waiter)
    try:
        await asyncio.wait_for(waiter, timeout)
    except TimeoutError:
        pass
    finally:
        _waiters.discard(waiter)
