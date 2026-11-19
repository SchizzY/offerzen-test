from sqlalchemy import BigInteger, Boolean, ForeignKey, Integer, String, func, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.db import Base
from app.models.mixins import TimestampMixin

ORDER_ACCEPTED = "order_accepted"
ORDER_FULFILLED = "order_fulfilled"

# Advisory lock that serialises appends to order_events (see append_event).
EVENT_LOG_LOCK = 7_262_001


class OrderEvent(TimestampMixin, Base):
    """Append-only log of order events (the outbox). Written in the same
    transaction as the change it describes; never updated after insert."""

    __tablename__ = "order_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    order_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)


class ConsumerOffset(TimestampMixin, Base):
    """How far each consumer has read order_events (like a Kafka offset)."""

    __tablename__ = "consumer_offsets"

    consumer: Mapped[str] = mapped_column(String(100), primary_key=True)
    last_event_id: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    paused: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


def append_event(session: Session, order_id: int, type: str, payload: dict) -> OrderEvent:
    """Append to order_events so that ids become visible in id order.

    Ids come from a sequence at insert time, but rows only become visible at
    commit. Without care, event 11 can commit before event 10, a reader that has
    moved past 11 never sees 10, and that order is silently skipped. Taking a
    transaction-scoped lock before the insert (released at commit) means no later
    id can commit before an earlier one, so "read everything after my last id"
    never skips. Cost: event-writing transactions commit one at a time, for the
    short span between this insert and their commit.
    """
    session.execute(select(func.pg_advisory_xact_lock(EVENT_LOG_LOCK)))
    event = OrderEvent(order_id=order_id, type=type, payload=payload)
    session.add(event)
    session.flush()
    return event
