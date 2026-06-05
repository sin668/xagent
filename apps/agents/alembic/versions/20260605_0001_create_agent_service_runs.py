"""Create agent service runs.

Revision ID: 20260605_0001
Revises:
Create Date: 2026-06-05
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260605_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_service_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent_type", sa.String(length=80), nullable=False),
        sa.Column("agent_mode", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("trigger_source", sa.String(length=80), nullable=False),
        sa.Column("input_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("output_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("output_summary_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("audit_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_retries", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_type", sa.String(length=80), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_service_runs_request_id", "agent_service_runs", ["request_id"])
    op.create_index("ix_agent_service_runs_agent_type", "agent_service_runs", ["agent_type"])
    op.create_index("ix_agent_service_runs_agent_mode", "agent_service_runs", ["agent_mode"])
    op.create_index("ix_agent_service_runs_status", "agent_service_runs", ["status"])
    op.create_index("ix_agent_service_runs_trigger_source", "agent_service_runs", ["trigger_source"])
    op.create_index("ix_agent_service_runs_error_type", "agent_service_runs", ["error_type"])


def downgrade() -> None:
    op.drop_index("ix_agent_service_runs_error_type", table_name="agent_service_runs")
    op.drop_index("ix_agent_service_runs_trigger_source", table_name="agent_service_runs")
    op.drop_index("ix_agent_service_runs_status", table_name="agent_service_runs")
    op.drop_index("ix_agent_service_runs_agent_mode", table_name="agent_service_runs")
    op.drop_index("ix_agent_service_runs_agent_type", table_name="agent_service_runs")
    op.drop_index("ix_agent_service_runs_request_id", table_name="agent_service_runs")
    op.drop_table("agent_service_runs")
