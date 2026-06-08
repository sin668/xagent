from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.models import LeadCleanupSuggestion, ReviewLog, StagingLead
from app.models.enums import (
    CustomerGrade,
    CustomerType,
    LeadCleanupSuggestionReviewStatus,
    LeadCleanupSuggestionType,
    StagingQueueStatus,
    StagingReviewStatus,
)
from app.schemas.lead_cleanup import LeadCleanupSuggestionExecuteRequest
from app.services.lead_cleanup import LeadCleanupSuggestionService


client = TestClient(app)


class FakeSession:
    def __init__(self, *, suggestions=None, leads=None):
        self.suggestions = {item.id: item for item in suggestions or []}
        self.leads = {item.id: item for item in leads or []}
        self.added = []
        self.flushed = False
        self.committed = False
        self.deleted = []

    def scalar(self, statement):
        text = str(statement)
        if "lead_cleanup_suggestions" in text:
            return next(iter(self.suggestions.values()), None)
        if "staging_leads" in text:
            return next(iter(self.leads.values()), None)
        return None

    def add(self, item):
        self.added.append(item)

    def flush(self):
        self.flushed = True

    def commit(self):
        self.committed = True

    def delete(self, item):
        self.deleted.append(item)


class FakeLookupSession(FakeSession):
    def __init__(self, *, suggestions=None, leads=None):
        super().__init__(suggestions=suggestions, leads=leads)
        self.lead_lookup_queue = list(leads or [])

    def scalar(self, statement):
        text = str(statement)
        if "lead_cleanup_suggestions" in text:
            return next(iter(self.suggestions.values()), None)
        if "staging_leads" in text:
            return self.lead_lookup_queue.pop(0) if self.lead_lookup_queue else None
        return None


def build_suggestion(**overrides) -> LeadCleanupSuggestion:
    payload = {
        "id": uuid4(),
        "cleanup_run_id": uuid4(),
        "staging_lead_id": uuid4(),
        "suggestion_type": LeadCleanupSuggestionType.STRONG_DUPLICATE,
        "target_lead_id": uuid4(),
        "confidence_score": 0.93,
        "reason": "公开联系方式和客户名称强重复。",
        "evidence_json": {"matched_fields": ["customer_name", "contact"]},
        "recommended_action": "人工确认后执行重复归并。",
        "review_status": LeadCleanupSuggestionReviewStatus.APPROVED,
        "reviewer_id": "admin-a",
        "reviewed_at": datetime(2026, 6, 4, 10, tzinfo=UTC),
        "executed_by": None,
        "executed_at": None,
        "execution_note": None,
        "created_at": datetime(2026, 6, 4, tzinfo=UTC),
        "updated_at": datetime(2026, 6, 4, tzinfo=UTC),
    }
    payload.update(overrides)
    return LeadCleanupSuggestion(**payload)


def build_lead(**overrides) -> StagingLead:
    payload = {
        "id": uuid4(),
        "candidate_url_id": uuid4(),
        "customer_name": "Auto City",
        "country": "Russia",
        "city": "Moscow",
        "customer_type": CustomerType.LOCAL_DEALER_SECONDARY_DEALER,
        "contacts_json": [{"type": "email", "value": "sales@auto-city.example"}],
        "activity_level": "active",
        "scale_signal": "公开页面展示库存。",
        "import_used_car_relevance": "二手车销售相关。",
        "source_evidence": "官网公开页面展示联系方式。",
        "recommended_grade": CustomerGrade.B,
        "recommended_reason": "有公开联系方式。",
        "missing_fields": [],
        "review_status": StagingReviewStatus.PENDING_REVIEW,
        "queue_status": StagingQueueStatus.PENDING_REVIEW,
        "dedupe_key": None,
        "requires_compliance_review": False,
        "created_at": datetime(2026, 6, 4, tzinfo=UTC),
        "updated_at": datetime(2026, 6, 4, tzinfo=UTC),
    }
    payload.update(overrides)
    return StagingLead(**payload)


