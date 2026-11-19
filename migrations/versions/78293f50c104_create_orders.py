"""create orders

Revision ID: 78293f50c104
Revises: 74c5a411f3fd
Create Date: 2026-11-18 00:34:49.775179

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '78293f50c104'
down_revision: Union[str, Sequence[str], None] = '74c5a411f3fd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        """
        CREATE TABLE orders (
            id          SERIAL PRIMARY KEY,
            order_ref   VARCHAR(100) NOT NULL UNIQUE,
            customer_id VARCHAR(100) NOT NULL,
            items       JSONB        NOT NULL DEFAULT '[]'::jsonb
        )
        """
    )
    op.execute("CREATE INDEX ix_orders_customer_id ON orders (customer_id)")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP TABLE orders")
