"""Create staging leads table.

Revision ID: 20260529_0012
Revises: 20260529_0011
Create Date: 2026-05-29
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260529_0012"
down_revision = "20260529_0011"
branch_labels = None
depends_on = None


staging_review_status = postgresql.ENUM(
    "pending_review",
    "needs_secondary_verification",
    "approved",
    "rejected",
    "duplicate",
    name="stagingreviewstatus",
    create_type=False,
)
staging_queue_status = postgresql.ENUM(
    "pending_review",
    "eligible",
    "not_eligible",
    "blocked",
    name="stagingqueuestatus",
    create_type=False,
)
customer_type = postgresql.ENUM(
    "local_dealer_secondary_dealer",
    "personal_buyer",
    "kol_auto_blogger",
    "unknown",
    "non_target",
    name="customertype",
    create_type=False,
)
customer_grade = postgresql.ENUM("A", "B", "C", "Invalid", "Watch", name="customergrade", create_type=False)


def upgrade() -> None:
    staging_review_status.create(op.get_bind(), checkfirst=True)
    staging_queue_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "staging_leads",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("candidate_url_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("candidate_urls.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("customer_name", sa.String(length=255), nullable=False, server_default="Unknown"),
        sa.Column("country", sa.String(length=80), nullable=False, server_default="Unknown"),
        sa.Column("city", sa.String(length=120), nullable=True),
        sa.Column("customer_type", customer_type, nullable=False, server_default="unknown"),
        sa.Column("contacts_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("activity_level", sa.String(length=80), nullable=True),
        sa.Column("scale_signal", sa.Text(), nullable=True),
        sa.Column("import_used_car_relevance", sa.String(length=120), nullable=True),
        sa.Column("source_evidence", sa.Text(), nullable=True),
        sa.Column("recommended_grade", customer_grade, nullable=False),
        sa.Column("recommended_reason", sa.Text(), nullable=True),
        sa.Column("missing_fields", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("review_status", staging_review_status, nullable=False),
        sa.Column("queue_status", staging_queue_status, nullable=False),
        sa.Column("dedupe_key", sa.String(length=255), nullable=True),
        sa.Column("requires_compliance_review", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_staging_leads_candidate_url_id", "staging_leads", ["candidate_url_id"])
    op.create_index("ix_staging_leads_customer_name", "staging_leads", ["customer_name"])
    op.create_index("ix_staging_leads_country", "staging_leads", ["country"])
    op.create_index("ix_staging_leads_city", "staging_leads", ["city"])
    op.create_index("ix_staging_leads_customer_type", "staging_leads", ["customer_type"])
    op.create_index("ix_staging_leads_recommended_grade", "staging_leads", ["recommended_grade"])
    op.create_index("ix_staging_leads_review_status", "staging_leads", ["review_status"])
    op.create_index("ix_staging_leads_queue_status", "staging_leads", ["queue_status"])
    op.create_index("ix_staging_leads_dedupe_key", "staging_leads", ["dedupe_key"])
    op.create_index("ix_staging_leads_requires_compliance_review", "staging_leads", ["requires_compliance_review"])
    op.execute("COMMENT ON TABLE staging_leads IS 'AI 抽取候选线索 staging 层，人工复核后才可进入 core'")


def downgrade() -> None:
    op.drop_index("ix_staging_leads_requires_compliance_review", table_name="staging_leads")
    op.drop_index("ix_staging_leads_dedupe_key", table_name="staging_leads")
    op.drop_index("ix_staging_leads_queue_status", table_name="staging_leads")
    op.drop_index("ix_staging_leads_review_status", table_name="staging_leads")
    op.drop_index("ix_staging_leads_recommended_grade", table_name="staging_leads")
    op.drop_index("ix_staging_leads_customer_type", table_name="staging_leads")
    op.drop_index("ix_staging_leads_city", table_name="staging_leads")
    op.drop_index("ix_staging_leads_country", table_name="staging_leads")
    op.drop_index("ix_staging_leads_customer_name", table_name="staging_leads")
    op.drop_index("ix_staging_leads_candidate_url_id", table_name="staging_leads")
    op.drop_table("staging_leads")
    staging_queue_status.drop(op.get_bind(), checkfirst=True)
    staging_review_status.drop(op.get_bind(), checkfirst=True)
