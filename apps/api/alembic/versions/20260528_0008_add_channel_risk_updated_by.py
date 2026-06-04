"""Add channel risk rule operator audit.

Revision ID: 20260528_0008
Revises: 20260528_0007
Create Date: 2026-05-28
"""
from alembic import op
import sqlalchemy as sa

revision = "20260528_0008"
down_revision = "20260528_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("channel_risk_rules", sa.Column("updated_by", sa.String(length=120), nullable=True))


def downgrade() -> None:
    op.drop_column("channel_risk_rules", "updated_by")
