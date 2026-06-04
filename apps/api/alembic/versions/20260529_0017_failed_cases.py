"""Create failed cases library.

Revision ID: 20260529_0017
Revises: 20260529_0016
Create Date: 2026-05-29
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260529_0017"
down_revision = "20260529_0016"
branch_labels = None
depends_on = None


failed_case_type = postgresql.ENUM(
    "fetch_failed",
    "schema_invalid",
    "missing_evidence",
    "risk_blocked",
    "duplicate",
    "llm_suspected_fabrication",
    name="failedcasetype",
    create_type=False,
)
channel_risk_level = postgresql.ENUM("Low", "Medium", "High", "Forbidden", name="channelrisklevel", create_type=False)


def upgrade() -> None:
    failed_case_type.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "failed_cases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("case_type", failed_case_type, nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("risk_level", channel_risk_level, nullable=True),
        sa.Column("related_task_type", sa.String(length=80), nullable=True),
        sa.Column("related_object_type", sa.String(length=80), nullable=True),
        sa.Column("related_object_id", sa.String(length=120), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=False),
        sa.Column("evidence_note", sa.Text(), nullable=True),
        sa.Column("raw_input_ref", sa.Text(), nullable=True),
        sa.Column("raw_output_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("model_name", sa.String(length=120), nullable=True),
        sa.Column("prompt_version", sa.String(length=120), nullable=True),
        sa.Column("usable_for_rag", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("touch_queue_allowed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_failed_cases_case_type", "failed_cases", ["case_type"])
    op.create_index("ix_failed_cases_risk_level", "failed_cases", ["risk_level"])
    op.create_index("ix_failed_cases_related_task_type", "failed_cases", ["related_task_type"])
    op.create_index("ix_failed_cases_related_object_type", "failed_cases", ["related_object_type"])
    op.create_index("ix_failed_cases_related_object_id", "failed_cases", ["related_object_id"])
    op.create_index("ix_failed_cases_model_name", "failed_cases", ["model_name"])
    op.create_index("ix_failed_cases_prompt_version", "failed_cases", ["prompt_version"])
    op.create_index("ix_failed_cases_usable_for_rag", "failed_cases", ["usable_for_rag"])
    op.create_index("ix_failed_cases_touch_queue_allowed", "failed_cases", ["touch_queue_allowed"])


def downgrade() -> None:
    op.drop_index("ix_failed_cases_touch_queue_allowed", table_name="failed_cases")
    op.drop_index("ix_failed_cases_usable_for_rag", table_name="failed_cases")
    op.drop_index("ix_failed_cases_prompt_version", table_name="failed_cases")
    op.drop_index("ix_failed_cases_model_name", table_name="failed_cases")
    op.drop_index("ix_failed_cases_related_object_id", table_name="failed_cases")
    op.drop_index("ix_failed_cases_related_object_type", table_name="failed_cases")
    op.drop_index("ix_failed_cases_related_task_type", table_name="failed_cases")
    op.drop_index("ix_failed_cases_risk_level", table_name="failed_cases")
    op.drop_index("ix_failed_cases_case_type", table_name="failed_cases")
    op.drop_table("failed_cases")
    failed_case_type.drop(op.get_bind(), checkfirst=True)

