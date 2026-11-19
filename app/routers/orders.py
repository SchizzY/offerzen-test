from typing import Annotated

from fastapi import APIRouter, Body, Depends, Query, status
from fastapi.openapi.models import Example

from app.controllers.order_controller import OrderController
from app.schemas.common import ErrorResponse
from app.schemas.order import Order, OrderCreate, OrderPage, OrderStatus

router = APIRouter(prefix="/orders", tags=["orders"])

CREATE_EXAMPLES: dict[str, Example] = {
    "basket": {
        "summary": "Everyday basket",
        "description": "All items in stock; the order is created as `pending`.",
        "value": {
            "order_ref": "ORD-1001",
            "customer_id": "c1",
            "items": [
                {"sku": "BAN-001", "qty": 2},
                {"sku": "MLK-001", "qty": 1},
                {"sku": "BRD-001", "qty": 1},
                {"sku": "EGG-001", "qty": 1},
            ],
        },
    },
    "single": {
        "summary": "Single item",
        "value": {
            "order_ref": "ORD-1002",
            "customer_id": "c2",
            "items": [{"sku": "COF-001", "qty": 1}],
        },
    },
    "out_of_stock": {
        "summary": "Out-of-stock item",
        "description": (
            "Basmati rice has no stock: the order is accepted, then the stock worker "
            "fulfils 0, charges 0 and marks it `unfulfilled`."
        ),
        "value": {
            "order_ref": "ORD-1003",
            "customer_id": "c1",
            "items": [{"sku": "RCE-001", "qty": 2}],
        },
    },
    "unknown_sku": {
        "summary": "Unknown SKU (422)",
        "value": {
            "order_ref": "ORD-1004",
            "customer_id": "c1",
            "items": [{"sku": "NOPE-001", "qty": 1}],
        },
    },
}

ORDER_NOT_FOUND = {
    "model": ErrorResponse,
    "description": "Order not found",
    "content": {"application/json": {"example": {"detail": "Order 999 not found"}}},
}

ORDER_EXAMPLE = {
    "order_ref": "ORD-1001",
    "customer_id": "c1",
    "items": [
        {"sku": "BAN-001", "qty": 2, "unit_price_cents": 2499, "fulfilled_qty": None, "line_total_cents": 4998},
        {"sku": "MLK-001", "qty": 1, "unit_price_cents": 3199, "fulfilled_qty": None, "line_total_cents": 3199},
    ],
    "id": 55,
    "total_cents": 8197,
    "status": "pending",
    "created_at": "2026-11-19T09:30:00Z",
    "updated_at": "2026-11-19T09:30:00Z",
}


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    operation_id="listOrders",
    summary="List orders",
    description=(
        "Returns orders newest first, using cursor (keyset) pagination. "
        "Call without `cursor` for the first page, then pass the `next_cursor` "
        "from each response until it is null. Pages stay consistent while new "
        "orders arrive: nothing is skipped or repeated."
    ),
    response_description="A page of orders and the cursor for the next page",
    responses={
        status.HTTP_200_OK: {
            "content": {
                "application/json": {
                    "example": {"items": [ORDER_EXAMPLE], "next_cursor": "eyJpZCI6NTV9"}
                }
            }
        },
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorResponse,
            "description": "The cursor is malformed",
            "content": {"application/json": {"example": {"detail": "Invalid cursor"}}},
        },
    },
)
async def list_orders(
    controller: OrderController = Depends(),
    cursor: Annotated[
        str | None, Query(description="`next_cursor` from the previous page")
    ] = None,
    limit: Annotated[int, Query(ge=1, le=100, description="Page size, 1-100")] = 20,
) -> OrderPage:
    return await controller.list_orders(cursor, limit)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    operation_id="createOrder",
    summary="Create an order",
    description=(
        "Accepts the order as `pending` and records an `order_accepted` event; it "
        "does not wait for stock. The stock worker then supplies what is available, "
        "charges only for that and sets the final status. `order_ref` must be "
        "unique, so change it before sending an example twice. Orders are still "
        "accepted while the Valkey cache is down; duplicates are then caught by Postgres."
    ),
    response_description="The created order",
    responses={
        status.HTTP_201_CREATED: {
            "content": {"application/json": {"example": ORDER_EXAMPLE}}
        },
        status.HTTP_409_CONFLICT: {
            "model": ErrorResponse,
            "description": "An order with this order_ref already exists",
            "content": {
                "application/json": {"example": {"detail": "Order 'ORD-1001' already exists"}}
            },
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "description": "Invalid body or unknown SKU(s)",
        },
    },
)
async def create_order(
    data: Annotated[OrderCreate, Body(openapi_examples=CREATE_EXAMPLES)],
    controller: OrderController = Depends(),
) -> Order:
    return await controller.create_order(data)


@router.get(
    "/{order_id}",
    status_code=status.HTTP_200_OK,
    operation_id="getOrder",
    summary="Get an order",
    description="Returns the full order: reference, customer, line items and status.",
    response_description="The order",
    responses={
        status.HTTP_200_OK: {"content": {"application/json": {"example": ORDER_EXAMPLE}}},
        status.HTTP_404_NOT_FOUND: ORDER_NOT_FOUND,
    },
)
async def get_order(order_id: int, controller: OrderController = Depends()) -> Order:
    return await controller.get_order(order_id)


@router.get(
    "/{order_id}/status",
    status_code=status.HTTP_200_OK,
    operation_id="getOrderStatus",
    summary="Get an order's status",
    response_description="The order id and its current status",
    responses={
        status.HTTP_200_OK: {
            "content": {"application/json": {
                "example": {"id": 55, "status": "pending", "updated_at": "2026-11-19T09:30:00Z"}
            }}
        },
        status.HTTP_404_NOT_FOUND: ORDER_NOT_FOUND,
    },
)
async def get_order_status(
    order_id: int, controller: OrderController = Depends()
) -> OrderStatus:
    return await controller.get_status(order_id)
