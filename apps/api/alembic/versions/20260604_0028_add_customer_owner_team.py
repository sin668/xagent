"""Add customer owner team.

Revision ID: 20260604_0028
Revises: 20260604_0027
Create Date: 2026-06-04
"""

from alembic import op
import sqlalchemy as sa


revision = "20260604_0028"
down_revision = "20260604_0027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("customers", sa.Column("owner_team", sa.String(length=80), nullable=True))
    op.create_index("ix_customers_owner_team", "customers", ["owner_team"])


def downgrade() -> None:
    op.drop_index("ix_customers_owner_team", table_name="customers")
    op.drop_column("customers", "owner_team")
