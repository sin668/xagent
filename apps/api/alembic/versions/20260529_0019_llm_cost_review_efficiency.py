"""Add ai audit cost and token fields.

Revision ID: 20260529_0019
Revises: 20260529_0018
Create Date: 2026-05-29
"""

from alembic import op
import sqlalchemy as sa

revision = "20260529_0019"
down_revision = "20260529_0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("ai_audit_logs", sa.Column("channel_name", sa.String(length=120), nullable=True))
    op.add_column("ai_audit_logs", sa.Column("input_tokens", sa.Integer(), nullable=True))
    op.add_column("ai_audit_logs", sa.Column("output_tokens", sa.Integer(), nullable=True))
    op.add_column("ai_audit_logs", sa.Column("total_tokens", sa.Integer(), nullable=True))
    op.add_column("ai_audit_logs", sa.Column("cost_amount", sa.Numeric(12, 4), nullable=True))
    op.add_column("ai_audit_logs", sa.Column("cost_currency", sa.String(length=12), nullable=True))
    op.create_index("ix_ai_audit_logs_channel_name", "ai_audit_logs", ["channel_name"])


def downgrade() -> None:
    op.drop_index("ix_ai_audit_logs_channel_name", table_name="ai_audit_logs")
    op.drop_column("ai_audit_logs", "cost_currency")
    op.drop_column("ai_audit_logs", "cost_amount")
    op.drop_column("ai_audit_logs", "total_tokens")
    op.drop_column("ai_audit_logs", "output_tokens")
    op.drop_column("ai_audit_logs", "input_tokens")
    op.drop_column("ai_audit_logs", "channel_name")
