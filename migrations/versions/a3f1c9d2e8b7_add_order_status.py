"""add order status

Revision ID: a3f1c9d2e8b7
Revises: 78293f50c104
Create Date: 2026-11-19 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'a3f1c9d2e8b7'
down_revision: Union[str, Sequence[str], None] = '78293f50c104'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        """
        ALTER TABLE orders
        ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'pending'
            CHECK (status IN ('pending', 'confirmed', 'backordered'))
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("ALTER TABLE orders DROP COLUMN status")
