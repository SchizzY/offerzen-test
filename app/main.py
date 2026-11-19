import asyncio
import contextlib
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from app import cache, cache_sync, stock_worker
from app.routers import events, health, orders, products
from app.schemas.event import OrderEventOut

logging.basicConfig(level=logging.INFO, format="%(levelname)s:     %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await cache.connect()
    tasks = [
        asyncio.create_task(cache_sync.run_forever()),
        asyncio.create_task(stock_worker.run_forever()),
    ]
    yield
    for task in tasks:
        task.cancel()
    for task in tasks:
        with contextlib.suppress(asyncio.CancelledError):
            await task
    await cache.disconnect()


app = FastAPI(
    title="OfferZen MRD API",
    description="Small consumer API",
    version="0.1.0",
    lifespan=lifespan,
    openapi_tags=[
        {"name": "orders", "description": "Create orders and check their status"},
        {"name": "products", "description": "Product stock levels"},
        {"name": "events", "description": "Order event feed for other systems (Server-Sent Events)"},
        {"name": "health", "description": "Service and dependency health"},
    ],
)

app.include_router(health.router)
app.include_router(orders.router)
app.include_router(products.router)
app.include_router(events.router)


def openapi_schema() -> dict:
    """FastAPI's schema, with SSE responses made valid OpenAPI 3.1.

    FastAPI describes SSE responses with `itemSchema`, an OpenAPI 3.2 keyword,
    inside a document it labels 3.1, so 3.1 validators and code generators reject
    it. Describe the stream as text instead (the example shows the wire format).
    """
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        tags=app.openapi_tags,
    )
    for path in schema.get("paths", {}).values():
        for operation in path.values():
            for response in operation.get("responses", {}).values():
                stream = response.get("content", {}).get("text/event-stream")
                if stream is not None and "itemSchema" in stream:
                    del stream["itemSchema"]
                    stream["schema"] = {
                        "type": "string",
                        "description": (
                            "Server-Sent Events; each event's `data` is an "
                            "[OrderEventOut](#/components/schemas/OrderEventOut) as JSON"
                        ),
                    }
    schema.setdefault("components", {}).setdefault("schemas", {})["OrderEventOut"] = (
        OrderEventOut.model_json_schema(ref_template="#/components/schemas/{model}")
    )
    app.openapi_schema = schema
    return schema


app.openapi = openapi_schema


if __name__ == "__main__":
    import uvicorn

    # Open event streams never end by themselves; close them on shutdown.
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True, timeout_graceful_shutdown=3)
