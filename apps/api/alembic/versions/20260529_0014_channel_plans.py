"""Create channel plans.

Revision ID: 20260529_0014
Revises: 20260529_0013
Create Date: 2026-05-29
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260529_0014"
down_revision = "20260529_0013"
branch_labels = None
depends_on = None


channel_risk_level = postgresql.ENUM("Low", "Medium", "High", "Forbidden", name="channelrisklevel", create_type=False)
source_usage_type = postgresql.ENUM(
    "automatic_collection",
    "public_discovery_only",
    "manual_sample",
    "policy_research",
    name="sourceusagetype",
    create_type=False,
)
channel_plan_status = postgresql.ENUM("draft", "enabled", "paused", "archived", name="channelplanstatus", create_type=False)


def upgrade() -> None:
    channel_plan_status.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "channel_plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("country", sa.String(length=80), nullable=False),
        sa.Column("city", sa.String(length=120), nullable=False),
        sa.Column("channel_name", sa.String(length=120), nullable=False),
        sa.Column("channel_type", sa.String(length=80), nullable=False),
        sa.Column("risk_level", channel_risk_level, nullable=False),
        sa.Column("source_usage_type", source_usage_type, nullable=False),
        sa.Column("keywords", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("daily_url_limit", sa.Integer(), nullable=False),
        sa.Column("daily_lead_limit", sa.Integer(), nullable=True),
        sa.Column("status", channel_plan_status, nullable=False, server_default="draft"),
        sa.Column("owner", sa.String(length=120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_channel_plans_country", "channel_plans", ["country"])
    op.create_index("ix_channel_plans_city", "channel_plans", ["city"])
    op.create_index("ix_channel_plans_channel_name", "channel_plans", ["channel_name"])
    op.create_index("ix_channel_plans_channel_type", "channel_plans", ["channel_type"])
    op.create_index("ix_channel_plans_risk_level", "channel_plans", ["risk_level"])
    op.create_index("ix_channel_plans_source_usage_type", "channel_plans", ["source_usage_type"])
    op.create_index("ix_channel_plans_status", "channel_plans", ["status"])
    op.create_index("ix_channel_plans_owner", "channel_plans", ["owner"])


def downgrade() -> None:
    op.drop_index("ix_channel_plans_owner", table_name="channel_plans")
    op.drop_index("ix_channel_plans_status", table_name="channel_plans")
    op.drop_index("ix_channel_plans_source_usage_type", table_name="channel_plans")
    op.drop_index("ix_channel_plans_risk_level", table_name="channel_plans")
    op.drop_index("ix_channel_plans_channel_type", table_name="channel_plans")
    op.drop_index("ix_channel_plans_channel_name", table_name="channel_plans")
    op.drop_index("ix_channel_plans_city", table_name="channel_plans")
    op.drop_index("ix_channel_plans_country", table_name="channel_plans")
    op.drop_table("channel_plans")
    channel_plan_status.drop(op.get_bind(), checkfirst=True)
