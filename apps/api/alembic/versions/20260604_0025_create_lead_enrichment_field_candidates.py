"""Create lead enrichment field candidates.

Revision ID: 20260604_0025
Revises: 20260604_0024
Create Date: 2026-06-04
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260604_0025"
down_revision = "20260604_0024"
branch_labels = None
depends_on = None


lead_enrichment_field_source_type = postgresql.ENUM(
    "ai_public_source",
    "manual_public_info",
    "manual_customer_reply",
    "manual_business_note",
    "unknown",
    name="leadenrichmentfieldsourcetype",
    create_type=False,
)
lead_enrichment_field_review_status = postgresql.ENUM(
    "pending",
    "accepted",
    "rejected",
    "needs_review",
    name="leadenrichmentfieldreviewstatus",
    create_type=False,
)


def upgrade() -> None:
    lead_enrichment_field_source_type.create(op.get_bind(), checkfirst=True)
    lead_enrichment_field_review_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "lead_enrichment_field_candidates",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("enrichment_result_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("staging_lead_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("field_name", sa.String(length=120), nullable=False),
        sa.Column("candidate_value", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("source_type", lead_enrichment_field_source_type, nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("evidence_note", sa.Text(), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("review_status", lead_enrichment_field_review_status, nullable=False),
        sa.Column("accepted_by", sa.String(length=120), nullable=True),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejected_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["enrichment_result_id"], ["lead_enrichment_results.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["staging_lead_id"], ["staging_leads.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_lead_enrichment_field_candidates_enrichment_result_id",
        "lead_enrichment_field_candidates",
        ["enrichment_result_id"],
    )
    op.create_index(
        "ix_lead_enrichment_field_candidates_staging_lead_id",
        "lead_enrichment_field_candidates",
        ["staging_lead_id"],
    )
    op.create_index("ix_lead_enrichment_field_candidates_field_name", "lead_enrichment_field_candidates", ["field_name"])
    op.create_index("ix_lead_enrichment_field_candidates_source_type", "lead_enrichment_field_candidates", ["source_type"])
    op.create_index(
        "ix_lead_enrichment_field_candidates_review_status",
        "lead_enrichment_field_candidates",
        ["review_status"],
    )
    op.create_index("ix_lead_enrichment_field_candidates_accepted_by", "lead_enrichment_field_candidates", ["accepted_by"])


def downgrade() -> None:
    op.drop_index("ix_lead_enrichment_field_candidates_accepted_by", table_name="lead_enrichment_field_candidates")
    op.drop_index("ix_lead_enrichment_field_candidates_review_status", table_name="lead_enrichment_field_candidates")
    op.drop_index("ix_lead_enrichment_field_candidates_source_type", table_name="lead_enrichment_field_candidates")
    op.drop_index("ix_lead_enrichment_field_candidates_field_name", table_name="lead_enrichment_field_candidates")
    op.drop_index("ix_lead_enrichment_field_candidates_staging_lead_id", table_name="lead_enrichment_field_candidates")
    op.drop_index(
        "ix_lead_enrichment_field_candidates_enrichment_result_id",
        table_name="lead_enrichment_field_candidates",
    )
    op.drop_table("lead_enrichment_field_candidates")
    lead_enrichment_field_review_status.drop(op.get_bind(), checkfirst=True)
    lead_enrichment_field_source_type.drop(op.get_bind(), checkfirst=True)
