from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.event import OrderEvent


class EventResource:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_after(self, after_id: int, limit: int) -> list[OrderEvent]:
        stmt = select(OrderEvent).where(OrderEvent.id > after_id).order_by(OrderEvent.id).limit(limit)
        return list(self.session.scalars(stmt))
