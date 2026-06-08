from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.dialects import postgresql

from app.main import app
from app.models import LeadCleanupSuggestion
from app.models.enums import LeadCleanupSuggestionReviewStatus, LeadCleanupSuggestionType
from app.schemas.lead_cleanup import LeadCleanupSuggestionListResponse, LeadCleanupSuggestionResponse
from app.services.lead_cleanup import LeadCleanupSuggestionQueryFilters, LeadCleanupSuggestionService


client = TestClient(app)


class FakeSession:
    def __init__(self, *, scalars_result=None, scalar_result=None):
        self.scalars_result = scalars_result or []
        self.scalar_result = scalar_result
        self.scalars_statements = []
        self.scalar_statements = []

    def scalars(self, statement):
        self.scalars_statements.append(statement)
        return FakeScalarResult(self.scalars_result)

    def scalar(self, statement):
        self.scalar_statements.append(statement)
        return self.scalar_result


class FakeScalarResult:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return self.rows


def build_suggestion(**overrides) -> LeadCleanupSuggestion:
    payload = {
        "id": uuid4(),
        "cleanup_run_id": uuid4(),
        "staging_lead_id": uuid4(),
        "suggestion_type": LeadCleanupSuggestionType.POSSIBLE_DUPLICATE,
        "target_lead_id": uuid4(),
        "confidence_score": 0.82,
        "reason": "客户名称和来源域名相似，建议人工确认。",
        "evidence_json": {"matched_fields": ["customer_name", "source_domain"]},
        "recommended_action": "人工确认是否归并。",
        "review_status": LeadCleanupSuggestionReviewStatus.PENDING,
        "reviewer_id": None,
        "reviewed_at": None,
        "executed_by": None,
        "executed_at": None,
        "execution_note": None,
        "created_at": datetime(2026, 6, 4, tzinfo=UTC),
        "updated_at": datetime(2026, 6, 4, tzinfo=UTC),
    }
    payload.update(overrides)
    return LeadCleanupSuggestion(**payload)


def test_lead_cleanup_suggestions_query_routes_are_registered_with_execute_endpoint() -> None:
    openapi = client.get("/openapi.json").json()
    paths = openapi["paths"]

    assert "/lead-cleanup/suggestions" in paths
    assert "get" in paths["/lead-cleanup/suggestions"]
    assert "/lead-cleanup/suggestions/{suggestion_id}" in paths
    assert "get" in paths["/lead-cleanup/suggestions/{suggestion_id}"]
    assert "/lead-cleanup/suggestions/{suggestion_id}/execute" in paths
    assert "post" in paths["/lead-cleanup/suggestions/{suggestion_id}/execute"]


def test_query_filters_default_to_pending_review_status() -> None:
    filters = LeadCleanupSuggestionQueryFilters()

    assert filters.review_status == LeadCleanupSuggestionReviewStatus.PENDING


def test_list_suggestions_query_supports_type_status_confidence_and_lead_filters() -> None:
    session = FakeSession(scalars_result=[build_suggestion()])
    service = LeadCleanupSuggestionService(session)
    filters = LeadCleanupSuggestionQueryFilters(
        suggestion_type=LeadCleanupSuggestionType.POSSIBLE_DUPLICATE,
        review_status=LeadCleanupSuggestionReviewStatus.PENDING,
        min_confidence=0.7,
        max_confidence=0.95,
        lead_id=uuid4(),
        limit=20,
    )

    rows = service.list_suggestions(filters)

    assert len(rows) == 1
    compiled = str(session.scalars_statements[0].compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))
    assert "lead_cleanup_suggestions" in compiled
    assert "possible_duplicate" in compiled
    assert "pending" in compiled
    assert "confidence_score >= 0.7" in compiled
    assert "confidence_score <= 0.95" in compiled
    assert "staging_lead_id" in compiled
    assert "LIMIT 20" in compiled


def test_default_list_query_only_returns_pending_suggestions() -> None:
    session = FakeSession(scalars_result=[])
    service = LeadCleanupSuggestionService(session)

    service.list_suggestions(LeadCleanupSuggestionQueryFilters())

    compiled = str(session.scalars_statements[0].compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))
    assert "review_status = 'pending'" in compiled


def test_get_suggestion_detail_returns_reason_evidence_action_and_target_lead() -> None:
    suggestion = build_suggestion()
    session = FakeSession(scalar_result=suggestion)
    service = LeadCleanupSuggestionService(session)

    detail = service.get_suggestion(suggestion.id)

    assert detail.id == suggestion.id
    assert detail.reason == "客户名称和来源域名相似，建议人工确认。"
    assert detail.evidence_json == {"matched_fields": ["customer_name", "source_domain"]}
    assert detail.recommended_action == "人工确认是否归并。"
    assert detail.target_lead_id == suggestion.target_lead_id


def test_get_suggestion_detail_raises_for_missing_record() -> None:
    service = LeadCleanupSuggestionService(FakeSession(scalar_result=None))

    try:
        service.get_suggestion(uuid4())
    except ValueError as exc:
        assert "清洗建议不存在" in str(exc)
    else:
        raise AssertionError("missing cleanup suggestion should raise")


def test_cleanup_response_schemas_wrap_list_and_detail_payloads() -> None:
    suggestion = build_suggestion()
    detail = LeadCleanupSuggestionResponse.model_validate(suggestion)
    response = LeadCleanupSuggestionListResponse(items=[detail], total=1)

    assert response.total == 1
    assert response.items[0].id == suggestion.id
    assert response.items[0].reason == suggestion.reason
