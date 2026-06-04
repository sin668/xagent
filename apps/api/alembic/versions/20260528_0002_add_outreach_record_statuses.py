"""Add outreach record statuses.

Revision ID: 20260528_0002
Revises: 20260528_0001
Create Date: 2026-05-28
"""
from alembic import op

revision = "20260528_0002"
down_revision = "20260528_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE outreachstatus ADD VALUE IF NOT EXISTS 'no_response'")
    op.execute("ALTER TYPE outreachstatus ADD VALUE IF NOT EXISTS 'bad_contact'")


def downgrade() -> None:
    # PostgreSQL does not support dropping enum values directly.
    pass
