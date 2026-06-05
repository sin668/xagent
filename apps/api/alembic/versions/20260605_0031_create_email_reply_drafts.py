"""Create email reply drafts.

Revision ID: 20260605_0031
Revises: 20260605_0030
Create Date: 2026-06-05
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260605_0031"
down_revision = "20260605_0030"
branch_labels = None
depends_on = None


email_reply_draft_status = postgresql.ENUM(
    "drafted",
    "pending_review",
    "approved",
    "sent",
    "rejected",
    "blocked",
    "failed",
    name="emailreplydraftstatus",
    create_type=False,
)


def upgrade() -> None:
    email_reply_draft_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "email_reply_drafts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("thread_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("agent_service_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("agent_task_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("prompt_template_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("prompt_version", sa.String(length=40), nullable=True),
        sa.Column("model", sa.String(length=120), nullable=True),
        sa.Column("detected_language", sa.String(length=20), nullable=True),
        sa.Column("reply_language", sa.String(length=20), nullable=True),
        sa.Column("language_confidence", sa.Float(), nullable=True),
        sa.Column("ai_suggested_subject", sa.String(length=500), nullable=True),
        sa.Column("ai_suggested_body", sa.Text(), nullable=False),
        sa.Column("final_subject", sa.String(length=500), nullable=True),
        sa.Column("final_body", sa.Text(), nullable=True),
        sa.Column("knowledge_hits_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("auto_send_allowed", sa.Boolean(), nullable=False),
        sa.Column("auto_send_decision_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("manual_review_required", sa.Boolean(), nullable=False),
        sa.Column("manual_review_reason", sa.Text(), nullable=True),
        sa.Column("status", email_reply_draft_status, nullable=False),
        sa.Column("reviewed_by", sa.String(length=120), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_record_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["agent_task_run_id"], ["agent_task_runs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["message_id"], ["email_messages.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["prompt_template_id"], ["llm_prompt_templates.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["sent_record_id"], ["outreach_records.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["thread_id"], ["email_threads.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_email_reply_drafts_thread_id", "email_reply_drafts", ["thread_id"])
    op.create_index("ix_email_reply_drafts_message_id", "email_reply_drafts", ["message_id"])
    op.create_index("ix_email_reply_drafts_customer_id", "email_reply_drafts", ["customer_id"])
    op.create_index("ix_email_reply_drafts_agent_service_run_id", "email_reply_drafts", ["agent_service_run_id"])
    op.create_index("ix_email_reply_drafts_agent_task_run_id", "email_reply_drafts", ["agent_task_run_id"])
    op.create_index("ix_email_reply_drafts_prompt_template_id", "email_reply_drafts", ["prompt_template_id"])
    op.create_index("ix_email_reply_drafts_detected_language", "email_reply_drafts", ["detected_language"])
    op.create_index("ix_email_reply_drafts_reply_language", "email_reply_drafts", ["reply_language"])
    op.create_index("ix_email_reply_drafts_auto_send_allowed", "email_reply_drafts", ["auto_send_allowed"])
    op.create_index("ix_email_reply_drafts_manual_review_required", "email_reply_drafts", ["manual_review_required"])
    op.create_index("ix_email_reply_drafts_status", "email_reply_drafts", ["status"])
    op.create_index("ix_email_reply_drafts_sent_record_id", "email_reply_drafts", ["sent_record_id"])


def downgrade() -> None:
    op.drop_index("ix_email_reply_drafts_sent_record_id", table_name="email_reply_drafts")
    op.drop_index("ix_email_reply_drafts_status", table_name="email_reply_drafts")
    op.drop_index("ix_email_reply_drafts_manual_review_required", table_name="email_reply_drafts")
    op.drop_index("ix_email_reply_drafts_auto_send_allowed", table_name="email_reply_drafts")
    op.drop_index("ix_email_reply_drafts_reply_language", table_name="email_reply_drafts")
    op.drop_index("ix_email_reply_drafts_detected_language", table_name="email_reply_drafts")
    op.drop_index("ix_email_reply_drafts_prompt_template_id", table_name="email_reply_drafts")
    op.drop_index("ix_email_reply_drafts_agent_task_run_id", table_name="email_reply_drafts")
    op.drop_index("ix_email_reply_drafts_agent_service_run_id", table_name="email_reply_drafts")
    op.drop_index("ix_email_reply_drafts_customer_id", table_name="email_reply_drafts")
    op.drop_index("ix_email_reply_drafts_message_id", table_name="email_reply_drafts")
    op.drop_index("ix_email_reply_drafts_thread_id", table_name="email_reply_drafts")
    op.drop_table("email_reply_drafts")

    email_reply_draft_status.drop(op.get_bind(), checkfirst=True)
