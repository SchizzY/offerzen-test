"""add order_events outbox, consumer offsets, fulfilment statuses

order_events is an append-only log: an order_accepted row is written in the same
transaction as its order. Consumers (the stock worker now, external systems
later) track their position in consumer_offsets, like Kafka consumer offsets.

Orders become pending -> confirmed | partially_fulfilled | unfulfilled; groceries
can't be backordered, so 'backordered' goes away and stock never goes negative.

Existing orders already had stock deducted the old way (in full), so they are
marked confirmed with fulfilled_qty = qty, get their events, and the stock
consumer starts after them so nothing is deducted twice.

Revision ID: f1b9c2d4e7a5
Revises: e5a8d1c3b6f2
Create Date: 2026-11-19 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'f1b9c2d4e7a5'
down_revision: Union[str, Sequence[str], None] = 'e5a8d1c3b6f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NEW_STATUSES = "('pending', 'confirmed', 'partially_fulfilled', 'unfulfilled')"
OLD_STATUSES = "('pending', 'confirmed', 'backordered')"


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        """
        CREATE TABLE order_events (
            id          BIGSERIAL    PRIMARY KEY,
            order_id    INTEGER      NOT NULL REFERENCES orders (id) ON DELETE CASCADE,
            type        VARCHAR(50)  NOT NULL,
            payload     JSONB        NOT NULL,
            created_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
            updated_at  TIMESTAMPTZ  NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX ix_order_events_order_id ON order_events (order_id)")
    op.execute(
        """
        CREATE TABLE consumer_offsets (
            consumer       VARCHAR(100) PRIMARY KEY,
            last_event_id  BIGINT       NOT NULL DEFAULT 0,
            paused         BOOLEAN      NOT NULL DEFAULT false,
            created_at     TIMESTAMPTZ  NOT NULL DEFAULT now(),
            updated_at     TIMESTAMPTZ  NOT NULL DEFAULT now()
        )
        """
    )
    for table in ("order_events", "consumer_offsets"):
        op.execute(
            f"""
            CREATE TRIGGER trg_{table}_updated_at
            BEFORE UPDATE ON {table}
            FOR EACH ROW EXECUTE FUNCTION set_updated_at()
            """
        )

    # Statuses: backordered -> fulfilment outcomes.
    op.execute("ALTER TABLE orders DROP CONSTRAINT orders_status_check")
    op.execute(
        f"""
        UPDATE orders SET
            status = CASE WHEN status = 'pending' THEN 'confirmed' ELSE status END,
            items = (
                SELECT COALESCE(jsonb_agg(
                    line || jsonb_build_object('fulfilled_qty', (line->>'qty')::int)
                    ORDER BY ord), '[]'::jsonb)
                FROM jsonb_array_elements(items) WITH ORDINALITY AS l(line, ord)
            )
        """
    )
    op.execute("UPDATE orders SET status = 'confirmed' WHERE status = 'backordered'")
    op.execute(f"ALTER TABLE orders ADD CONSTRAINT orders_status_check CHECK (status IN {NEW_STATUSES})")

    # History for existing orders; the stock consumer starts after it.
    op.execute(
        """
        INSERT INTO order_events (order_id, type, payload, created_at, updated_at)
        SELECT id, 'order_accepted',
               jsonb_build_object(
                   'order_id', id, 'order_ref', order_ref, 'customer_id', customer_id,
                   'items', items, 'total_cents', total_cents),
               created_at, created_at
        FROM orders ORDER BY id
        """
    )
    op.execute(
        """
        INSERT INTO consumer_offsets (consumer, last_event_id)
        SELECT 'stock', COALESCE(max(id), 0) FROM order_events
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP TABLE consumer_offsets")
    op.execute("DROP TABLE order_events")
    op.execute("ALTER TABLE orders DROP CONSTRAINT orders_status_check")
    op.execute(
        """
        UPDATE orders SET
            status = CASE WHEN status = 'pending' THEN 'pending' ELSE 'confirmed' END,
            items = (
                SELECT COALESCE(jsonb_agg(line - 'fulfilled_qty' ORDER BY ord), '[]'::jsonb)
                FROM jsonb_array_elements(items) WITH ORDINALITY AS l(line, ord)
            )
        """
    )
    op.execute(f"ALTER TABLE orders ADD CONSTRAINT orders_status_check CHECK (status IN {OLD_STATUSES})")
