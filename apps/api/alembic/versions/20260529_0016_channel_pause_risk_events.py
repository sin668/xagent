"""Add channel pause risk event fields.

Revision ID: 20260529_0016
Revises: 20260529_0015
Create Date: 2026-05-29
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260529_0016"
down_revision = "20260529_0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("risk_events", sa.Column("channel_plan_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("risk_events", sa.Column("pause_suggested", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("risk_events", sa.Column("resolution_note", sa.Text(), nullable=True))
    op.add_column("risk_events", sa.Column("resolved_by", sa.String(length=120), nullable=True))
    op.create_foreign_key(
        "fk_risk_events_channel_plan_id_channel_plans",
        "risk_events",
        "channel_plans",
        ["channel_plan_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_risk_events_channel_plan_id", "risk_events", ["channel_plan_id"])
    op.create_index("ix_risk_events_pause_suggested", "risk_events", ["pause_suggested"])


def downgrade() -> None:
    op.drop_index("ix_risk_events_pause_suggested", table_name="risk_events")
    op.drop_index("ix_risk_events_channel_plan_id", table_name="risk_events")
    op.drop_constraint("fk_risk_events_channel_plan_id_channel_plans", "risk_events", type_="foreignkey")
    op.drop_column("risk_events", "resolved_by")
    op.drop_column("risk_events", "resolution_note")
    op.drop_column("risk_events", "pause_suggested")
    op.drop_column("risk_events", "channel_plan_id")
