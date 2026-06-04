"""Add outreach record owner.

Revision ID: 20260528_0003
Revises: 20260528_0002
Create Date: 2026-05-28
"""
from alembic import op
import sqlalchemy as sa

revision = "20260528_0003"
down_revision = "20260528_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("outreach_records", sa.Column("owner", sa.String(length=120), nullable=True))


def downgrade() -> None:
    op.drop_column("outreach_records", "owner")
