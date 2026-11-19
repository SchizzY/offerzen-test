import base64
import binascii
import json
import logging
import os

from fastapi import Depends, HTTPException, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.exc import IntegrityError

from app import event_bus
from app.cache import Valkey, ValkeyError, get_valkey
from app.models.order import Order as OrderModel
from app.resources.order_resource import OrderResource
from app.resources.product_resource import ProductResource
from app.schemas.order import Order, OrderCreate, OrderPage, OrderStatus

logger = logging.getLogger(__name__)

PENDING_TTL = int(os.getenv("ORDER_PENDING_TTL", 30))
ORDER_CACHE_TTL = int(os.getenv("ORDER_CACHE_TTL", 60 * 60 * 24 * 7))

if not 0 < PENDING_TTL < ORDER_CACHE_TTL:
    raise ValueError("ORDER_CACHE_TTL must be longer than ORDER_PENDING_TTL, both > 0")

CacheDown = (ValkeyError, OSError)


def order_cache_key(order_ref: str) -> str:
    return f"order:{order_ref}"


def encode_cursor(order_id: int) -> str:
    raw = json.dumps({"id": order_id}, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def decode_cursor(cursor: str) -> int:
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        order_id = json.loads(base64.urlsafe_b64decode(padded))["id"]
    except (binascii.Error, ValueError, TypeError, KeyError):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid cursor") from None
    if not isinstance(order_id, int) or isinstance(order_id, bool) or order_id < 1:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid cursor")
    return order_id


class OrderController:
    def __init__(
        self,
        resource: OrderResource = Depends(),
        products: ProductResource = Depends(),
        cache: Valkey = Depends(get_valkey),
    ) -> None:
        self.resource = resource
        self.products = products
        self.cache = cache

    @staticmethod
    def _quantities(data: OrderCreate) -> dict[str, int]:
        totals: dict[str, int] = {}
        for item in data.items:
            totals[item.sku] = totals.get(item.sku, 0) + item.qty
        return totals

    @staticmethod
    def _price_lines(data: OrderCreate, prices: dict[str, float]) -> tuple[list[dict], int]:
        lines = []
        for item in data.items:
            unit = round(prices[item.sku])
            lines.append(
                {**item.model_dump(), "unit_price_cents": unit, "line_total_cents": unit * item.qty}
            )
        return lines, sum(line["line_total_cents"] for line in lines)

    async def create_order(self, data: OrderCreate) -> Order:
        """Valkey is checked first as a fast path; Postgres is the source of truth.

        1. Claim order_ref in Valkey (SET NX). Taken -> 409 without touching the DB.
           Valkey down -> skip the claim and carry on.
        2. Check Postgres for the ref. Found -> backfill Valkey, 409.
        3. Insert the order and its order_accepted event. The unique constraint on order_ref settles any race that got
           past 1 and 2 (e.g. while Valkey was down): the loser rolls back -> 409.
        4. Commit, wake the stock worker, then write the order to Valkey. A failed
           cache write is logged and left to the sync loop; it never fails the order.
        """
        key = order_cache_key(data.order_ref)

        claimed = await self._claim(key)
        if claimed is False:
            raise self._already_exists(data.order_ref)

        try:
            existing = await run_in_threadpool(self.resource.get_by_ref, data.order_ref)
            if existing is not None:
                await self._try_cache(Order.model_validate(existing), ORDER_CACHE_TTL)
                raise self._already_exists(data.order_ref)
            quantities = self._quantities(data)
            prices = await run_in_threadpool(self.products.prices, set(quantities))
            unknown = sorted(set(quantities) - set(prices))
            if unknown:
                await run_in_threadpool(self.resource.rollback)
                await self._release(key, claimed)
                raise HTTPException(
                    status.HTTP_422_UNPROCESSABLE_CONTENT,
                    f"Unknown SKU(s): {', '.join(unknown)}",
                )
            lines, total_cents = self._price_lines(data, prices)
            # Order + order_accepted event in one transaction. Stock is NOT touched
            # here: the stock worker applies it from the event, so orders are
            # accepted even while stock is paused or unavailable.
            staged = await run_in_threadpool(self.resource.stage, data, lines, total_cents)
            order = Order.model_validate(staged)
            await run_in_threadpool(self.resource.commit)
        except IntegrityError:
            await run_in_threadpool(self.resource.rollback)
            await self._backfill_ref(data.order_ref)
            raise self._already_exists(data.order_ref) from None
        except HTTPException:
            raise
        except Exception:
            await run_in_threadpool(self.resource.rollback)
            await self._release(key, claimed)
            raise

        event_bus.publish()
        await self._try_cache(order, ORDER_CACHE_TTL)
        return order

    async def list_orders(self, cursor: str | None, limit: int) -> OrderPage:
        before_id = decode_cursor(cursor) if cursor else None
        rows = await run_in_threadpool(self.resource.list_page, before_id, limit + 1)
        page, has_more = rows[:limit], len(rows) > limit
        return OrderPage(
            items=[Order.model_validate(row) for row in page],
            next_cursor=encode_cursor(page[-1].id) if has_more else None,
        )

    async def get_order(self, order_id: int) -> Order:
        return Order.model_validate(await self._get_or_404(order_id))

    async def get_status(self, order_id: int) -> OrderStatus:
        return OrderStatus.model_validate(await self._get_or_404(order_id))

    async def _get_or_404(self, order_id: int) -> OrderModel:
        order = await run_in_threadpool(self.resource.get, order_id)
        if order is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Order {order_id} not found")
        return order

    async def _try_cache(self, order: Order, ttl: int) -> None:
        try:
            await self.cache.set(order_cache_key(order.order_ref), order.model_dump_json(), ex=ttl)
        except CacheDown:
            logger.warning("Could not cache order %s", order.order_ref)

    async def _claim(self, key: str) -> bool | None:
        """True = claimed, False = already taken, None = Valkey down (fall back to DB)."""
        try:
            return bool(await self.cache.set(key, "pending", nx=True, ex=PENDING_TTL))
        except CacheDown:
            logger.warning("Valkey down; deduplicating %s against Postgres only", key)
            return None

    async def _release(self, key: str, claimed: bool | None) -> None:
        if not claimed:
            return
        try:
            await self.cache.delete(key)
        except CacheDown:
            logger.warning("Could not release %s; it expires in %ss", key, PENDING_TTL)

    async def _backfill_ref(self, order_ref: str) -> None:
        existing = await run_in_threadpool(self.resource.get_by_ref, order_ref)
        if existing is not None:
            await self._try_cache(Order.model_validate(existing), ORDER_CACHE_TTL)

    @staticmethod
    def _already_exists(order_ref: str) -> HTTPException:
        return HTTPException(status.HTTP_409_CONFLICT, f"Order {order_ref!r} already exists")
