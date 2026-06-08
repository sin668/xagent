from pathlib import Path

from pydantic import ValidationError
from sqlalchemy import insert, select
from sqlalchemy.dialects import postgresql

from app.db.base import Base
from app.models import LeadCleanupRun, LeadCleanupSuggestion
from app.models.enums import LeadCleanupRunStatus, LeadCleanupSuggestionReviewStatus, LeadCleanupSuggestionType
from app.schemas.lead_cleanup import LeadCleanupRunCreate, LeadCleanupSuggestionCreate, LeadCleanupSuggestionUpdate


API_ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = API_ROOT / "alembic" / "versions" / "20260604_0026_create_lead_cleanup_tables.py"


def test_lead_cleanup_migration_declares_required_tables_and_fields() -> None:
    assert MIGRATION_PATH.exists()
    migration = MIGRATION_PATH.read_text(encoding="utf-8")

    assert 'revision = "20260604_0026"' in migration
    assert 'down_revision = "20260604_0025"' in migration
    assert '"lead_cleanup_runs"' in migration
    assert '"lead_cleanup_suggestions"' in migration

    for field_name in (
        "trigger_source",
        "status",
        "input_filter_json",
        "output_summary_json",
        "llm_provider",
        "llm_model",
        "prompt_template_id",
        "started_at",
        "finished_at",
        "created_at",
        "updated_at",
    ):
        assert field_name in migration

    for field_name in (
        "cleanup_run_id",
        "staging_lead_id",
        "suggestion_type",
        "target_lead_id",
        "confidence_score",
        "reason",
        "evidence_json",
        "recommended_action",
        "review_status",
        "reviewer_id",
        "reviewed_at",
        "executed_by",
        "executed_at",
        "execution_note",
        "created_at",
        "updated_at",
    ):
        assert field_name in migration
    assert "customer_id" not in migration
    assert '"customers"' not in migration


def test_lead_cleanup_models_are_registered_for_alembic_metadata() -> None:
    table_names = set(Base.metadata.tables.keys())
    models_init = (API_ROOT / "app" / "models" / "__init__.py").read_text(encoding="utf-8")

    assert "lead_cleanup_runs" in table_names
    assert "lead_cleanup_suggestions" in table_names
    assert "LeadCleanupRun" in models_init
    assert "LeadCleanupSuggestion" in models_init
    assert "LeadCleanupSuggestionType" in models_init
    assert "LeadCleanupSuggestionReviewStatus" in models_init


def test_cleanup_suggestion_types_cover_frozen_story_values() -> None:
    expected_values = {
        "strong_duplicate",
        "possible_duplicate",
        "merge_contact_method",
        "merge_source_evidence",
        "restore_from_watch",
        "confirm_invalid",
        "mark_abandoned",
        "needs_manual_review",
    }

    assert {item.value for item in LeadCleanupSuggestionType} == expected_values


def test_cleanup_suggestion_review_status_supports_pending_approved_rejected_executed() -> None:
    assert LeadCleanupSuggestionReviewStatus.PENDING.value == "pending"
    assert LeadCleanupSuggestionReviewStatus.APPROVED.value == "approved"
    assert LeadCleanupSuggestionReviewStatus.REJECTED.value == "rejected"
    assert LeadCleanupSuggestionReviewStatus.EXECUTED.value == "executed"


def test_cleanup_run_schema_defaults_to_pending_and_preserves_input_filter() -> None:
    payload = LeadCleanupRunCreate(
        trigger_source="scheduled_agent",
        input_filter_json={"grades": ["Watch", "Invalid"]},
        llm_provider="deepseek",
        llm_model="deepseek-chat",
    )

    assert payload.status == LeadCleanupRunStatus.PENDING
    assert payload.input_filter_json == {"grades": ["Watch", "Invalid"]}
    assert payload.output_summary_json is None


def test_cleanup_suggestion_schema_preserves_evidence_and_requires_reviewer_for_approval() -> None:
    payload = LeadCleanupSuggestionCreate(
        cleanup_run_id="11111111-1111-1111-1111-111111111111",
        staging_lead_id="22222222-2222-2222-2222-222222222222",
        suggestion_type=LeadCleanupSuggestionType.POSSIBLE_DUPLICATE,
        target_lead_id="33333333-3333-3333-3333-333333333333",
        confidence_score=0.76,
        reason="客户名称和官网域名相似，需要人工确认。",
        evidence_json={"matched_fields": ["customer_name", "source_domain"]},
        recommended_action="人工确认是否归并。",
    )

    assert payload.review_status == LeadCleanupSuggestionReviewStatus.PENDING
    assert payload.evidence_json == {"matched_fields": ["customer_name", "source_domain"]}

    try:
        LeadCleanupSuggestionUpdate(review_status=LeadCleanupSuggestionReviewStatus.APPROVED)
    except ValidationError as exc:
        assert "reviewer_id" in str(exc)
    else:
        raise AssertionError("approved cleanup suggestion should require reviewer_id")


def test_cleanup_suggestion_schema_requires_executor_for_executed_status() -> None:
    try:
        LeadCleanupSuggestionUpdate(review_status=LeadCleanupSuggestionReviewStatus.EXECUTED, reviewer_id="ops-a")
    except ValidationError as exc:
        assert "executed_by" in str(exc)
    else:
        raise AssertionError("executed cleanup suggestion should require executed_by")


def test_cleanup_models_can_compile_minimal_insert_and_select_sql() -> None:
    run_insert = insert(LeadCleanupRun).values(
        trigger_source="scheduled_agent",
        status=LeadCleanupRunStatus.PENDING,
        input_filter_json={"grades": ["Watch", "Invalid"]},
    )
    suggestion_insert = insert(LeadCleanupSuggestion).values(
        cleanup_run_id="11111111-1111-1111-1111-111111111111",
        staging_lead_id="22222222-2222-2222-2222-222222222222",
        suggestion_type=LeadCleanupSuggestionType.NEEDS_MANUAL_REVIEW,
        confidence_score=0.5,
        reason="信息不足，建议人工复核。",
        evidence_json={"reason": "missing_contact"},
        recommended_action="人工复核。",
        review_status=LeadCleanupSuggestionReviewStatus.PENDING,
    )
    query = select(LeadCleanupSuggestion).where(
        LeadCleanupSuggestion.review_status == LeadCleanupSuggestionReviewStatus.PENDING
    )

    compiled_run_insert = str(run_insert.compile(dialect=postgresql.dialect()))
    compiled_suggestion_insert = str(suggestion_insert.compile(dialect=postgresql.dialect()))
    compiled_query = str(query.compile(dialect=postgresql.dialect()))

    assert "INSERT INTO lead_cleanup_runs" in compiled_run_insert
    assert "INSERT INTO lead_cleanup_suggestions" in compiled_suggestion_insert
    assert "lead_cleanup_suggestions" in compiled_query
