import os
from collections.abc import AsyncIterator

from fastapi.concurrency import run_in_threadpool
from fastapi.sse import ServerSentEvent

from app import event_bus
from app.db import SessionLocal
from app.resources.event_resource import EventResource
from app.schemas.event import OrderEventOut

POLL_INTERVAL = float(os.getenv("EVENT_STREAM_POLL", 1))
BATCH_SIZE = 100
RETRY_MS = 2000


def _events_after(after_id: int) -> list[OrderEventOut]:
    # A short session per read: a stream can stay open for hours and must not
    # hold a database connection the whole time.
    with SessionLocal() as session:
        return [OrderEventOut.model_validate(e) for e in EventResource(session).list_after(after_id, BATCH_SIZE)]


class EventController:
    async def stream(self, after_id: int) -> AsyncIterator[ServerSentEvent]:
        """Every event after `after_id`, then new ones as they are appended.

        Catches up first (replaying history in batches), then waits for the next
        append (woken by event_bus, polling as a fallback). FastAPI sends keep-
        alive pings while idle and stops this generator when the client leaves.
        """
        cursor = after_id
        yield ServerSentEvent(comment=f"streaming order events after #{cursor}", retry=RETRY_MS)
        while True:
            events = await run_in_threadpool(_events_after, cursor)
            for event in events:
                yield ServerSentEvent(id=str(event.id), event=event.type, data=event)
                cursor = event.id
            if len(events) < BATCH_SIZE:
                await event_bus.wait(POLL_INTERVAL)
