"""Create audit and risk base logs.

Revision ID: 20260529_0013
Revises: 20260529_0012
Create Date: 2026-05-29
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260529_0013"
down_revision = "20260529_0012"
branch_labels = None
depends_on = None


risk_event_severity = postgresql.ENUM("low", "medium", "high", "critical", name="riskeventseverity", create_type=False)
risk_event_status = postgresql.ENUM("open", "investigating", "resolved", "dismissed", name="riskeventstatus", create_type=False)
channel_risk_level = postgresql.ENUM("Low", "Medium", "High", "Forbidden", name="channelrisklevel", create_type=False)


def upgrade() -> None:
    risk_event_severity.create(op.get_bind(), checkfirst=True)
    risk_event_status.create(op.get_bind(), checkfirst=True)

    op.add_column("ai_audit_logs", sa.Column("source_urls", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")))
    op.add_column("ai_audit_logs", sa.Column("output_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True))

    op.create_table(
        "agent_run_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("task_id", sa.String(length=120), nullable=True),
        sa.Column("agent_name", sa.String(length=120), nullable=False),
        sa.Column("action", sa.String(length=120), nullable=False),
        sa.Column("input_ref", sa.Text(), nullable=True),
        sa.Column("output_ref", sa.Text(), nullable=True),
        sa.Column("result", sa.String(length=80), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_agent_run_logs_task_id", "agent_run_logs", ["task_id"])
    op.create_index("ix_agent_run_logs_agent_name", "agent_run_logs", ["agent_name"])
    op.create_index("ix_agent_run_logs_action", "agent_run_logs", ["action"])
    op.create_index("ix_agent_run_logs_result", "agent_run_logs", ["result"])

    op.create_table(
        "review_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("task_id", sa.String(length=120), nullable=True),
        sa.Column("agent_name", sa.String(length=120), nullable=True),
        sa.Column("action", sa.String(length=120), nullable=False),
        sa.Column("reviewer", sa.String(length=120), nullable=True),
        sa.Column("input_ref", sa.Text(), nullable=True),
        sa.Column("output_ref", sa.Text(), nullable=True),
        sa.Column("result", sa.String(length=80), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_review_logs_task_id", "review_logs", ["task_id"])
    op.create_index("ix_review_logs_agent_name", "review_logs", ["agent_name"])
    op.create_index("ix_review_logs_action", "review_logs", ["action"])
    op.create_index("ix_review_logs_reviewer", "review_logs", ["reviewer"])
    op.create_index("ix_review_logs_result", "review_logs", ["result"])

    op.create_table(
        "risk_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("task_id", sa.String(length=120), nullable=True),
        sa.Column("agent_name", sa.String(length=120), nullable=True),
        sa.Column("action", sa.String(length=120), nullable=True),
        sa.Column("channel", sa.String(length=120), nullable=False),
        sa.Column("risk_level", channel_risk_level, nullable=False),
        sa.Column("event_type", sa.String(length=120), nullable=False),
        sa.Column("severity", risk_event_severity, nullable=False),
        sa.Column("resolution_status", risk_event_status, nullable=False),
        sa.Column("block_reason", sa.Text(), nullable=True),
        sa.Column("input_ref", sa.Text(), nullable=True),
        sa.Column("output_ref", sa.Text(), nullable=True),
        sa.Column("result", sa.String(length=80), nullable=False, server_default="blocked"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_risk_events_task_id", "risk_events", ["task_id"])
    op.create_index("ix_risk_events_agent_name", "risk_events", ["agent_name"])
    op.create_index("ix_risk_events_action", "risk_events", ["action"])
    op.create_index("ix_risk_events_channel", "risk_events", ["channel"])
    op.create_index("ix_risk_events_risk_level", "risk_events", ["risk_level"])
    op.create_index("ix_risk_events_event_type", "risk_events", ["event_type"])
    op.create_index("ix_risk_events_severity", "risk_events", ["severity"])
    op.create_index("ix_risk_events_resolution_status", "risk_events", ["resolution_status"])
    op.create_index("ix_risk_events_result", "risk_events", ["result"])


def downgrade() -> None:
    op.drop_index("ix_risk_events_result", table_name="risk_events")
    op.drop_index("ix_risk_events_resolution_status", table_name="risk_events")
    op.drop_index("ix_risk_events_severity", table_name="risk_events")
    op.drop_index("ix_risk_events_event_type", table_name="risk_events")
    op.drop_index("ix_risk_events_risk_level", table_name="risk_events")
    op.drop_index("ix_risk_events_channel", table_name="risk_events")
    op.drop_index("ix_risk_events_action", table_name="risk_events")
    op.drop_index("ix_risk_events_agent_name", table_name="risk_events")
    op.drop_index("ix_risk_events_task_id", table_name="risk_events")
    op.drop_table("risk_events")

    op.drop_index("ix_review_logs_result", table_name="review_logs")
    op.drop_index("ix_review_logs_reviewer", table_name="review_logs")
    op.drop_index("ix_review_logs_action", table_name="review_logs")
    op.drop_index("ix_review_logs_agent_name", table_name="review_logs")
    op.drop_index("ix_review_logs_task_id", table_name="review_logs")
    op.drop_table("review_logs")

    op.drop_index("ix_agent_run_logs_result", table_name="agent_run_logs")
    op.drop_index("ix_agent_run_logs_action", table_name="agent_run_logs")
    op.drop_index("ix_agent_run_logs_agent_name", table_name="agent_run_logs")
    op.drop_index("ix_agent_run_logs_task_id", table_name="agent_run_logs")
    op.drop_table("agent_run_logs")

    op.drop_column("ai_audit_logs", "output_json")
    op.drop_column("ai_audit_logs", "source_urls")
    risk_event_status.drop(op.get_bind(), checkfirst=True)
    risk_event_severity.drop(op.get_bind(), checkfirst=True)
