"""Scope llm prompt default by provider and model.

Revision ID: 20260605_0034
Revises: 20260605_0033
Create Date: 2026-06-05
"""

from alembic import op
import sqlalchemy as sa


revision = "20260605_0034"
down_revision = "20260605_0033"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("uq_llm_prompt_templates_active_default_task", table_name="llm_prompt_templates")
    op.create_index(
        "uq_llm_prompt_templates_active_default_scope",
        "llm_prompt_templates",
        ["task_type", "provider", "model"],
        unique=True,
        postgresql_where=sa.text("status = 'active' AND is_default = true"),
    )


def downgrade() -> None:
    op.drop_index("uq_llm_prompt_templates_active_default_scope", table_name="llm_prompt_templates")
    op.create_index(
        "uq_llm_prompt_templates_active_default_task",
        "llm_prompt_templates",
        ["task_type"],
        unique=True,
        postgresql_where=sa.text("status = 'active' AND is_default = true"),
    )
