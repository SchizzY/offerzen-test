from collections.abc import AsyncIterable
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query
from fastapi.sse import EventSourceResponse, ServerSentEvent

from app.controllers.event_controller import EventController

router = APIRouter(prefix="/events", tags=["events"])

STREAM_EXAMPLE = (
    "id: 17\n"
    "event: order_accepted\n"
    'data: {"id":17,"type":"order_accepted","order_id":9,"payload":{"order_id":9,'
    '"order_ref":"ORD-1001","customer_id":"c1","items":[{"sku":"BAN-001","qty":2,'
    '"unit_price_cents":2499,"line_total_cents":4998}],"total_cents":4998},'
    '"created_at":"2026-11-19T09:30:00Z"}\n\n'
    "id: 18\n"
    "event: order_fulfilled\n"
    'data: {"id":18,"type":"order_fulfilled","order_id":9,"payload":{"order_id":9,'
    '"order_ref":"ORD-1001","status":"confirmed","items":[{"sku":"BAN-001","qty":2,'
    '"fulfilled_qty":2,"unit_price_cents":2499,"line_total_cents":4998}],'
    '"total_cents":4998},"created_at":"2026-11-19T09:30:00Z"}\n\n'
)


@router.get(
    "/stream",
    response_class=EventSourceResponse,
    operation_id="streamOrderEvents",
    summary="Stream order events (Server-Sent Events)",
    description=(
        "An append-only feed of order events, in order, as Server-Sent Events.\n\n"
        "- `order_accepted`: an order was accepted (what was ordered, at what price).\n"
        "- `order_fulfilled`: the stock worker processed it (what was supplied and charged).\n\n"
        "Replays every event after `after` (default: from the start), then stays "
        "open and sends new events as they happen. Each event's `id` is its log "
        "position: reconnect with the `Last-Event-ID` header (browsers do this "
        "automatically) or `?after=<id>` to resume without gaps. Delivery is "
        "at-least-once, so ignore ids you have already processed.\n\n"
        "Try it: `curl -N localhost:8000/events/stream`"
    ),
    responses={200: {"content": {"text/event-stream": {"example": STREAM_EXAMPLE}}}},
)
async def stream_order_events(
    after: Annotated[int, Query(ge=0, description="Replay events after this id (0 = everything)")] = 0,
    last_event_id: Annotated[
        int | None, Header(alias="Last-Event-ID", ge=0, description="Sent by SSE clients on reconnect")
    ] = None,
    controller: EventController = Depends(),
) -> AsyncIterable[ServerSentEvent]:
    async for event in controller.stream(max(after, last_event_id or 0)):
        yield event
