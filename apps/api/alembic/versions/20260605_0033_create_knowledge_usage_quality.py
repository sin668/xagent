"""Create knowledge usage and quality metrics.

Revision ID: 20260605_0033
Revises: 20260605_0032
Create Date: 2026-06-05
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260605_0033"
down_revision = "20260605_0032"
branch_labels = None
depends_on = None


knowledge_usage_outcome = postgresql.ENUM(
    "retrieved",
    "adopted",
    "edited",
    "rejected",
    "customer_replied",
    "bounced",
    "suggest_deprecate",
    name="knowledgeusageoutcome",
    create_type=False,
)


def upgrade() -> None:
    knowledge_usage_outcome.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "knowledge_usage_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("knowledge_item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("knowledge_version", sa.String(length=80), nullable=False),
        sa.Column("email_reply_draft_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("retrieval_query", sa.Text(), nullable=True),
        sa.Column("similarity_score", sa.Float(), nullable=True),
        sa.Column("rank", sa.Integer(), nullable=True),
        sa.Column("filters_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("outcome", knowledge_usage_outcome, nullable=False),
        sa.Column("adopted", sa.Boolean(), nullable=False),
        sa.Column("edit_distance_ratio", sa.Float(), nullable=True),
        sa.Column("caused_bounce", sa.Boolean(), nullable=False),
        sa.Column("customer_replied", sa.Boolean(), nullable=False),
        sa.Column("suggest_deprecate", sa.Boolean(), nullable=False),
        sa.Column("suggest_deprecate_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["email_reply_draft_id"], ["email_reply_drafts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["knowledge_item_id"], ["knowledge_items.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_knowledge_usage_records_knowledge_item_id", "knowledge_usage_records", ["knowledge_item_id"])
    op.create_index("ix_knowledge_usage_records_knowledge_version", "knowledge_usage_records", ["knowledge_version"])
    op.create_index("ix_knowledge_usage_records_email_reply_draft_id", "knowledge_usage_records", ["email_reply_draft_id"])
    op.create_index("ix_knowledge_usage_records_outcome", "knowledge_usage_records", ["outcome"])
    op.create_index("ix_knowledge_usage_records_adopted", "knowledge_usage_records", ["adopted"])
    op.create_index("ix_knowledge_usage_records_caused_bounce", "knowledge_usage_records", ["caused_bounce"])
    op.create_index("ix_knowledge_usage_records_customer_replied", "knowledge_usage_records", ["customer_replied"])
    op.create_index("ix_knowledge_usage_records_suggest_deprecate", "knowledge_usage_records", ["suggest_deprecate"])

    op.create_table(
        "knowledge_quality_metrics",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("knowledge_item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("knowledge_version", sa.String(length=80), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("retrieval_count", sa.Integer(), nullable=False),
        sa.Column("adoption_count", sa.Integer(), nullable=False),
        sa.Column("adoption_rate", sa.Float(), nullable=False),
        sa.Column("average_edit_distance_ratio", sa.Float(), nullable=True),
        sa.Column("bounce_count", sa.Integer(), nullable=False),
        sa.Column("bounce_rate", sa.Float(), nullable=False),
        sa.Column("customer_reply_count", sa.Integer(), nullable=False),
        sa.Column("customer_reply_rate", sa.Float(), nullable=False),
        sa.Column("suggest_deprecate", sa.Boolean(), nullable=False),
        sa.Column("suggest_deprecate_reason", sa.Text(), nullable=True),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["knowledge_item_id"], ["knowledge_items.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_knowledge_quality_metrics_knowledge_item_id", "knowledge_quality_metrics", ["knowledge_item_id"])
    op.create_index("ix_knowledge_quality_metrics_knowledge_version", "knowledge_quality_metrics", ["knowledge_version"])
    op.create_index("ix_knowledge_quality_metrics_period_start", "knowledge_quality_metrics", ["period_start"])
    op.create_index("ix_knowledge_quality_metrics_period_end", "knowledge_quality_metrics", ["period_end"])
    op.create_index("ix_knowledge_quality_metrics_suggest_deprecate", "knowledge_quality_metrics", ["suggest_deprecate"])


def downgrade() -> None:
    op.drop_index("ix_knowledge_quality_metrics_suggest_deprecate", table_name="knowledge_quality_metrics")
    op.drop_index("ix_knowledge_quality_metrics_period_end", table_name="knowledge_quality_metrics")
    op.drop_index("ix_knowledge_quality_metrics_period_start", table_name="knowledge_quality_metrics")
    op.drop_index("ix_knowledge_quality_metrics_knowledge_version", table_name="knowledge_quality_metrics")
    op.drop_index("ix_knowledge_quality_metrics_knowledge_item_id", table_name="knowledge_quality_metrics")
    op.drop_table("knowledge_quality_metrics")

    op.drop_index("ix_knowledge_usage_records_suggest_deprecate", table_name="knowledge_usage_records")
    op.drop_index("ix_knowledge_usage_records_customer_replied", table_name="knowledge_usage_records")
    op.drop_index("ix_knowledge_usage_records_caused_bounce", table_name="knowledge_usage_records")
    op.drop_index("ix_knowledge_usage_records_adopted", table_name="knowledge_usage_records")
    op.drop_index("ix_knowledge_usage_records_outcome", table_name="knowledge_usage_records")
    op.drop_index("ix_knowledge_usage_records_email_reply_draft_id", table_name="knowledge_usage_records")
    op.drop_index("ix_knowledge_usage_records_knowledge_version", table_name="knowledge_usage_records")
    op.drop_index("ix_knowledge_usage_records_knowledge_item_id", table_name="knowledge_usage_records")
    op.drop_table("knowledge_usage_records")

    knowledge_usage_outcome.drop(op.get_bind(), checkfirst=True)
