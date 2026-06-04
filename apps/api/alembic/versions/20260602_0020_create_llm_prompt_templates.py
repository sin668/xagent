"""Create llm prompt templates.

Revision ID: 20260602_0020
Revises: 20260529_0019
Create Date: 2026-06-02
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260602_0020"
down_revision = "20260529_0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "llm_prompt_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("task_type", sa.Enum("SOURCE_DISCOVERY", "LEAD_EXTRACTION", "LEAD_GRADING", name="llmprompttasktype"), nullable=False),
        sa.Column("provider", sa.String(length=80), nullable=False),
        sa.Column("model", sa.String(length=120), nullable=False),
        sa.Column("system_prompt", sa.Text(), nullable=False),
        sa.Column("user_prompt_template", sa.Text(), nullable=False),
        sa.Column("output_schema_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("version", sa.String(length=40), nullable=False),
        sa.Column("status", sa.Enum("draft", "active", "paused", "archived", name="llmprompttemplatestatus"), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_by", sa.String(length=120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_llm_prompt_templates_name", "llm_prompt_templates", ["name"])
    op.create_index("ix_llm_prompt_templates_task_type", "llm_prompt_templates", ["task_type"])
    op.create_index("ix_llm_prompt_templates_provider", "llm_prompt_templates", ["provider"])
    op.create_index("ix_llm_prompt_templates_status", "llm_prompt_templates", ["status"])
    op.create_index("ix_llm_prompt_templates_is_default", "llm_prompt_templates", ["is_default"])
    op.create_index(
        "uq_llm_prompt_templates_active_default_task",
        "llm_prompt_templates",
        ["task_type"],
        unique=True,
        postgresql_where=sa.text("status = 'active' AND is_default = true"),
    )


def downgrade() -> None:
    op.drop_index("uq_llm_prompt_templates_active_default_task", table_name="llm_prompt_templates")
    op.drop_index("ix_llm_prompt_templates_is_default", table_name="llm_prompt_templates")
    op.drop_index("ix_llm_prompt_templates_status", table_name="llm_prompt_templates")
    op.drop_index("ix_llm_prompt_templates_provider", table_name="llm_prompt_templates")
    op.drop_index("ix_llm_prompt_templates_task_type", table_name="llm_prompt_templates")
    op.drop_index("ix_llm_prompt_templates_name", table_name="llm_prompt_templates")
    op.drop_table("llm_prompt_templates")
    sa.Enum(name="llmprompttemplatestatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="llmprompttasktype").drop(op.get_bind(), checkfirst=True)
