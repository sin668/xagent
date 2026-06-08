from datetime import UTC, datetime
from uuid import uuid4

from app.models import LeadCleanupSuggestion, ReviewLog
from app.models.enums import LeadCleanupSuggestionReviewStatus, LeadCleanupSuggestionType
from app.services.lead_cleanup import LeadCleanupSuggestionService
from app.services.phase3_metrics import Phase3CleanupMetricsService


class FakeAuditSession:
    def __init__(self):
        self.added = []

    def add(self, item):
        self.added.append(item)


class FakeMetricsSession:
    def __init__(self, suggestions):
        self.suggestions = suggestions

    def scalars(self, statement):
        return FakeScalarResult(self.suggestions)


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
        "suggestion_type": LeadCleanupSuggestionType.STRONG_DUPLICATE,
        "target_lead_id": uuid4(),
        "confidence_score": 0.9,
        "reason": "公开证据显示重复。",
        "evidence_json": {"source": "agent_cleanup"},
        "recommended_action": "人工确认后执行清洗。",
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


def test_audit_suggestion_created_records_source_evidence_actor_and_action() -> None:
    suggestion = build_suggestion()
    session = FakeAuditSession()
    service = LeadCleanupSuggestionService(session)

    audit = service.audit_suggestion_created(
        suggestion,
        actor="cleanup-agent",
        result="created",
        evidence_note="公开来源生成清洗建议。",
    )

    assert isinstance(audit, ReviewLog)
    assert audit.action == "lead_cleanup_suggestion_created"
    assert audit.agent_name == "lead-cleanup-suggestion"
    assert audit.reviewer == "cleanup-agent"
    assert audit.task_id == str(suggestion.id)
    assert "suggestion_type=strong_duplicate" in audit.input_ref
    assert audit.result == "created"
    assert audit.error_message == "公开来源生成清洗建议。"
    assert audit in session.added


def test_cleanup_metrics_separate_created_approved_and_executed_counts() -> None:
    suggestions = [
        build_suggestion(review_status=LeadCleanupSuggestionReviewStatus.PENDING),
        build_suggestion(
            suggestion_type=LeadCleanupSuggestionType.MERGE_CONTACT_METHOD,
            review_status=LeadCleanupSuggestionReviewStatus.APPROVED,
            reviewer_id="admin-a",
            reviewed_at=datetime(2026, 6, 4, tzinfo=UTC),
        ),
        build_suggestion(
            suggestion_type=LeadCleanupSuggestionType.STRONG_DUPLICATE,
            review_status=LeadCleanupSuggestionReviewStatus.EXECUTED,
            reviewer_id="admin-a",
            reviewed_at=datetime(2026, 6, 4, tzinfo=UTC),
            executed_by="admin-a",
            executed_at=datetime(2026, 6, 4, tzinfo=UTC),
        ),
        build_suggestion(
            suggestion_type=LeadCleanupSuggestionType.POSSIBLE_DUPLICATE,
            review_status=LeadCleanupSuggestionReviewStatus.EXECUTED,
            reviewer_id="admin-a",
            reviewed_at=datetime(2026, 6, 4, tzinfo=UTC),
            executed_by="admin-a",
            executed_at=datetime(2026, 6, 4, tzinfo=UTC),
        ),
        build_suggestion(
            suggestion_type=LeadCleanupSuggestionType.RESTORE_FROM_WATCH,
            review_status=LeadCleanupSuggestionReviewStatus.EXECUTED,
            reviewer_id="compliance-a",
            reviewed_at=datetime(2026, 6, 4, tzinfo=UTC),
            executed_by="compliance-a",
            executed_at=datetime(2026, 6, 4, tzinfo=UTC),
        ),
        build_suggestion(
            suggestion_type=LeadCleanupSuggestionType.CONFIRM_INVALID,
            review_status=LeadCleanupSuggestionReviewStatus.EXECUTED,
            reviewer_id="ops-a",
            reviewed_at=datetime(2026, 6, 4, tzinfo=UTC),
            executed_by="ops-a",
            executed_at=datetime(2026, 6, 4, tzinfo=UTC),
        ),
        build_suggestion(
            suggestion_type=LeadCleanupSuggestionType.CONFIRM_INVALID,
            review_status=LeadCleanupSuggestionReviewStatus.REJECTED,
            reviewer_id="ops-b",
            reviewed_at=datetime(2026, 6, 4, tzinfo=UTC),
        ),
    ]
    service = Phase3CleanupMetricsService(FakeMetricsSession(suggestions))

    metrics = service.cleanup_metrics()

    assert metrics["created_count"] == 7
    assert metrics["approved_count"] == 5
    assert metrics["executed_count"] == 4
    assert metrics["rejected_count"] == 1
    assert metrics["pending_count"] == 1
    assert metrics["adoption_rate"] == 5 / 7
    assert metrics["execution_rate"] == 4 / 7
    assert metrics["duplicate_merge_rate"] == 2 / 7
    assert metrics["watch_restore_rate"] == 1 / 7
    assert metrics["invalid_confirm_rate"] == 1 / 7
    assert metrics["auto_suggestion_not_equal_executed"] is True


def test_cleanup_metrics_return_zero_rates_when_no_suggestions_exist() -> None:
    service = Phase3CleanupMetricsService(FakeMetricsSession([]))

    metrics = service.cleanup_metrics()

    assert metrics["created_count"] == 0
    assert metrics["approved_count"] == 0
    assert metrics["executed_count"] == 0
    assert metrics["adoption_rate"] == 0
    assert metrics["duplicate_merge_rate"] == 0
    assert metrics["watch_restore_rate"] == 0
    assert metrics["invalid_confirm_rate"] == 0
