"""store products.price_cents as an integer

It was created as FLOAT (double precision). Money in floating point can't
represent every value exactly, so prices are whole cents in an INTEGER, and
can't be negative. Existing values are rounded to the nearest cent (they were
all whole already in practice).

Revision ID: a7d3e9f2c1b8
Revises: f1b9c2d4e7a5
Create Date: 2026-11-19 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'a7d3e9f2c1b8'
down_revision: Union[str, Sequence[str], None] = 'f1b9c2d4e7a5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        """
        ALTER TABLE products
            ALTER COLUMN price_cents TYPE INTEGER USING round(price_cents)::integer,
            ADD CONSTRAINT ck_products_price_cents_non_negative CHECK (price_cents >= 0)
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        """
        ALTER TABLE products
            DROP CONSTRAINT ck_products_price_cents_non_negative,
            ALTER COLUMN price_cents TYPE DOUBLE PRECISION
        """
    )
