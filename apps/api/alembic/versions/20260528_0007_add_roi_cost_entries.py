"""Add ROI cost entries.

Revision ID: 20260528_0007
Revises: 20260528_0006
Create Date: 2026-05-28
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260528_0007"
down_revision = "20260528_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "roi_cost_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("external_id", sa.String(length=120), nullable=True),
        sa.Column("cost_type", sa.String(length=40), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(length=12), nullable=False, server_default="USD"),
        sa.Column("labor_hours", sa.Numeric(8, 2), nullable=True),
        sa.Column("hourly_rate", sa.Numeric(10, 2), nullable=True),
        sa.Column("channel_name", sa.String(length=120), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_roi_cost_entries_external_id", "roi_cost_entries", ["external_id"], unique=True)
    op.create_index("ix_roi_cost_entries_cost_type", "roi_cost_entries", ["cost_type"])
    op.create_index("ix_roi_cost_entries_channel_name", "roi_cost_entries", ["channel_name"])
    op.create_index("ix_roi_cost_entries_occurred_at", "roi_cost_entries", ["occurred_at"])


def downgrade() -> None:
    op.drop_index("ix_roi_cost_entries_occurred_at", table_name="roi_cost_entries")
    op.drop_index("ix_roi_cost_entries_channel_name", table_name="roi_cost_entries")
    op.drop_index("ix_roi_cost_entries_cost_type", table_name="roi_cost_entries")
    op.drop_index("ix_roi_cost_entries_external_id", table_name="roi_cost_entries")
    op.drop_table("roi_cost_entries")
