"""Create email threads and messages.

Revision ID: 20260605_0030
Revises: 20260605_0029
Create Date: 2026-06-05
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260605_0030"
down_revision = "20260605_0029"
branch_labels = None
depends_on = None


email_thread_status = postgresql.ENUM(
    "open",
    "waiting_reply",
    "replied",
    "archived",
    "blocked",
    name="emailthreadstatus",
    create_type=False,
)
email_message_direction = postgresql.ENUM(
    "inbound",
    "outbound",
    name="emailmessagedirection",
    create_type=False,
)
email_message_status = postgresql.ENUM(
    "received",
    "pending_reply",
    "drafted",
    "sent",
    "failed",
    "archived",
    name="emailmessagestatus",
    create_type=False,
)
email_message_source_type = postgresql.ENUM(
    "manual",
    "api_import",
    "mailbox_sync",
    name="emailmessagesourcetype",
    create_type=False,
)


def upgrade() -> None:
    email_thread_status.create(op.get_bind(), checkfirst=True)
    email_message_direction.create(op.get_bind(), checkfirst=True)
    email_message_status.create(op.get_bind(), checkfirst=True)
    email_message_source_type.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "email_threads",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("subject", sa.String(length=500), nullable=False),
        sa.Column("status", email_thread_status, nullable=False),
        sa.Column("channel_account", sa.String(length=255), nullable=True),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_email_threads_customer_id", "email_threads", ["customer_id"])
    op.create_index("ix_email_threads_status", "email_threads", ["status"])
    op.create_index("ix_email_threads_channel_account", "email_threads", ["channel_account"])
    op.create_index("ix_email_threads_last_message_at", "email_threads", ["last_message_at"])

    op.create_table(
        "email_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("thread_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("direction", email_message_direction, nullable=False),
        sa.Column("from_email", sa.String(length=320), nullable=False),
        sa.Column("to_emails", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("cc_emails", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("subject", sa.String(length=500), nullable=False),
        sa.Column("body_text", sa.Text(), nullable=False),
        sa.Column("body_html", sa.Text(), nullable=True),
        sa.Column("language", sa.String(length=20), nullable=True),
        sa.Column("status", email_message_status, nullable=False),
        sa.Column("source_type", email_message_source_type, nullable=False),
        sa.Column("external_message_id", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["thread_id"], ["email_threads.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_email_messages_thread_id", "email_messages", ["thread_id"])
    op.create_index("ix_email_messages_customer_id", "email_messages", ["customer_id"])
    op.create_index("ix_email_messages_direction", "email_messages", ["direction"])
    op.create_index("ix_email_messages_from_email", "email_messages", ["from_email"])
    op.create_index("ix_email_messages_language", "email_messages", ["language"])
    op.create_index("ix_email_messages_status", "email_messages", ["status"])
    op.create_index("ix_email_messages_source_type", "email_messages", ["source_type"])
    op.create_index("ix_email_messages_external_message_id", "email_messages", ["external_message_id"])


def downgrade() -> None:
    op.drop_index("ix_email_messages_external_message_id", table_name="email_messages")
    op.drop_index("ix_email_messages_source_type", table_name="email_messages")
    op.drop_index("ix_email_messages_status", table_name="email_messages")
    op.drop_index("ix_email_messages_language", table_name="email_messages")
    op.drop_index("ix_email_messages_from_email", table_name="email_messages")
    op.drop_index("ix_email_messages_direction", table_name="email_messages")
    op.drop_index("ix_email_messages_customer_id", table_name="email_messages")
    op.drop_index("ix_email_messages_thread_id", table_name="email_messages")
    op.drop_table("email_messages")

    op.drop_index("ix_email_threads_last_message_at", table_name="email_threads")
    op.drop_index("ix_email_threads_channel_account", table_name="email_threads")
    op.drop_index("ix_email_threads_status", table_name="email_threads")
    op.drop_index("ix_email_threads_customer_id", table_name="email_threads")
    op.drop_table("email_threads")

    email_message_source_type.drop(op.get_bind(), checkfirst=True)
    email_message_status.drop(op.get_bind(), checkfirst=True)
    email_message_direction.drop(op.get_bind(), checkfirst=True)
    email_thread_status.drop(op.get_bind(), checkfirst=True)
