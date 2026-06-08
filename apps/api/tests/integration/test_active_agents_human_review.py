from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.models import (
    LeadCleanupRun,
    LeadCleanupSuggestion,
    LeadEnrichmentFieldCandidate,
    LeadEnrichmentResult,
    ReviewLog,
    StagingLead,
)
from app.models.enums import (
    CustomerGrade,
    CustomerType,
    LeadCleanupRunStatus,
    LeadCleanupSuggestionReviewStatus,
    LeadCleanupSuggestionType,
    LeadEnrichmentFieldReviewStatus,
    LeadEnrichmentFieldSourceType,
    LeadEnrichmentResultStatus,
    LeadEnrichmentType,
    StagingQueueStatus,
    StagingReviewStatus,
)
from app.schemas.lead_enrichment_field_candidate import (
    LeadEnrichmentFieldCandidateAccept,
    LeadEnrichmentFieldCandidateReject,
)
from app.services.lead_cleanup import LeadCleanupSuggestionService
from app.services.lead_enrichment import LeadEnrichmentService


class ReviewIntegrationSession:
    def __init__(self, *, leads: list[StagingLead] | None = None, cleanup_suggestions: list[LeadCleanupSuggestion] | None = None):
        self.leads = {item.id: item for item in leads or []}
        self.cleanup_suggestions = {item.id: item for item in cleanup_suggestions or []}
        self.added = []
        self.flushed = False
        self.deleted = []
        self.lead_lookup_queue = list(leads or [])

    def add(self, item):
        self.added.append(item)
        if isinstance(item, LeadCleanupSuggestion):
            self.cleanup_suggestions[item.id] = item

    def add_all(self, items):
        for item in items:
            self.add(item)

    def get(self, model, item_id):
        if model is StagingLead:
            return self.leads.get(item_id)
        return None

    def scalar(self, statement):
        text = str(statement)
        if "lead_cleanup_suggestions" in text:
            return next(iter(self.cleanup_suggestions.values()), None)
        if "staging_leads" in text:
            return self.lead_lookup_queue.pop(0) if self.lead_lookup_queue else None
        return None

    def flush(self):
        self.flushed = True
        for item in self.added:
            if getattr(item, "id", None) is None:
                item.id = uuid4()
            if isinstance(item, LeadCleanupSuggestion):
                self.cleanup_suggestions[item.id] = item

    def delete(self, item):
        self.deleted.append(item)


class HttpDeepEnrichmentReviewRuntime:
    def run_deep_enrichment_response(self, *, agent_run_id, staging_lead_id, lead_snapshot, missing_fields):
        return {
            "schema_version": "phase4.agent.run.v1",
            "agent_service_run_id": "88888888-8888-8888-8888-888888888888",
            "request_id": str(agent_run_id),
            "status": "succeeded",
            "agent_type": "deep_enrichment",
            "agent_mode": "active",
            "output": {
                "schema_version": "phase3.agent.deep_enrichment.v1",
                "agent_run_id": str(agent_run_id),
                "staging_lead_id": str(staging_lead_id),
                "field_candidates": [
                    {
                        "field_name": "contacts_json",
                        "candidate_value": [{"type": "email", "value": "sales@example.ru"}],
                        "source_type": "ai_public_source",
                        "source_url": "https://dealer.example.ru/contact",
                        "evidence_note": "公开联系页展示邮箱 sales@example.ru。",
                        "confidence_score": 0.9,
                        "review_status": "pending",
                    }
                ],
                "missing_fields": [],
                "recommended_next_action": "manual_review",
                "audit": {"writes_core_tables": False, "output_table": "lead_enrichment_field_candidates"},
            },
            "audit": {"writes_core_tables": False, "executed_nodes": [{"node": "validate_evidence", "status": "succeeded"}]},
            "error": None,
        }


