from pathlib import Path

from pydantic import ValidationError

from app.models.enums import LLMPromptTemplateStatus, LLMPromptTaskType
from app.services.llm_prompt_templates import LLMPromptTemplateService


API_ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = API_ROOT / "alembic" / "versions" / "20260602_0020_create_llm_prompt_templates.py"


def test_llm_prompt_template_migration_declares_required_table_and_fields() -> None:
    assert MIGRATION_PATH.exists()
    migration = MIGRATION_PATH.read_text(encoding="utf-8")

    assert 'revision = "20260602_0020"' in migration
    assert 'down_revision = "20260529_0019"' in migration
    assert '"llm_prompt_templates"' in migration
    for field_name in (
        "name",
        "task_type",
        "provider",
        "model",
        "system_prompt",
        "user_prompt_template",
        "output_schema_json",
        "version",
        "status",
        "is_default",
        "created_by",
        "created_at",
        "updated_at",
    ):
        assert field_name in migration


def test_llm_prompt_template_model_and_schema_are_registered() -> None:
    models_init = (API_ROOT / "app" / "models" / "__init__.py").read_text(encoding="utf-8")
    schema_file = API_ROOT / "app" / "schemas" / "llm_prompt_template.py"

    assert "LLMPromptTemplate" in models_init
    assert schema_file.exists()


def test_llm_prompt_template_schema_rejects_invalid_status() -> None:
    from app.schemas.llm_prompt_template import LLMPromptTemplateCreate

    try:
        LLMPromptTemplateCreate(
            name="source_discovery_default",
            task_type="SOURCE_DISCOVERY",
            provider="deepseek",
            model="deepseek-chat",
            system_prompt="只发现来源，不触达。",
            user_prompt_template="国家: {country}",
            output_schema_json={"type": "object"},
            version="v1.0",
            status="enabled",
            is_default=True,
            created_by="codex",
        )
    except ValidationError as exc:
        assert "status" in str(exc)
    else:
        raise AssertionError("LLMPromptTemplateCreate should reject invalid status")


def test_prompt_template_status_and_task_type_enums_are_available() -> None:
    assert LLMPromptTemplateStatus.ACTIVE == "active"
    assert LLMPromptTaskType.SOURCE_DISCOVERY == "SOURCE_DISCOVERY"
    assert LLMPromptTaskType.LEAD_EXTRACTION == "LEAD_EXTRACTION"
    assert LLMPromptTaskType.LEAD_GRADING == "LEAD_GRADING"


def test_only_one_active_default_template_is_allowed_per_task_type() -> None:
    existing_templates = [
        {
            "task_type": LLMPromptTaskType.SOURCE_DISCOVERY,
            "status": LLMPromptTemplateStatus.ACTIVE,
            "is_default": True,
        }
    ]

    try:
        LLMPromptTemplateService.validate_default_template_uniqueness(
            existing_templates=existing_templates,
            task_type=LLMPromptTaskType.SOURCE_DISCOVERY,
            status=LLMPromptTemplateStatus.ACTIVE,
            is_default=True,
        )
    except ValueError as exc:
        assert "同一 task_type 只能有一个 active 默认模板" in str(exc)
    else:
        raise AssertionError("Duplicate active default prompt template should be rejected")


def test_paused_or_non_default_template_does_not_conflict_with_active_default() -> None:
    existing_templates = [
        {
            "task_type": LLMPromptTaskType.SOURCE_DISCOVERY,
            "status": LLMPromptTemplateStatus.ACTIVE,
            "is_default": True,
        }
    ]

    LLMPromptTemplateService.validate_default_template_uniqueness(
        existing_templates=existing_templates,
        task_type=LLMPromptTaskType.SOURCE_DISCOVERY,
        status=LLMPromptTemplateStatus.PAUSED,
        is_default=True,
    )
    LLMPromptTemplateService.validate_default_template_uniqueness(
        existing_templates=existing_templates,
        task_type=LLMPromptTaskType.SOURCE_DISCOVERY,
        status=LLMPromptTemplateStatus.ACTIVE,
        is_default=False,
    )
