"""Add email reply agent task type.

Revision ID: 20260605_0036
Revises: 20260605_0035
Create Date: 2026-06-05
"""

from alembic import op


revision = "20260605_0036"
down_revision = "20260605_0035"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE agenttasktype ADD VALUE IF NOT EXISTS 'EMAIL_REPLY'")


def downgrade() -> None:
    # PostgreSQL enum values cannot be dropped safely without rebuilding the type.
    pass
