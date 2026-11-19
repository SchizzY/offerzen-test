"""create products

Revision ID: 74c5a411f3fd
Revises: 
Create Date: 2026-11-18 00:32:30.448415

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '74c5a411f3fd'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        """
        CREATE TABLE products (
            id          SERIAL PRIMARY KEY,
            sku         VARCHAR(100) NOT NULL UNIQUE,
            name        VARCHAR(255) NOT NULL,
            price_cents FLOAT        NOT NULL,
            stock       INTEGER      NOT NULL DEFAULT 0
        )
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP TABLE products")