class HttpLeadCleanupReviewRuntime:
    def run_lead_cleanup_response(self, *, cleanup_run_id, leads):
        lead_id = leads[0]["staging_lead_id"]
        return {
            "schema_version": "phase4.agent.run.v1",
            "agent_service_run_id": "99999999-9999-9999-9999-999999999999",
            "request_id": str(cleanup_run_id),
            "status": "succeeded",
            "agent_type": "lead_cleanup",
            "agent_mode": "active",
            "output": {
                "schema_version": "phase3.agent.lead_cleanup.v1",
                "cleanup_run_id": str(cleanup_run_id),
                "suggestions": [
                    {
                        "staging_lead_id": str(lead_id),
                        "suggestion_type": "confirm_invalid",
                        "target_lead_id": None,
                        "confidence_score": 0.86,
                        "reason": "公开页面显示该对象不是车辆采购客户。",
                        "evidence_json": {"invalid_reason": "非车辆采购客户"},
                        "recommended_action": "人工确认后标记 Invalid",
                        "review_status": "pending",
                    }
                ],
                "blocked_items": [],
                "audit": {"writes_core_tables": False, "output_table": "lead_cleanup_suggestions"},
            },
            "audit": {"writes_core_tables": False, "executed_nodes": [{"node": "validate_suggestions", "status": "succeeded"}]},
            "error": None,
        }


def build_staging_lead(**overrides) -> StagingLead:
    payload = {
        "id": uuid4(),
        "candidate_url_id": uuid4(),
        "customer_name": "Ru Auto City",
        "country": "Russia",
        "city": "Moscow",
        "customer_type": CustomerType.LOCAL_DEALER_SECONDARY_DEALER,
        "contacts_json": [],
        "activity_level": "active",
        "scale_signal": "公开页面展示库存。",
        "import_used_car_relevance": "二手车销售相关。",
        "source_evidence": "公开官网包含车辆销售线索。",
        "recommended_grade": CustomerGrade.B,
        "recommended_reason": "具备公开业务证据。",
        "missing_fields": ["contacts_json"],
        "review_status": StagingReviewStatus.PENDING_REVIEW,
        "queue_status": StagingQueueStatus.PENDING_REVIEW,
        "dedupe_key": None,
        "requires_compliance_review": False,
        "created_at": datetime(2026, 6, 5, tzinfo=UTC),
        "updated_at": datetime(2026, 6, 5, tzinfo=UTC),
    }
    payload.update(overrides)
    return StagingLead(**payload)


def build_enrichment_result(lead: StagingLead) -> LeadEnrichmentResult:
    return LeadEnrichmentResult(
        id=uuid4(),
        staging_lead_id=lead.id,
        enrichment_type=LeadEnrichmentType.AI_DEEP_RESEARCH,
        triggered_by="ops-a",
        status=LeadEnrichmentResultStatus.PENDING,
        input_snapshot_json={"customer_name": lead.customer_name, "contacts_json": lead.contacts_json},
        output_json=None,
        evidence_links=[],
        confidence_score=None,
        missing_fields=lead.missing_fields,
        recommended_action="run_deep_enrichment_agent",
        agent_task_run_id=None,
        created_at=datetime(2026, 6, 5, tzinfo=UTC),
        updated_at=datetime(2026, 6, 5, tzinfo=UTC),
    )


def build_cleanup_run() -> LeadCleanupRun:
    return LeadCleanupRun(
        id=uuid4(),
        trigger_source="phase4_active_review_integration",
        status=LeadCleanupRunStatus.PENDING,
        input_filter_json={"grades": ["Invalid"]},
        output_summary_json=None,
        created_at=datetime(2026, 6, 5, tzinfo=UTC),
        updated_at=datetime(2026, 6, 5, tzinfo=UTC),
    )


def first_added(session: ReviewIntegrationSession, model):
    return next(item for item in session.added if isinstance(item, model))


