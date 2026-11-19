from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


OrderStatusValue = Literal["pending", "confirmed", "partially_fulfilled", "unfulfilled"]


class OrderItem(BaseModel):
    sku: str = Field(description="Product SKU", examples=["BAN-001"])
    qty: int = Field(gt=0, description="Quantity to order, at least 1", examples=[2])


class OrderLine(OrderItem):
    unit_price_cents: int = Field(
        description="Product price when the order was placed", examples=[2499]
    )
    fulfilled_qty: int | None = Field(
        default=None,
        description="Units actually supplied; null until the stock worker processes the order",
        examples=[2],
    )
    line_total_cents: int = Field(
        description="unit_price_cents x qty while pending, then x fulfilled_qty", examples=[4998]
    )


class OrderCreate(BaseModel):
    order_ref: str = Field(
        description="Client-supplied unique reference; reusing one returns 409",
        examples=["ORD-1001"],
    )
    customer_id: str = Field(description="Customer placing the order", examples=["c1"])
    items: list[OrderItem] = Field(default=[], description="Line items; repeated SKUs are summed")


class Order(OrderCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="Server-assigned order id", examples=[55])
    items: list[OrderLine] = Field(description="Line items with the prices charged")
    total_cents: int = Field(
        description=(
            "Sum of line totals at the prices when the order was placed. Drops if "
            "lines can't be fully fulfilled: only what is supplied is charged"
        ),
        examples=[8197],
    )
    status: OrderStatusValue = Field(
        default="pending",
        description=(
            "`pending` until the stock worker processes it, then `confirmed` (all "
            "supplied), `partially_fulfilled` or `unfulfilled` (nothing supplied)"
        ),
    )
    created_at: datetime = Field(description="When the order was accepted")
    updated_at: datetime = Field(description="Last change to the order")


class OrderStatus(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="Order id", examples=[55])
    status: OrderStatusValue = Field(description="Current order status", examples=["pending"])
    updated_at: datetime = Field(description="When the status (or order) last changed")


class OrderPage(BaseModel):
    items: list[Order] = Field(description="Orders on this page, newest first")
    next_cursor: str | None = Field(
        description="Pass as `cursor` to get the next page; null on the last page",
        examples=["eyJpZCI6NTZ9"],
    )
