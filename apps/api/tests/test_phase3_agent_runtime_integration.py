from datetime import UTC, datetime
from uuid import uuid4

from app.models import (
    AgentTaskRun,
    LeadCleanupRun,
    LeadCleanupSuggestion,
    LeadEnrichmentFieldCandidate,
    LeadEnrichmentResult,
)
from app.models.enums import (
    AgentTaskRunStatus,
    AgentTaskType,
    LeadCleanupRunStatus,
    LeadCleanupSuggestionReviewStatus,
    LeadCleanupSuggestionType,
    LeadEnrichmentFieldReviewStatus,
    LeadEnrichmentFieldSourceType,
    LeadEnrichmentResultStatus,
    LeadEnrichmentType,
)
from app.services.lead_cleanup import LeadCleanupSuggestionService
from app.services.lead_enrichment import LeadEnrichmentService


class FakeSession:
    def __init__(self):
        self.added = []
        self.flushed = False

    def add(self, item):
        self.added.append(item)

    def add_all(self, items):
        self.added.extend(items)

    def flush(self):
        self.flushed = True
        for item in self.added:
            if getattr(item, "id", None) is None:
                item.id = uuid4()


class SuccessfulDeepEnrichmentRuntime:
    def run_deep_enrichment(self, *, agent_run_id, staging_lead_id, lead_snapshot, missing_fields):
        return {
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
                    "confidence_score": 0.88,
                    "review_status": "pending",
                }
            ],
            "missing_fields": [],
            "recommended_next_action": "manual_review",
            "audit": {
                "writes_core_tables": False,
                "output_table": "lead_enrichment_field_candidates",
            },
        }


class FailingDeepEnrichmentRuntime:
    def run_deep_enrichment(self, **kwargs):
        raise RuntimeError("mock agent unavailable")


class SuccessfulCleanupRuntime:
    def run_lead_cleanup(self, *, cleanup_run_id, leads):
        lead_id = leads[0]["staging_lead_id"]
        return {
            "schema_version": "phase3.agent.lead_cleanup.v1",
            "cleanup_run_id": str(cleanup_run_id),
            "suggestions": [
                {
                    "staging_lead_id": str(lead_id),
                    "suggestion_type": "confirm_invalid",
                    "target_lead_id": None,
                    "confidence_score": 0.81,
                    "reason": "线索为 Invalid，建议人工确认无效原因。",
                    "evidence_json": {"invalid_reason": "非车辆销售客户。"},
                    "recommended_action": "人工确认无效原因后保留清洗结论",
                    "review_status": "pending",
                }
            ],
            "blocked_items": [],
            "audit": {
                "writes_core_tables": False,
                "output_table": "lead_cleanup_suggestions",
            },
        }


def build_pending_enrichment_result() -> LeadEnrichmentResult:
    lead_id = uuid4()
    return LeadEnrichmentResult(
        id=uuid4(),
        staging_lead_id=lead_id,
        enrichment_type=LeadEnrichmentType.AI_DEEP_RESEARCH,
        triggered_by="ops-a",
        status=LeadEnrichmentResultStatus.PENDING,
        input_snapshot_json={"customer_name": "Ru Auto City", "city": "Moscow"},
        output_json=None,
        evidence_links=[],
        confidence_score=None,
        missing_fields=["contacts_json"],
        recommended_action="run_deep_enrichment_agent",
        agent_task_run_id=None,
        created_at=datetime(2026, 6, 4, tzinfo=UTC),
        updated_at=datetime(2026, 6, 4, tzinfo=UTC),
    )


def test_lead_enrichment_service_runs_mock_agent_and_writes_candidates_with_task_audit() -> None:
    session = FakeSession()
    service = LeadEnrichmentService(session)
    result = build_pending_enrichment_result()

    task_run = service.run_deep_enrichment_agent(
        result,
        runtime=SuccessfulDeepEnrichmentRuntime(),
        now=datetime(2026, 6, 4, 15, tzinfo=UTC),
    )

    assert isinstance(task_run, AgentTaskRun)
    assert task_run.task_type == AgentTaskType.LEAD_GRADING
    assert task_run.status == AgentTaskRunStatus.SUCCEEDED
    assert task_run.output_summary_json["field_candidate_count"] == 1
    assert result.status == LeadEnrichmentResultStatus.SUCCEEDED
    assert result.agent_task_run_id == task_run.id
    assert result.output_json["schema_version"] == "phase3.agent.deep_enrichment.v1"
    assert result.evidence_links == ["https://dealer.example.ru/contact"]
    candidate = next(item for item in session.added if isinstance(item, LeadEnrichmentFieldCandidate))
    assert candidate.field_name == "contacts_json"
    assert candidate.source_type == LeadEnrichmentFieldSourceType.AI_PUBLIC_SOURCE
    assert candidate.review_status == LeadEnrichmentFieldReviewStatus.PENDING
    assert not hasattr(candidate, "customer_id")


def test_lead_enrichment_agent_failure_marks_task_failed_without_raising_to_api_thread() -> None:
    session = FakeSession()
    service = LeadEnrichmentService(session)
    result = build_pending_enrichment_result()

    task_run = service.run_deep_enrichment_agent(
        result,
        runtime=FailingDeepEnrichmentRuntime(),
        now=datetime(2026, 6, 4, 15, tzinfo=UTC),
    )

    assert task_run.status in {AgentTaskRunStatus.FAILED, AgentTaskRunStatus.RETRY_PENDING}
    assert "mock agent unavailable" in (task_run.error_message or "")
    assert result.status == LeadEnrichmentResultStatus.FAILED
    assert result.agent_task_run_id == task_run.id


def test_lead_cleanup_service_runs_mock_agent_and_writes_pending_suggestions() -> None:
    session = FakeSession()
    service = LeadCleanupSuggestionService(session)
    cleanup_run = LeadCleanupRun(
        id=uuid4(),
        trigger_source="manual-agent-runtime-test",
        status=LeadCleanupRunStatus.PENDING,
        input_filter_json={"grades": ["Watch", "Invalid"]},
        output_summary_json=None,
        created_at=datetime(2026, 6, 4, tzinfo=UTC),
        updated_at=datetime(2026, 6, 4, tzinfo=UTC),
    )
    lead_id = uuid4()

    task_run = service.run_cleanup_agent(
        cleanup_run,
        leads=[{"staging_lead_id": lead_id, "recommended_grade": "Invalid"}],
        runtime=SuccessfulCleanupRuntime(),
        now=datetime(2026, 6, 4, 16, tzinfo=UTC),
    )

    assert isinstance(task_run, AgentTaskRun)
    assert task_run.status == AgentTaskRunStatus.SUCCEEDED
    assert cleanup_run.status == LeadCleanupRunStatus.SUCCEEDED
    assert cleanup_run.output_summary_json["suggestion_count"] == 1
    suggestion = next(item for item in session.added if isinstance(item, LeadCleanupSuggestion))
    assert suggestion.cleanup_run_id == cleanup_run.id
    assert suggestion.staging_lead_id == lead_id
    assert suggestion.suggestion_type == LeadCleanupSuggestionType.CONFIRM_INVALID
    assert suggestion.review_status == LeadCleanupSuggestionReviewStatus.PENDING
    assert suggestion.executed_by is None
    assert suggestion.executed_at is None
