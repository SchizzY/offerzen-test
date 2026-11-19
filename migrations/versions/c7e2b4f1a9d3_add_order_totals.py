"""add order totals

Stores the price charged on each line (unit_price_cents, line_total_cents inside
items) and the order total. Existing orders are backfilled from current product
prices, since their original prices were never recorded.

Revision ID: c7e2b4f1a9d3
Revises: a3f1c9d2e8b7
Create Date: 2026-11-19 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'c7e2b4f1a9d3'
down_revision: Union[str, Sequence[str], None] = 'a3f1c9d2e8b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TABLE orders ADD COLUMN total_cents INTEGER")
    op.execute(
        """
        UPDATE orders o
        SET items = priced.items, total_cents = priced.total_cents
        FROM (
            SELECT
                o2.id,
                jsonb_agg(
                    line.item || jsonb_build_object(
                        'unit_price_cents', COALESCE(round(p.price_cents), 0)::int,
                        'line_total_cents',
                            COALESCE(round(p.price_cents), 0)::int * (line.item->>'qty')::int
                    )
                    ORDER BY line.ord
                ) AS items,
                sum(COALESCE(round(p.price_cents), 0)::int * (line.item->>'qty')::int)
                    AS total_cents
            FROM orders o2
            CROSS JOIN LATERAL jsonb_array_elements(o2.items) WITH ORDINALITY AS line(item, ord)
            LEFT JOIN products p ON p.sku = line.item->>'sku'
            GROUP BY o2.id
        ) priced
        WHERE o.id = priced.id
        """
    )
    op.execute("UPDATE orders SET total_cents = 0 WHERE total_cents IS NULL")
    op.execute(
        """
        ALTER TABLE orders
            ALTER COLUMN total_cents SET NOT NULL,
            ADD CONSTRAINT ck_orders_total_cents_non_negative CHECK (total_cents >= 0)
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        """
        UPDATE orders o
        SET items = COALESCE((
            SELECT jsonb_agg(item - 'unit_price_cents' - 'line_total_cents' ORDER BY ord)
            FROM jsonb_array_elements(o.items) WITH ORDINALITY AS line(item, ord)
        ), '[]'::jsonb)
        """
    )
    op.execute("ALTER TABLE orders DROP COLUMN total_cents")
