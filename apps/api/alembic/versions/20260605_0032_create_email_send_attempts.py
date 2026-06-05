"""Create email send attempts.

Revision ID: 20260605_0032
Revises: 20260605_0031
Create Date: 2026-06-05
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260605_0032"
down_revision = "20260605_0031"
branch_labels = None
depends_on = None


email_send_attempt_status = postgresql.ENUM(
    "pending",
    "sending",
    "sent",
    "failed",
    "retry_pending",
    "bounced",
    "blocked",
    name="emailsendattemptstatus",
    create_type=False,
)


def upgrade() -> None:
    email_send_attempt_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "email_send_attempts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reply_draft_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("outreach_record_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("provider", sa.String(length=80), nullable=False),
        sa.Column("provider_message_id", sa.String(length=255), nullable=True),
        sa.Column("from_email", sa.String(length=320), nullable=False),
        sa.Column("to_emails", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("cc_emails", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("bcc_emails", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("subject_snapshot", sa.String(length=500), nullable=False),
        sa.Column("body_text_snapshot", sa.Text(), nullable=False),
        sa.Column("body_html_snapshot", sa.Text(), nullable=True),
        sa.Column("status", email_send_attempt_status, nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("error_code", sa.String(length=120), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("bounce_reason", sa.Text(), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["outreach_record_id"], ["outreach_records.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reply_draft_id"], ["email_reply_drafts.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_email_send_attempts_reply_draft_id", "email_send_attempts", ["reply_draft_id"])
    op.create_index("ix_email_send_attempts_outreach_record_id", "email_send_attempts", ["outreach_record_id"])
    op.create_index("ix_email_send_attempts_provider", "email_send_attempts", ["provider"])
    op.create_index("ix_email_send_attempts_provider_message_id", "email_send_attempts", ["provider_message_id"])
    op.create_index("ix_email_send_attempts_from_email", "email_send_attempts", ["from_email"])
    op.create_index("ix_email_send_attempts_status", "email_send_attempts", ["status"])
    op.create_index("ix_email_send_attempts_error_code", "email_send_attempts", ["error_code"])
    op.create_index("ix_email_send_attempts_sent_at", "email_send_attempts", ["sent_at"])


def downgrade() -> None:
    op.drop_index("ix_email_send_attempts_sent_at", table_name="email_send_attempts")
    op.drop_index("ix_email_send_attempts_error_code", table_name="email_send_attempts")
    op.drop_index("ix_email_send_attempts_status", table_name="email_send_attempts")
    op.drop_index("ix_email_send_attempts_from_email", table_name="email_send_attempts")
    op.drop_index("ix_email_send_attempts_provider_message_id", table_name="email_send_attempts")
    op.drop_index("ix_email_send_attempts_provider", table_name="email_send_attempts")
    op.drop_index("ix_email_send_attempts_outreach_record_id", table_name="email_send_attempts")
    op.drop_index("ix_email_send_attempts_reply_draft_id", table_name="email_send_attempts")
    op.drop_table("email_send_attempts")

    email_send_attempt_status.drop(op.get_bind(), checkfirst=True)
