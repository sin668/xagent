"""Create lead enrichment results.

Revision ID: 20260604_0024
Revises: 20260603_0023
Create Date: 2026-06-04
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260604_0024"
down_revision = "20260603_0023"
branch_labels = None
depends_on = None


lead_enrichment_type = postgresql.ENUM(
    "ai_deep_research",
    "manual_supplement",
    name="leadenrichmenttype",
    create_type=False,
)
lead_enrichment_result_status = postgresql.ENUM(
    "pending",
    "running",
    "succeeded",
    "failed",
    "cancelled",
    name="leadenrichmentresultstatus",
    create_type=False,
)


def upgrade() -> None:
    lead_enrichment_type.create(op.get_bind(), checkfirst=True)
    lead_enrichment_result_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "lead_enrichment_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("staging_lead_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("enrichment_type", lead_enrichment_type, nullable=False),
        sa.Column("triggered_by", sa.String(length=120), nullable=False),
        sa.Column("status", lead_enrichment_result_status, nullable=False),
        sa.Column("input_snapshot_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("output_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("evidence_links", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("missing_fields", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("recommended_action", sa.String(length=120), nullable=True),
        sa.Column("agent_task_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["agent_task_run_id"], ["agent_task_runs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["staging_lead_id"], ["staging_leads.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_lead_enrichment_results_staging_lead_id", "lead_enrichment_results", ["staging_lead_id"])
    op.create_index("ix_lead_enrichment_results_enrichment_type", "lead_enrichment_results", ["enrichment_type"])
    op.create_index("ix_lead_enrichment_results_triggered_by", "lead_enrichment_results", ["triggered_by"])
    op.create_index("ix_lead_enrichment_results_status", "lead_enrichment_results", ["status"])
    op.create_index("ix_lead_enrichment_results_recommended_action", "lead_enrichment_results", ["recommended_action"])
    op.create_index("ix_lead_enrichment_results_agent_task_run_id", "lead_enrichment_results", ["agent_task_run_id"])


def downgrade() -> None:
    op.drop_index("ix_lead_enrichment_results_agent_task_run_id", table_name="lead_enrichment_results")
    op.drop_index("ix_lead_enrichment_results_recommended_action", table_name="lead_enrichment_results")
    op.drop_index("ix_lead_enrichment_results_status", table_name="lead_enrichment_results")
    op.drop_index("ix_lead_enrichment_results_triggered_by", table_name="lead_enrichment_results")
    op.drop_index("ix_lead_enrichment_results_enrichment_type", table_name="lead_enrichment_results")
    op.drop_index("ix_lead_enrichment_results_staging_lead_id", table_name="lead_enrichment_results")
    op.drop_table("lead_enrichment_results")
    lead_enrichment_result_status.drop(op.get_bind(), checkfirst=True)
    lead_enrichment_type.drop(op.get_bind(), checkfirst=True)
