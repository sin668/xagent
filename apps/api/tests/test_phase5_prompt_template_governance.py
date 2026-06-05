from pathlib import Path

from sqlalchemy import inspect

from app.models.enums import LLMPromptTaskType
from app.models.llm_prompt_template import LLMPromptTemplate


API_ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = API_ROOT / "alembic" / "versions" / "20260605_0029_extend_llm_prompt_templates_governance.py"


def test_phase5_prompt_task_type_enum_includes_email_reply_tasks() -> None:
    assert LLMPromptTaskType.EMAIL_REPLY_DRAFT == "EMAIL_REPLY_DRAFT"
    assert LLMPromptTaskType.EMAIL_REPLY_AUTO_SEND_CHECK == "EMAIL_REPLY_AUTO_SEND_CHECK"
    assert LLMPromptTaskType.EMAIL_REPLY_KNOWLEDGE_RETRIEVAL == "EMAIL_REPLY_KNOWLEDGE_RETRIEVAL"
    assert LLMPromptTaskType.EMAIL_REPLY_SEND == "EMAIL_REPLY_SEND"


def test_phase5_prompt_template_model_declares_governance_columns() -> None:
    columns = inspect(LLMPromptTemplate).columns

    for column_name in (
        "source_file_path",
        "source_file_hash",
        "migration_batch_id",
        "parent_template_id",
        "published_by",
        "published_at",
        "change_summary",
        "rollback_from_template_id",
        "validation_status",
        "validation_errors_json",
    ):
        assert column_name in columns


def test_phase5_prompt_template_governance_migration_declares_upgrade_and_downgrade() -> None:
    assert MIGRATION_PATH.exists()
    migration = MIGRATION_PATH.read_text(encoding="utf-8")

    assert 'revision = "20260605_0029"' in migration
    assert 'down_revision = "20260604_0028"' in migration

    for enum_value in (
        "EMAIL_REPLY_DRAFT",
        "EMAIL_REPLY_AUTO_SEND_CHECK",
        "EMAIL_REPLY_KNOWLEDGE_RETRIEVAL",
        "EMAIL_REPLY_SEND",
    ):
        assert enum_value in migration

    for column_name in (
        "source_file_path",
        "source_file_hash",
        "migration_batch_id",
        "parent_template_id",
        "published_by",
        "published_at",
        "change_summary",
        "rollback_from_template_id",
        "validation_status",
        "validation_errors_json",
    ):
        assert column_name in migration

    assert "drop_column" in migration
    assert "rollback_from_template_id" in migration
    assert "parent_template_id" in migration
