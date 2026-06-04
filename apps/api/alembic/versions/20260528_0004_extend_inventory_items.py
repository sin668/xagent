"""Extend inventory items for light quote table.

Revision ID: 20260528_0004
Revises: 20260528_0003
Create Date: 2026-05-28
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260528_0004"
down_revision = "20260528_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("inventory_items", sa.Column("configuration", sa.Text(), nullable=True))
    op.add_column("inventory_items", sa.Column("media_urls", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("inventory_items", sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("inventory_items", "valid_until")
    op.drop_column("inventory_items", "media_urls")
    op.drop_column("inventory_items", "configuration")
