from sqlalchemy import func, select

from app.db import SessionLocal
from app.models.event import OrderEvent
from app.models.order import Order
from app.models.product import Product


def place(client, order_ref: str, items: list[dict], customer_id: str = "c1"):
    return client.post("/orders", json={"order_ref": order_ref, "customer_id": customer_id, "items": items})


def order(order_ref: str) -> Order | None:
    with SessionLocal() as session:
        return session.scalar(select(Order).where(Order.order_ref == order_ref))


def count_orders(order_ref: str) -> int:
    with SessionLocal() as session:
        return session.scalar(select(func.count()).select_from(Order).where(Order.order_ref == order_ref))


def stock(sku: str) -> int:
    with SessionLocal() as session:
        return session.scalar(select(Product.stock).where(Product.sku == sku))


def set_price(sku: str, price_cents: int) -> None:
    with SessionLocal() as session:
        session.query(Product).filter(Product.sku == sku).update({"price_cents": price_cents})
        session.commit()


def event_types(order_id: int) -> list[str]:
    with SessionLocal() as session:
        return list(session.scalars(select(OrderEvent.type).where(OrderEvent.order_id == order_id).order_by(OrderEvent.id)))


def wait_for_stock_worker(timeout: float = 10) -> None:
    from scripts.stock_worker import wait

    assert wait(timeout), "stock worker didn't catch up in time"