def test_cleanup_execute_route_and_request_schema_are_registered() -> None:
    openapi = client.get("/openapi.json").json()
    paths = openapi["paths"]

    assert "/lead-cleanup/suggestions/{suggestion_id}/execute" in paths
    assert "post" in paths["/lead-cleanup/suggestions/{suggestion_id}/execute"]

    request = LeadCleanupSuggestionExecuteRequest(
        actor="admin-a",
        actor_role="admin",
        execution_note="按人工确认结果执行。",
    )

    assert request.actor == "admin-a"
    assert request.actor_role == "admin"
    assert request.execution_note == "按人工确认结果执行。"


def test_execute_blocks_suggestion_that_is_not_approved() -> None:
    suggestion = build_suggestion(review_status=LeadCleanupSuggestionReviewStatus.PENDING)
    service = LeadCleanupSuggestionService(FakeSession(suggestions=[suggestion]))

    try:
        service.execute_suggestion(
            suggestion.id,
            actor="admin-a",
            actor_role="admin",
            execution_note="尝试执行未审批建议。",
            now=datetime(2026, 6, 4, 12, tzinfo=UTC),
        )
    except ValueError as exc:
        assert "未 approve 的清洗建议不能执行" in str(exc)
    else:
        raise AssertionError("未 approve 的清洗建议不得执行")


def test_execute_duplicate_requires_admin_role() -> None:
    source = build_lead()
    target = build_lead()
    suggestion = build_suggestion(staging_lead_id=source.id, target_lead_id=target.id)
    service = LeadCleanupSuggestionService(FakeLookupSession(suggestions=[suggestion], leads=[source, target]))

    try:
        service.execute_suggestion(
            suggestion.id,
            actor="ops-a",
            actor_role="operations",
            execution_note="运营尝试执行重复归并。",
            now=datetime(2026, 6, 4, 12, tzinfo=UTC),
        )
    except PermissionError as exc:
        assert "疑似重复和客户级归并需要管理员确认" in str(exc)
    else:
        raise AssertionError("重复归并执行不应由运营执行")


def test_execute_duplicate_marks_secondary_as_duplicate_without_deleting_lead() -> None:
    secondary = build_lead(customer_name="Auto City Moscow")
    target = build_lead(customer_name="Auto City", contacts_json=[{"type": "email", "value": "main@auto-city.example"}])
    suggestion = build_suggestion(
        staging_lead_id=secondary.id,
        target_lead_id=target.id,
        suggestion_type=LeadCleanupSuggestionType.STRONG_DUPLICATE,
    )
    session = FakeLookupSession(suggestions=[suggestion], leads=[secondary, target])
    service = LeadCleanupSuggestionService(session)

    updated = service.execute_suggestion(
        suggestion.id,
        actor="admin-a",
        actor_role="admin",
        execution_note="确认强重复，标记副记录。",
        now=datetime(2026, 6, 4, 12, tzinfo=UTC),
    )

    assert updated.review_status == LeadCleanupSuggestionReviewStatus.EXECUTED
    assert updated.executed_by == "admin-a"
    assert updated.execution_note == "确认强重复，标记副记录。"
    assert secondary.review_status == StagingReviewStatus.DUPLICATE
    assert secondary.queue_status == StagingQueueStatus.NOT_ELIGIBLE
    assert secondary.dedupe_key == f"duplicate_of:{target.id}"
    assert session.deleted == []


def test_execute_possible_duplicate_requires_admin_even_after_approval() -> None:
    secondary = build_lead(customer_name="Auto City Moscow")
    target = build_lead(customer_name="Auto City")
    suggestion = build_suggestion(
        staging_lead_id=secondary.id,
        target_lead_id=target.id,
        suggestion_type=LeadCleanupSuggestionType.POSSIBLE_DUPLICATE,
        reviewer_id="admin-a",
    )
    service = LeadCleanupSuggestionService(FakeLookupSession(suggestions=[suggestion], leads=[secondary, target]))

    try:
        service.execute_suggestion(
            suggestion.id,
            actor="ops-a",
            actor_role="operations",
            execution_note="运营尝试执行疑似重复归并。",
            now=datetime(2026, 6, 4, 12, tzinfo=UTC),
        )
    except PermissionError as exc:
        assert "疑似重复和客户级归并需要管理员确认" in str(exc)
    else:
        raise AssertionError("疑似重复和客户级归并执行阶段仍必须由管理员操作")


