"""Extend llm prompt template governance fields.

Revision ID: 20260605_0029
Revises: 20260604_0028
Create Date: 2026-06-05
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260605_0029"
down_revision = "20260604_0028"
branch_labels = None
depends_on = None


OLD_TASK_TYPE_VALUES = ("SOURCE_DISCOVERY", "LEAD_EXTRACTION", "LEAD_GRADING")
NEW_TASK_TYPE_VALUES = (
    *OLD_TASK_TYPE_VALUES,
    "EMAIL_REPLY_DRAFT",
    "EMAIL_REPLY_AUTO_SEND_CHECK",
    "EMAIL_REPLY_KNOWLEDGE_RETRIEVAL",
    "EMAIL_REPLY_SEND",
)


def upgrade() -> None:
    bind = op.get_bind()
    for value in NEW_TASK_TYPE_VALUES[len(OLD_TASK_TYPE_VALUES) :]:
        op.execute(sa.text(f"ALTER TYPE llmprompttasktype ADD VALUE IF NOT EXISTS '{value}'"))

    op.add_column("llm_prompt_templates", sa.Column("source_file_path", sa.String(length=500), nullable=True))
    op.add_column("llm_prompt_templates", sa.Column("source_file_hash", sa.String(length=128), nullable=True))
    op.add_column("llm_prompt_templates", sa.Column("migration_batch_id", sa.String(length=120), nullable=True))
    op.add_column("llm_prompt_templates", sa.Column("parent_template_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("llm_prompt_templates", sa.Column("published_by", sa.String(length=120), nullable=True))
    op.add_column("llm_prompt_templates", sa.Column("published_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("llm_prompt_templates", sa.Column("change_summary", sa.Text(), nullable=True))
    op.add_column("llm_prompt_templates", sa.Column("rollback_from_template_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("llm_prompt_templates", sa.Column("validation_status", sa.String(length=40), nullable=True))
    op.add_column("llm_prompt_templates", sa.Column("validation_errors_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True))

    op.create_index("ix_llm_prompt_templates_source_file_path", "llm_prompt_templates", ["source_file_path"])
    op.create_index("ix_llm_prompt_templates_source_file_hash", "llm_prompt_templates", ["source_file_hash"])
    op.create_index("ix_llm_prompt_templates_migration_batch_id", "llm_prompt_templates", ["migration_batch_id"])
    op.create_index("ix_llm_prompt_templates_validation_status", "llm_prompt_templates", ["validation_status"])
    op.create_foreign_key(
        "fk_llm_prompt_templates_parent_template_id",
        "llm_prompt_templates",
        "llm_prompt_templates",
        ["parent_template_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_llm_prompt_templates_rollback_from_template_id",
        "llm_prompt_templates",
        "llm_prompt_templates",
        ["rollback_from_template_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Ensure SQLAlchemy/Alembic does not keep an obsolete enum snapshot in this transaction.
    bind.execute(sa.text("SELECT 1"))


def downgrade() -> None:
    op.drop_constraint("fk_llm_prompt_templates_rollback_from_template_id", "llm_prompt_templates", type_="foreignkey")
    op.drop_constraint("fk_llm_prompt_templates_parent_template_id", "llm_prompt_templates", type_="foreignkey")
    op.drop_index("ix_llm_prompt_templates_validation_status", table_name="llm_prompt_templates")
    op.drop_index("ix_llm_prompt_templates_migration_batch_id", table_name="llm_prompt_templates")
    op.drop_index("ix_llm_prompt_templates_source_file_hash", table_name="llm_prompt_templates")
    op.drop_index("ix_llm_prompt_templates_source_file_path", table_name="llm_prompt_templates")

    op.drop_column("llm_prompt_templates", "validation_errors_json")
    op.drop_column("llm_prompt_templates", "validation_status")
    op.drop_column("llm_prompt_templates", "rollback_from_template_id")
    op.drop_column("llm_prompt_templates", "change_summary")
    op.drop_column("llm_prompt_templates", "published_at")
    op.drop_column("llm_prompt_templates", "published_by")
    op.drop_column("llm_prompt_templates", "parent_template_id")
    op.drop_column("llm_prompt_templates", "migration_batch_id")
    op.drop_column("llm_prompt_templates", "source_file_hash")
    op.drop_column("llm_prompt_templates", "source_file_path")

    old_enum = postgresql.ENUM(*OLD_TASK_TYPE_VALUES, name="llmprompttasktype_old")
    old_enum.create(op.get_bind(), checkfirst=True)
    op.execute(
        sa.text(
            "ALTER TABLE llm_prompt_templates "
            "ALTER COLUMN task_type TYPE llmprompttasktype_old "
            "USING task_type::text::llmprompttasktype_old"
        )
    )
    op.execute(sa.text("DROP TYPE llmprompttasktype"))
    op.execute(sa.text("ALTER TYPE llmprompttasktype_old RENAME TO llmprompttasktype"))