def test_deep_enrichment_active_run_candidate_is_pending_until_human_review_then_apps_api_writes_staging_field() -> None:
    lead = build_staging_lead()
    session = ReviewIntegrationSession(leads=[lead])
    service = LeadEnrichmentService(session)
    result = build_enrichment_result(lead)

    task_run = service.run_deep_enrichment_agent(
        result,
        runtime=HttpDeepEnrichmentReviewRuntime(),
        now=datetime(2026, 6, 5, 10, tzinfo=UTC),
        agents_base_url="http://agents.local:8010",
    )

    candidate = first_added(session, LeadEnrichmentFieldCandidate)
    assert task_run.output_summary_json["external_agent_run_id"] == "88888888-8888-8888-8888-888888888888"
    assert candidate.review_status == LeadEnrichmentFieldReviewStatus.PENDING
    assert lead.contacts_json == []

    service.accept_field_candidate_with_audit(
        candidate,
        request=LeadEnrichmentFieldCandidateAccept(accepted_by="reviewer-a"),
        now=datetime(2026, 6, 5, 11, tzinfo=UTC),
    )

    assert candidate.review_status == LeadEnrichmentFieldReviewStatus.ACCEPTED
    assert lead.contacts_json == [{"type": "email", "value": "sales@example.ru"}]
    assert lead.missing_fields == []
    assert first_added(session, ReviewLog).action == "lead_enrichment_field_accepted"


def test_deep_enrichment_active_run_rejected_candidate_does_not_write_staging_field() -> None:
    lead = build_staging_lead()
    session = ReviewIntegrationSession(leads=[lead])
    service = LeadEnrichmentService(session)
    result = build_enrichment_result(lead)

    service.run_deep_enrichment_agent(
        result,
        runtime=HttpDeepEnrichmentReviewRuntime(),
        now=datetime(2026, 6, 5, 10, tzinfo=UTC),
        agents_base_url="http://agents.local:8010",
    )
    candidate = first_added(session, LeadEnrichmentFieldCandidate)

    service.reject_field_candidate_with_audit(
        candidate,
        request=LeadEnrichmentFieldCandidateReject(rejected_reason="公开证据不足，不采纳联系方式。"),
        now=datetime(2026, 6, 5, 11, tzinfo=UTC),
    )

    assert candidate.review_status == LeadEnrichmentFieldReviewStatus.REJECTED
    assert lead.contacts_json == []
    assert lead.missing_fields == ["contacts_json"]


def test_lead_cleanup_active_run_suggestion_requires_approval_before_apps_api_execution() -> None:
    lead = build_staging_lead(recommended_grade=CustomerGrade.INVALID)
    session = ReviewIntegrationSession(leads=[lead])
    service = LeadCleanupSuggestionService(session)
    cleanup_run = build_cleanup_run()

    task_run = service.run_cleanup_agent(
        cleanup_run,
        leads=[{"staging_lead_id": lead.id, "recommended_grade": "Invalid"}],
        runtime=HttpLeadCleanupReviewRuntime(),
        now=datetime(2026, 6, 5, 10, tzinfo=UTC),
        agents_base_url="http://agents.local:8010",
    )

    suggestion = first_added(session, LeadCleanupSuggestion)
    assert task_run.output_summary_json["external_agent_run_id"] == "99999999-9999-9999-9999-999999999999"
    assert suggestion.review_status == LeadCleanupSuggestionReviewStatus.PENDING
    assert suggestion.executed_by is None

    try:
        service.execute_suggestion(
            suggestion.id,
            actor="admin-a",
            actor_role="admin",
            execution_note="未审核不得执行。",
            now=datetime(2026, 6, 5, 11, tzinfo=UTC),
        )
    except ValueError as exc:
        assert "未 approve 的清洗建议不能执行" in str(exc)
    else:
        raise AssertionError("active_run 清洗建议未审核前不得执行")

    service.approve_suggestion(
        suggestion.id,
        actor="admin-a",
        actor_role="admin",
        review_note="人工确认该线索应标记无效。",
        now=datetime(2026, 6, 5, 11, tzinfo=UTC),
    )
    service.execute_suggestion(
        suggestion.id,
        actor="admin-a",
        actor_role="admin",
        execution_note="按人工确认结果执行。",
        now=datetime(2026, 6, 5, 11, 30, tzinfo=UTC),
    )

    assert suggestion.review_status == LeadCleanupSuggestionReviewStatus.EXECUTED
    assert suggestion.executed_by == "admin-a"
    assert lead.review_status == StagingReviewStatus.REJECTED
    assert lead.queue_status == StagingQueueStatus.NOT_ELIGIBLE
    assert lead.recommended_grade == CustomerGrade.INVALID
    assert session.deleted == []
