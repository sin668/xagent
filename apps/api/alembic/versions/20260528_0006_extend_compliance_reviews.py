"""Extend compliance reviews.

Revision ID: 20260528_0006
Revises: 20260528_0005
Create Date: 2026-05-28
"""
from alembic import op

revision = "20260528_0006"
down_revision = "20260528_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE customerstatus ADD VALUE IF NOT EXISTS 'quoted'")
    op.execute("ALTER TABLE compliance_reviews ADD COLUMN IF NOT EXISTS risk_note TEXT")


def downgrade() -> None:
    op.execute("ALTER TABLE compliance_reviews DROP COLUMN IF EXISTS risk_note")
