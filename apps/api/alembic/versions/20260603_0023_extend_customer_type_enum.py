"""Extend customer type enum.

Revision ID: 20260603_0023
Revises: 20260602_0022
Create Date: 2026-06-03
"""

from alembic import op


revision = "20260603_0023"
down_revision = "20260602_0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE customertype ADD VALUE IF NOT EXISTS 'dealership_directory'")
    op.execute("ALTER TYPE customertype ADD VALUE IF NOT EXISTS 'marketplace'")


def downgrade() -> None:
    # PostgreSQL enum values cannot be safely removed without rebuilding dependent columns.
    pass
