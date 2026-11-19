"""Seed products and a few sample orders.

    poetry run python -m app.seed

Safe to re-run: existing products are left alone and sample orders that already
exist (same order_ref) are skipped. Orders go through OrderController, so totals,
line prices and stock deduction are exactly what the API would produce.
"""

import asyncio

from fastapi import HTTPException, status
from sqlalchemy.dialects.postgresql import insert

from app.cache import valkey_client
from app.controllers.order_controller import OrderController
from app.db import SessionLocal
from app.models.product import Product
from app.resources.order_resource import OrderResource
from app.resources.product_resource import ProductResource
from app.schemas.order import Order, OrderCreate

PRODUCTS = [
    {"sku": "BAN-001", "name": "Bananas (1kg)", "price_cents": 2499, "stock": 120},
    {"sku": "APL-001", "name": "Granny Smith Apples (1kg)", "price_cents": 3299, "stock": 80},
    {"sku": "APL-002", "name": "Pink Lady Apples (1kg)", "price_cents": 3899, "stock": 60},
    {"sku": "APL-003", "name": "Royal Gala Apples (1kg)", "price_cents": 3499, "stock": 75},
    {"sku": "ORG-001", "name": "Navel Oranges (1.5kg)", "price_cents": 2999, "stock": 90},
    {"sku": "AVO-001", "name": "Hass Avocados (4 pack)", "price_cents": 4499, "stock": 40},
    {"sku": "MLK-001", "name": "Full Cream Milk (2L)", "price_cents": 3199, "stock": 150},
    {"sku": "BRD-001", "name": "Brown Bread (700g)", "price_cents": 1899, "stock": 100},
    {"sku": "EGG-001", "name": "Large Eggs (18 pack)", "price_cents": 6499, "stock": 50},
    {"sku": "CHS-001", "name": "Cheddar Cheese (400g)", "price_cents": 8999, "stock": 30},
    {"sku": "COF-001", "name": "Ground Coffee (250g)", "price_cents": 10999, "stock": 25},
    {"sku": "RCE-001", "name": "Basmati Rice (2kg)", "price_cents": 5499, "stock": 0},
]

SAMPLE_ORDERS = [
    {
        "order_ref": "SEED-001",
        "customer_id": "c1",
        "items": [{"sku": "BAN-001", "qty": 2}, {"sku": "MLK-001", "qty": 1}],
    },
    {
        "order_ref": "SEED-002",
        "customer_id": "c2",
        "items": [
            {"sku": "BRD-001", "qty": 1},
            {"sku": "EGG-001", "qty": 1},
            {"sku": "CHS-001", "qty": 1},
        ],
    },
    {
        "order_ref": "SEED-003",
        "customer_id": "c1",
        "items": [{"sku": "COF-001", "qty": 2}, {"sku": "AVO-001", "qty": 1}],
    },
    {
        "order_ref": "SEED-004",
        "customer_id": "c3",
        "items": [{"sku": "APL-002", "qty": 3}, {"sku": "ORG-001", "qty": 1}],
    },
]


def seed_products() -> int:
    stmt = (
        insert(Product)
        .values(PRODUCTS)
        .on_conflict_do_nothing(index_elements=["sku"])
        .returning(Product.sku)
    )
    with SessionLocal() as session:
        inserted = session.scalars(stmt).all()
        session.commit()
    return len(inserted)


async def seed_orders() -> tuple[list[Order], int]:
    created: list[Order] = []
    skipped = 0
    async with valkey_client() as cache:
        for data in SAMPLE_ORDERS:
            with SessionLocal() as session:
                controller = OrderController(
                    OrderResource(session), ProductResource(session), cache
                )
                try:
                    created.append(await controller.create_order(OrderCreate(**data)))
                except HTTPException as err:
                    if err.status_code != status.HTTP_409_CONFLICT:
                        raise
                    skipped += 1
    return created, skipped


if __name__ == "__main__":
    count = seed_products()
    print(f"Inserted {count} products ({len(PRODUCTS) - count} already existed).")
    orders, skipped = asyncio.run(seed_orders())
    print(f"Created {len(orders)} sample orders ({skipped} already existed).")
    for order in orders:
        print(f"  #{order.id} {order.order_ref}: {order.total_cents} cents, {len(order.items)} lines")
