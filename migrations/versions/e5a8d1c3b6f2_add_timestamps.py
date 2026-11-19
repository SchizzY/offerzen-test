"""add created_at / updated_at to orders and products

updated_at is kept current by a BEFORE UPDATE trigger, so it also covers bulk
UPDATEs (stock deduction) and manual SQL. Existing rows get the migration time,
since their real creation times were never recorded.

Revision ID: e5a8d1c3b6f2
Revises: c7e2b4f1a9d3
Create Date: 2026-11-19 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'e5a8d1c3b6f2'
down_revision: Union[str, Sequence[str], None] = 'c7e2b4f1a9d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLES = ("orders", "products")


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        """
        CREATE FUNCTION set_updated_at() RETURNS trigger AS $$
        BEGIN
            IF NEW IS DISTINCT FROM OLD THEN
                NEW.updated_at = now();
            END IF;
            RETURN NEW;
        END
        $$ LANGUAGE plpgsql
        """
    )
    for table in TABLES:
        op.execute(
            f"""
            ALTER TABLE {table}
                ADD COLUMN created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                ADD COLUMN updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            """
        )
        op.execute(
            f"""
            CREATE TRIGGER trg_{table}_updated_at
            BEFORE UPDATE ON {table}
            FOR EACH ROW EXECUTE FUNCTION set_updated_at()
            """
        )
    op.execute("CREATE INDEX ix_orders_created_at ON orders (created_at)")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP INDEX ix_orders_created_at")
    for table in TABLES:
        op.execute(f"DROP TRIGGER trg_{table}_updated_at ON {table}")
        op.execute(f"ALTER TABLE {table} DROP COLUMN created_at, DROP COLUMN updated_at")
    op.execute("DROP FUNCTION set_updated_at()")
