from pathlib import Path

from app.models.enums import FailedCaseType
from app.services.failed_cases import FailedCaseService


API_ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = API_ROOT / "alembic" / "versions" / "20260529_0017_failed_cases.py"


def test_failed_cases_migration_declares_required_table_and_fields() -> None:
    assert MIGRATION_PATH.exists()
    migration = MIGRATION_PATH.read_text(encoding="utf-8")

    assert 'revision = "20260529_0017"' in migration
    assert 'down_revision = "20260529_0016"' in migration
    assert '"failed_cases"' in migration
    for field in [
        "case_type",
        "source_url",
        "risk_level",
        "related_task_type",
        "related_object_type",
        "related_object_id",
        "failure_reason",
        "evidence_note",
        "raw_output_json",
        "usable_for_rag",
        "touch_queue_allowed",
    ]:
        assert field in migration


def test_failed_case_model_and_router_are_registered() -> None:
    models_init = (API_ROOT / "app" / "models" / "__init__.py").read_text(encoding="utf-8")
    main_py = (API_ROOT / "app" / "main.py").read_text(encoding="utf-8")

    assert "FailedCase" in models_init
    assert "FailedCaseType" in models_init
    assert "failed_cases_router" in main_py


def test_failure_reason_classifier_covers_required_categories() -> None:
    samples = {
        "fetch_failed": "公开页面读取失败 timeout",
        "schema_invalid": "LLM 输出 schema_version 不正确",
        "missing_evidence": "LLM 输出缺少来源证据",
        "risk_blocked": "High/Forbidden 来源不得写入 staging",
        "duplicate": "强重复线索不得晋级 core",
        "llm_suspected_fabrication": "联系方式不在公开文本中，不得写入 staging",
    }

    for expected, reason in samples.items():
        assert FailedCaseService.classify_failure_reason(reason) == FailedCaseType(expected)


def test_failed_case_rag_payload_preserves_source_and_never_allows_touch_queue() -> None:
    payload = FailedCaseService.build_failed_case_payload(
        case_type=FailedCaseType.LLM_SUSPECTED_FABRICATION,
        source_url="https://dealer.example/contact",
        risk_level="Medium",
        related_task_type="lead_extraction",
        related_object_type="candidate_url",
        related_object_id="candidate-1",
        failure_reason="联系方式不在公开文本中",
        evidence_note="模型输出了页面中不存在的手机号",
        raw_output_json={"phone": "+7 999 000 00 00"},
        model_name="test-model",
        prompt_version="lead-extraction-v1",
    )

    assert payload["usable_for_rag"] is True
    assert payload["touch_queue_allowed"] is False
    assert payload["source_url"] == "https://dealer.example/contact"
    assert payload["raw_output_json"] == {"phone": "+7 999 000 00 00"}


def test_failed_case_api_contract_exists() -> None:
    api_file = API_ROOT / "app" / "api" / "failed_cases.py"

    assert api_file.exists()
    text = api_file.read_text(encoding="utf-8")
    assert '@router.post("",' in text
    assert '@router.get("",' in text


def test_llm_services_record_failed_cases_on_validation_error() -> None:
    extraction_service = (API_ROOT / "app" / "services" / "llm_lead_extraction.py").read_text(encoding="utf-8")
    grading_service = (API_ROOT / "app" / "services" / "llm_lead_grading.py").read_text(encoding="utf-8")

    assert "FailedCaseService" in extraction_service
    assert "record_failed_case" in extraction_service
    assert "FailedCaseService" in grading_service
    assert "record_failed_case" in grading_service
