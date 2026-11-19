from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_session
from app.models.event import ORDER_ACCEPTED, append_event
from app.models.order import Order
from app.schemas.order import OrderCreate


class OrderResource:
    def __init__(self, session: Session = Depends(get_session)) -> None:
        self.session = session

    def list_after(self, after_id: int, limit: int) -> list[Order]:
        stmt = select(Order).where(Order.id > after_id).order_by(Order.id).limit(limit)
        return list(self.session.scalars(stmt))

    def list_page(self, before_id: int | None, limit: int) -> list[Order]:
        stmt = select(Order).order_by(Order.id.desc()).limit(limit)
        if before_id is not None:
            stmt = stmt.where(Order.id < before_id)
        return list(self.session.scalars(stmt))

    def get(self, order_id: int) -> Order | None:
        return self.session.get(Order, order_id)

    def get_by_ref(self, order_ref: str) -> Order | None:
        return self.session.scalar(select(Order).where(Order.order_ref == order_ref))

    def stage(self, data: OrderCreate, lines: list[dict], total_cents: int) -> Order:
        order = Order(
            order_ref=data.order_ref,
            customer_id=data.customer_id,
            items=lines,
            total_cents=total_cents,
        )
        self.session.add(order)
        try:
            self.session.flush()
        except IntegrityError:
            self.session.rollback()
            raise
        # Outbox: the event commits (or rolls back) together with the order.
        append_event(
            self.session,
            order.id,
            ORDER_ACCEPTED,
            {
                "order_id": order.id,
                "order_ref": order.order_ref,
                "customer_id": order.customer_id,
                "items": lines,
                "total_cents": total_cents,
            },
        )
        return order

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()
