"""Create agent task runs.

Revision ID: 20260602_0021
Revises: 20260602_0020
Create Date: 2026-06-02
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260602_0021"
down_revision = "20260602_0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_task_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("task_type", sa.Enum("SOURCE_DISCOVERY", "LEAD_EXTRACTION", "LEAD_GRADING", "RETRY_WORKER", name="agenttasktype"), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "running",
                "succeeded",
                "failed",
                "retry_pending",
                "paused",
                "cancelled",
                "manual_review_required",
                name="agenttaskrunstatus",
            ),
            nullable=False,
        ),
        sa.Column("trigger_source", sa.String(length=80), nullable=False),
        sa.Column("input_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("output_summary_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("llm_provider", sa.String(length=80), nullable=True),
        sa.Column("llm_model", sa.String(length=120), nullable=True),
        sa.Column("prompt_template_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("prompt_version", sa.String(length=40), nullable=True),
        sa.Column("token_usage_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["prompt_template_id"], ["llm_prompt_templates.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_task_runs_task_type", "agent_task_runs", ["task_type"])
    op.create_index("ix_agent_task_runs_status", "agent_task_runs", ["status"])
    op.create_index("ix_agent_task_runs_trigger_source", "agent_task_runs", ["trigger_source"])
    op.create_index("ix_agent_task_runs_llm_provider", "agent_task_runs", ["llm_provider"])
    op.create_index("ix_agent_task_runs_prompt_template_id", "agent_task_runs", ["prompt_template_id"])


def downgrade() -> None:
    op.drop_index("ix_agent_task_runs_prompt_template_id", table_name="agent_task_runs")
    op.drop_index("ix_agent_task_runs_llm_provider", table_name="agent_task_runs")
    op.drop_index("ix_agent_task_runs_trigger_source", table_name="agent_task_runs")
    op.drop_index("ix_agent_task_runs_status", table_name="agent_task_runs")
    op.drop_index("ix_agent_task_runs_task_type", table_name="agent_task_runs")
    op.drop_table("agent_task_runs")
    sa.Enum(name="agenttaskrunstatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="agenttasktype").drop(op.get_bind(), checkfirst=True)
