"""Create lead cleanup tables.

Revision ID: 20260604_0026
Revises: 20260604_0025
Create Date: 2026-06-04
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260604_0026"
down_revision = "20260604_0025"
branch_labels = None
depends_on = None


lead_cleanup_run_status = postgresql.ENUM(
    "pending",
    "running",
    "succeeded",
    "failed",
    "cancelled",
    name="leadcleanuprunstatus",
    create_type=False,
)
lead_cleanup_suggestion_type = postgresql.ENUM(
    "strong_duplicate",
    "possible_duplicate",
    "merge_contact_method",
    "merge_source_evidence",
    "restore_from_watch",
    "confirm_invalid",
    "mark_abandoned",
    "needs_manual_review",
    name="leadcleanupsuggestiontype",
    create_type=False,
)
lead_cleanup_suggestion_review_status = postgresql.ENUM(
    "pending",
    "approved",
    "rejected",
    "executed",
    name="leadcleanupsuggestionreviewstatus",
    create_type=False,
)


def upgrade() -> None:
    lead_cleanup_run_status.create(op.get_bind(), checkfirst=True)
    lead_cleanup_suggestion_type.create(op.get_bind(), checkfirst=True)
    lead_cleanup_suggestion_review_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "lead_cleanup_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("trigger_source", sa.String(length=120), nullable=False),
        sa.Column("status", lead_cleanup_run_status, nullable=False),
        sa.Column("input_filter_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("output_summary_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("llm_provider", sa.String(length=80), nullable=True),
        sa.Column("llm_model", sa.String(length=120), nullable=True),
        sa.Column("prompt_template_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["prompt_template_id"], ["llm_prompt_templates.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_lead_cleanup_runs_trigger_source", "lead_cleanup_runs", ["trigger_source"])
    op.create_index("ix_lead_cleanup_runs_status", "lead_cleanup_runs", ["status"])
    op.create_index("ix_lead_cleanup_runs_llm_provider", "lead_cleanup_runs", ["llm_provider"])
    op.create_index("ix_lead_cleanup_runs_prompt_template_id", "lead_cleanup_runs", ["prompt_template_id"])

    op.create_table(
        "lead_cleanup_suggestions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cleanup_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("staging_lead_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("suggestion_type", lead_cleanup_suggestion_type, nullable=False),
        sa.Column("target_lead_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("evidence_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("recommended_action", sa.Text(), nullable=False),
        sa.Column("review_status", lead_cleanup_suggestion_review_status, nullable=False),
        sa.Column("reviewer_id", sa.String(length=120), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("executed_by", sa.String(length=120), nullable=True),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("execution_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["cleanup_run_id"], ["lead_cleanup_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["staging_lead_id"], ["staging_leads.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_lead_id"], ["staging_leads.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_lead_cleanup_suggestions_cleanup_run_id", "lead_cleanup_suggestions", ["cleanup_run_id"])
    op.create_index("ix_lead_cleanup_suggestions_staging_lead_id", "lead_cleanup_suggestions", ["staging_lead_id"])
    op.create_index("ix_lead_cleanup_suggestions_suggestion_type", "lead_cleanup_suggestions", ["suggestion_type"])
    op.create_index("ix_lead_cleanup_suggestions_target_lead_id", "lead_cleanup_suggestions", ["target_lead_id"])
    op.create_index("ix_lead_cleanup_suggestions_review_status", "lead_cleanup_suggestions", ["review_status"])
    op.create_index("ix_lead_cleanup_suggestions_reviewer_id", "lead_cleanup_suggestions", ["reviewer_id"])
    op.create_index("ix_lead_cleanup_suggestions_executed_by", "lead_cleanup_suggestions", ["executed_by"])


def downgrade() -> None:
    op.drop_index("ix_lead_cleanup_suggestions_executed_by", table_name="lead_cleanup_suggestions")
    op.drop_index("ix_lead_cleanup_suggestions_reviewer_id", table_name="lead_cleanup_suggestions")
    op.drop_index("ix_lead_cleanup_suggestions_review_status", table_name="lead_cleanup_suggestions")
    op.drop_index("ix_lead_cleanup_suggestions_target_lead_id", table_name="lead_cleanup_suggestions")
    op.drop_index("ix_lead_cleanup_suggestions_suggestion_type", table_name="lead_cleanup_suggestions")
    op.drop_index("ix_lead_cleanup_suggestions_staging_lead_id", table_name="lead_cleanup_suggestions")
    op.drop_index("ix_lead_cleanup_suggestions_cleanup_run_id", table_name="lead_cleanup_suggestions")
    op.drop_table("lead_cleanup_suggestions")
    op.drop_index("ix_lead_cleanup_runs_prompt_template_id", table_name="lead_cleanup_runs")
    op.drop_index("ix_lead_cleanup_runs_llm_provider", table_name="lead_cleanup_runs")
    op.drop_index("ix_lead_cleanup_runs_status", table_name="lead_cleanup_runs")
    op.drop_index("ix_lead_cleanup_runs_trigger_source", table_name="lead_cleanup_runs")
    op.drop_table("lead_cleanup_runs")
    lead_cleanup_suggestion_review_status.drop(op.get_bind(), checkfirst=True)
    lead_cleanup_suggestion_type.drop(op.get_bind(), checkfirst=True)
    lead_cleanup_run_status.drop(op.get_bind(), checkfirst=True)