def test_execute_merge_contact_method_deduplicates_and_preserves_target_contacts() -> None:
    source = build_lead(
        contacts_json=[
            {"type": "email", "value": " sales@auto-city.example "},
            {"method_type": "telegram", "value": "@autocity"},
        ]
    )
    target = build_lead(contacts_json=[{"type": "email", "value": "sales@auto-city.example"}])
    suggestion = build_suggestion(
        staging_lead_id=source.id,
        target_lead_id=target.id,
        suggestion_type=LeadCleanupSuggestionType.MERGE_CONTACT_METHOD,
    )
    service = LeadCleanupSuggestionService(FakeLookupSession(suggestions=[suggestion], leads=[source, target]))

    service.execute_suggestion(
        suggestion.id,
        actor="admin-a",
        actor_role="admin",
        execution_note="合并公开联系方式。",
        now=datetime(2026, 6, 4, 12, tzinfo=UTC),
    )

    assert target.contacts_json == [
        {"type": "email", "value": "sales@auto-city.example"},
        {"method_type": "telegram", "value": "@autocity"},
    ]


def test_execute_merge_source_evidence_appends_without_overwriting_target() -> None:
    source = build_lead(source_evidence="来源B：公开目录展示 Telegram。")
    target = build_lead(source_evidence="来源A：官网展示邮箱。")
    suggestion = build_suggestion(
        staging_lead_id=source.id,
        target_lead_id=target.id,
        suggestion_type=LeadCleanupSuggestionType.MERGE_SOURCE_EVIDENCE,
    )
    service = LeadCleanupSuggestionService(FakeLookupSession(suggestions=[suggestion], leads=[source, target]))

    service.execute_suggestion(
        suggestion.id,
        actor="admin-a",
        actor_role="admin",
        execution_note="合并来源证据。",
        now=datetime(2026, 6, 4, 12, tzinfo=UTC),
    )

    assert "来源A：官网展示邮箱。" in target.source_evidence
    assert "来源B：公开目录展示 Telegram。" in target.source_evidence


def test_execute_propagates_do_not_contact_boundary_to_target_lead() -> None:
    source = build_lead()
    target = build_lead(recommended_grade=CustomerGrade.B, queue_status=StagingQueueStatus.PENDING_REVIEW)
    suggestion = build_suggestion(
        staging_lead_id=source.id,
        target_lead_id=target.id,
        suggestion_type=LeadCleanupSuggestionType.STRONG_DUPLICATE,
        evidence_json={"do_not_contact": True, "do_not_contact_reason": "公开记录显示客户拒绝继续联系。"},
    )
    service = LeadCleanupSuggestionService(FakeLookupSession(suggestions=[suggestion], leads=[source, target]))

    service.execute_suggestion(
        suggestion.id,
        actor="admin-a",
        actor_role="admin",
        execution_note="传播勿扰状态。",
        now=datetime(2026, 6, 4, 12, tzinfo=UTC),
    )

    assert target.recommended_grade == CustomerGrade.WATCH
    assert target.queue_status == StagingQueueStatus.NOT_ELIGIBLE
    assert "公开记录显示客户拒绝继续联系" in target.source_evidence


def test_execute_records_audit_log_and_flushes_changes() -> None:
    source = build_lead()
    target = build_lead()
    suggestion = build_suggestion(staging_lead_id=source.id, target_lead_id=target.id)
    session = FakeLookupSession(suggestions=[suggestion], leads=[source, target])
    service = LeadCleanupSuggestionService(session)

    service.execute_suggestion(
        suggestion.id,
        actor="admin-a",
        actor_role="admin",
        execution_note="执行强重复清洗。",
        now=datetime(2026, 6, 4, 12, tzinfo=UTC),
    )

    audit = next(item for item in session.added if isinstance(item, ReviewLog))
    assert audit.action == "lead_cleanup_suggestion_executed"
    assert audit.reviewer == "admin-a"
    assert audit.task_id == str(suggestion.id)
    assert "staging_lead_id=" in audit.input_ref
    assert audit.result == "executed"
    assert audit.error_message == "执行强重复清洗。"
    assert session.flushed is True
