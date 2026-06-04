"""Create lead source candidates.

Revision ID: 20260602_0022
Revises: 20260602_0021
Create Date: 2026-06-02
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260602_0022"
down_revision = "20260602_0021"
branch_labels = None
depends_on = None


source_platform = postgresql.ENUM(
    "official_website",
    "public_directory",
    "search_engine",
    "google_maps",
    "yandex_maps",
    "youtube",
    "drom",
    "other",
    name="sourceplatform",
    create_type=False,
)
channel_risk_level = postgresql.ENUM("Low", "Medium", "High", "Forbidden", name="channelrisklevel", create_type=False)
review_status = postgresql.ENUM(
    "pending",
    "auto_approved",
    "approved",
    "rejected",
    "high_risk_review",
    "paused",
    "needs_recheck",
    name="leadsourcecandidatereviewstatus",
    create_type=False,
)
extraction_status = postgresql.ENUM(
    "pending",
    "queued",
    "running",
    "succeeded",
    "failed",
    "retry",
    "blocked",
    name="leadsourcecandidateextractionstatus",
    create_type=False,
)


def upgrade() -> None:
    review_status.create(op.get_bind(), checkfirst=True)
    extraction_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "lead_source_candidates",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("normalized_domain", sa.String(length=255), nullable=False),
        sa.Column("platform", source_platform, nullable=False),
        sa.Column("channel_name", sa.String(length=120), nullable=False),
        sa.Column("country", sa.String(length=80), nullable=False),
        sa.Column("city", sa.String(length=120), nullable=True),
        sa.Column("risk_level", channel_risk_level, nullable=False),
        sa.Column("review_status", review_status, nullable=False),
        sa.Column("approved_for_extraction", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("reviewer_id", sa.String(length=120), nullable=True),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("discovery_method", sa.String(length=120), nullable=False),
        sa.Column("discovery_query", sa.Text(), nullable=True),
        sa.Column("discovery_reason", sa.Text(), nullable=False),
        sa.Column("evidence_note", sa.Text(), nullable=False),
        sa.Column("evidence_links", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("llm_provider", sa.String(length=80), nullable=True),
        sa.Column("llm_model", sa.String(length=120), nullable=True),
        sa.Column("llm_output_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("extraction_status", extraction_status, nullable=False),
        sa.Column("last_extracted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("dedupe_key", sa.String(length=64), nullable=False),
        sa.Column("duplicate_of_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_duplicate", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_by_task_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by_task_run_id"], ["agent_task_runs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["duplicate_of_id"], ["lead_source_candidates.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dedupe_key", name="uq_lead_source_candidates_dedupe_key"),
    )
    op.create_index("ix_lead_source_candidates_normalized_domain", "lead_source_candidates", ["normalized_domain"])
    op.create_index("ix_lead_source_candidates_platform", "lead_source_candidates", ["platform"])
    op.create_index("ix_lead_source_candidates_channel_name", "lead_source_candidates", ["channel_name"])
    op.create_index("ix_lead_source_candidates_country", "lead_source_candidates", ["country"])
    op.create_index("ix_lead_source_candidates_city", "lead_source_candidates", ["city"])
    op.create_index("ix_lead_source_candidates_risk_level", "lead_source_candidates", ["risk_level"])
    op.create_index("ix_lead_source_candidates_review_status", "lead_source_candidates", ["review_status"])
    op.create_index("ix_lead_source_candidates_approved_for_extraction", "lead_source_candidates", ["approved_for_extraction"])
    op.create_index("ix_lead_source_candidates_extraction_status", "lead_source_candidates", ["extraction_status"])
    op.create_index("ix_lead_source_candidates_dedupe_key", "lead_source_candidates", ["dedupe_key"])
    op.create_index("ix_lead_source_candidates_duplicate_of_id", "lead_source_candidates", ["duplicate_of_id"])
    op.create_index("ix_lead_source_candidates_is_duplicate", "lead_source_candidates", ["is_duplicate"])
    op.create_index("ix_lead_source_candidates_created_by_task_run_id", "lead_source_candidates", ["created_by_task_run_id"])


def downgrade() -> None:
    op.drop_index("ix_lead_source_candidates_created_by_task_run_id", table_name="lead_source_candidates")
    op.drop_index("ix_lead_source_candidates_is_duplicate", table_name="lead_source_candidates")
    op.drop_index("ix_lead_source_candidates_duplicate_of_id", table_name="lead_source_candidates")
    op.drop_index("ix_lead_source_candidates_dedupe_key", table_name="lead_source_candidates")
    op.drop_index("ix_lead_source_candidates_extraction_status", table_name="lead_source_candidates")
    op.drop_index("ix_lead_source_candidates_approved_for_extraction", table_name="lead_source_candidates")
    op.drop_index("ix_lead_source_candidates_review_status", table_name="lead_source_candidates")
    op.drop_index("ix_lead_source_candidates_risk_level", table_name="lead_source_candidates")
    op.drop_index("ix_lead_source_candidates_city", table_name="lead_source_candidates")
    op.drop_index("ix_lead_source_candidates_country", table_name="lead_source_candidates")
    op.drop_index("ix_lead_source_candidates_channel_name", table_name="lead_source_candidates")
    op.drop_index("ix_lead_source_candidates_platform", table_name="lead_source_candidates")
    op.drop_index("ix_lead_source_candidates_normalized_domain", table_name="lead_source_candidates")
    op.drop_table("lead_source_candidates")
    extraction_status.drop(op.get_bind(), checkfirst=True)
    review_status.drop(op.get_bind(), checkfirst=True)
