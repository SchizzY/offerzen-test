from datetime import datetime

from sqlalchemy import DateTime, FetchedValue, func
from sqlalchemy.orm import Mapped, mapped_column


class TimestampMixin:
    """created_at / updated_at, both set by Postgres.

    updated_at is maintained by a BEFORE UPDATE trigger (see the add_timestamps
    migration), so it is also bumped by bulk UPDATEs and manual SQL, not only by
    ORM writes. eager_defaults makes INSERT/UPDATE return the values immediately.
    """

    __mapper_args__ = {"eager_defaults": True}

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        server_onupdate=FetchedValue(),
    )
