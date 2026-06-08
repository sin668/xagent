from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.models import LeadCleanupSuggestion, ReviewLog
from app.models.enums import LeadCleanupSuggestionReviewStatus, LeadCleanupSuggestionType
from app.schemas.lead_cleanup import LeadCleanupSuggestionReviewRequest
from app.services.lead_cleanup import LeadCleanupSuggestionService


client = TestClient(app)


class FakeSession:
    def __init__(self, suggestion=None):
        self.suggestion = suggestion
        self.added = []
        self.flushed = False
        self.committed = False

    def scalar(self, statement):
        return self.suggestion

    def add(self, item):
        self.added.append(item)

    def flush(self):
        self.flushed = True

    def commit(self):
        self.committed = True


def build_suggestion(**overrides) -> LeadCleanupSuggestion:
    payload = {
        "id": uuid4(),
        "cleanup_run_id": uuid4(),
        "staging_lead_id": uuid4(),
        "suggestion_type": LeadCleanupSuggestionType.STRONG_DUPLICATE,
        "target_lead_id": uuid4(),
        "confidence_score": 0.92,
        "reason": "客户名称和联系方式强重复。",
        "evidence_json": {"matched_fields": ["customer_name", "contact"]},
        "recommended_action": "人工确认后归并联系方式。",
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


def test_cleanup_review_routes_are_registered_with_execute_endpoint() -> None:
    openapi = client.get("/openapi.json").json()
    paths = openapi["paths"]

    assert "/lead-cleanup/suggestions/{suggestion_id}/approve" in paths
    assert "patch" in paths["/lead-cleanup/suggestions/{suggestion_id}/approve"]
    assert "/lead-cleanup/suggestions/{suggestion_id}/reject" in paths
    assert "patch" in paths["/lead-cleanup/suggestions/{suggestion_id}/reject"]
    assert "/lead-cleanup/suggestions/{suggestion_id}/execute" in paths
    assert "post" in paths["/lead-cleanup/suggestions/{suggestion_id}/execute"]


def test_review_request_requires_actor_role_and_note_for_audit() -> None:
    request = LeadCleanupSuggestionReviewRequest(
        actor="ops-a",
        actor_role="operations",
        review_note="证据充分，人工确认。",
    )

    assert request.actor == "ops-a"
    assert request.actor_role == "operations"
    assert request.review_note == "证据充分，人工确认。"


def test_approve_pending_suggestion_records_reviewer_time_and_audit_without_execution() -> None:
    now = datetime(2026, 6, 4, 12, tzinfo=UTC)
    suggestion = build_suggestion()
    session = FakeSession(suggestion)
    service = LeadCleanupSuggestionService(session)

    updated = service.approve_suggestion(
        suggestion.id,
        actor="ops-a",
        actor_role="operations",
        review_note="强重复证据充分。",
        now=now,
    )

    assert updated.review_status == LeadCleanupSuggestionReviewStatus.APPROVED
    assert updated.reviewer_id == "ops-a"
    assert updated.reviewed_at == now
    assert updated.executed_by is None
    assert updated.executed_at is None
    audit = next(item for item in session.added if isinstance(item, ReviewLog))
    assert audit.action == "lead_cleanup_suggestion_approved"
    assert audit.reviewer == "ops-a"
    assert audit.task_id == str(suggestion.id)
    assert "suggestion_type=strong_duplicate" in audit.input_ref
    assert audit.result == "approved"
    assert audit.error_message == "强重复证据充分。"
    assert session.flushed is True


def test_reject_pending_suggestion_records_reviewer_time_and_audit_without_execution() -> None:
    now = datetime(2026, 6, 4, 13, tzinfo=UTC)
    suggestion = build_suggestion(suggestion_type=LeadCleanupSuggestionType.NEEDS_MANUAL_REVIEW)
    session = FakeSession(suggestion)
    service = LeadCleanupSuggestionService(session)

    updated = service.reject_suggestion(
        suggestion.id,
        actor="ops-a",
        actor_role="operations",
        review_note="证据不足，不采纳。",
        now=now,
    )

    assert updated.review_status == LeadCleanupSuggestionReviewStatus.REJECTED
    assert updated.reviewer_id == "ops-a"
    assert updated.reviewed_at == now
    assert updated.executed_by is None
    assert updated.executed_at is None
    audit = next(item for item in session.added if isinstance(item, ReviewLog))
    assert audit.action == "lead_cleanup_suggestion_rejected"
    assert audit.result == "rejected"
    assert audit.error_message == "证据不足，不采纳。"


def test_restore_watch_or_invalid_cleanup_requires_compliance_or_admin_role() -> None:
    suggestion = build_suggestion(suggestion_type=LeadCleanupSuggestionType.RESTORE_FROM_WATCH)
    service = LeadCleanupSuggestionService(FakeSession(suggestion))

    try:
        service.approve_suggestion(
            suggestion.id,
            actor="ops-a",
            actor_role="operations",
            review_note="运营尝试恢复。",
            now=datetime(2026, 6, 4, tzinfo=UTC),
        )
    except PermissionError as exc:
        assert "恢复 Watch/Invalid 必须由合规或管理员确认" in str(exc)
    else:
        raise AssertionError("恢复 Watch/Invalid 不应由运营确认")


def test_possible_duplicate_and_customer_level_merge_require_admin_role() -> None:
    for suggestion_type in (
        LeadCleanupSuggestionType.POSSIBLE_DUPLICATE,
        LeadCleanupSuggestionType.MERGE_CONTACT_METHOD,
        LeadCleanupSuggestionType.MERGE_SOURCE_EVIDENCE,
    ):
        suggestion = build_suggestion(suggestion_type=suggestion_type)
        service = LeadCleanupSuggestionService(FakeSession(suggestion))
        try:
            service.approve_suggestion(
                suggestion.id,
                actor="ops-a",
                actor_role="operations",
                review_note="运营尝试确认疑似重复或客户级归并。",
                now=datetime(2026, 6, 4, tzinfo=UTC),
            )
        except PermissionError as exc:
            assert "疑似重复和客户级归并需要管理员确认" in str(exc)
        else:
            raise AssertionError(f"{suggestion_type.value} 不应由运营确认")


def test_admin_can_approve_possible_duplicate_but_still_does_not_execute() -> None:
    suggestion = build_suggestion(suggestion_type=LeadCleanupSuggestionType.POSSIBLE_DUPLICATE)
    session = FakeSession(suggestion)
    service = LeadCleanupSuggestionService(session)

    updated = service.approve_suggestion(
        suggestion.id,
        actor="admin-a",
        actor_role="admin",
        review_note="管理员确认疑似重复。",
        now=datetime(2026, 6, 4, tzinfo=UTC),
    )

    assert updated.review_status == LeadCleanupSuggestionReviewStatus.APPROVED
    assert updated.executed_by is None
    assert updated.executed_at is None
    assert all(not getattr(item, "action", "").endswith("_executed") for item in session.added)


def test_review_blocks_non_pending_suggestion() -> None:
    suggestion = build_suggestion(review_status=LeadCleanupSuggestionReviewStatus.EXECUTED, executed_by="ops-a")
    service = LeadCleanupSuggestionService(FakeSession(suggestion))

    try:
        service.reject_suggestion(
            suggestion.id,
            actor="ops-b",
            actor_role="operations",
            review_note="尝试重新拒绝已执行建议。",
            now=datetime(2026, 6, 4, tzinfo=UTC),
        )
    except ValueError as exc:
        assert "只有 pending 清洗建议可以人工确认或拒绝" in str(exc)
    else:
        raise AssertionError("已执行建议不得重新确认/拒绝")
