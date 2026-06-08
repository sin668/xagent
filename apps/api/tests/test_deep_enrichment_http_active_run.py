from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from app.agents.http_runtime import HttpAgentRuntime
from app.models import AgentTaskRun, LeadEnrichmentFieldCandidate, LeadEnrichmentResult
from app.models.enums import (
    AgentTaskRunStatus,
    LeadEnrichmentFieldReviewStatus,
    LeadEnrichmentResultStatus,
    LeadEnrichmentType,
)
from app.services.lead_enrichment import LeadEnrichmentService, select_deep_enrichment_runtime
from app.settings import Settings


API_ROOT = Path(__file__).resolve().parents[1]


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


class SuccessfulHttpDeepEnrichmentRuntime:
    def run_deep_enrichment_response(self, *, agent_run_id, staging_lead_id, lead_snapshot, missing_fields):
        return {
            "schema_version": "phase4.agent.run.v1",
            "agent_service_run_id": "44444444-4444-4444-4444-444444444444",
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
                        "confidence_score": 0.88,
                        "review_status": "pending",
                    }
                ],
                "missing_fields": [],
                "recommended_next_action": "manual_review",
                "audit": {"writes_core_tables": False, "output_table": "lead_enrichment_field_candidates"},
            },
            "audit": {
                "writes_core_tables": False,
                "executed_nodes": [{"node": "validate_evidence", "status": "succeeded"}],
                "risk_flags": [],
                "source_urls": ["https://dealer.example.ru/contact"],
            },
            "error": None,
        }


class FailedHttpDeepEnrichmentRuntime:
    def run_deep_enrichment_response(self, *, agent_run_id, staging_lead_id, lead_snapshot, missing_fields):
        return {
            "schema_version": "phase4.agent.run.v1",
            "agent_service_run_id": "55555555-5555-5555-5555-555555555555",
            "request_id": str(agent_run_id),
            "status": "failed",
            "agent_type": "deep_enrichment",
            "agent_mode": "active",
            "output": None,
            "audit": {"writes_core_tables": False, "failed_node": "validate_evidence"},
            "error": {
                "error_type": "evidence_validation_error",
                "message": "no public evidence",
                "retryable": False,
                "failed_node": "validate_evidence",
            },
        }


class LocalDeepEnrichmentRuntime:
    def run_deep_enrichment(self, *, agent_run_id, staging_lead_id, lead_snapshot, missing_fields):
        return {
            "schema_version": "phase3.agent.deep_enrichment.v1",
            "agent_run_id": str(agent_run_id),
            "staging_lead_id": str(staging_lead_id),
            "field_candidates": [],
            "missing_fields": missing_fields,
            "recommended_next_action": "continue_enrichment",
            "audit": {"writes_core_tables": False, "output_table": "lead_enrichment_field_candidates"},
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
        created_at=datetime(2026, 6, 5, tzinfo=UTC),
        updated_at=datetime(2026, 6, 5, tzinfo=UTC),
    )


def test_deep_enrichment_http_active_run_saves_external_agent_summary_and_pending_candidates() -> None:
    session = FakeSession()
    service = LeadEnrichmentService(session)
    result = build_pending_enrichment_result()

    task_run = service.run_deep_enrichment_agent(
        result,
        runtime=SuccessfulHttpDeepEnrichmentRuntime(),
        now=datetime(2026, 6, 5, 15, tzinfo=UTC),
        agents_base_url="http://agents.local:8010",
    )

    assert isinstance(task_run, AgentTaskRun)
    assert task_run.status == AgentTaskRunStatus.SUCCEEDED
    assert result.status == LeadEnrichmentResultStatus.SUCCEEDED
    assert result.agent_task_run_id == task_run.id
    assert result.output_json["schema_version"] == "phase3.agent.deep_enrichment.v1"
    assert result.evidence_links == ["https://dealer.example.ru/contact"]
    summary = task_run.output_summary_json
    assert summary["field_candidate_count"] == 1
    assert summary["external_agent_run_id"] == "44444444-4444-4444-4444-444444444444"
    assert summary["external_agent_status"] == "succeeded"
    assert summary["external_agent_type"] == "deep_enrichment"
    assert summary["agents_base_url"] == "http://agents.local:8010"
    assert summary["external_agent_audit"]["writes_core_tables"] is False
    assert summary["external_agent_audit"]["source_url_count"] == 1

    candidate = next(item for item in session.added if isinstance(item, LeadEnrichmentFieldCandidate))
    assert candidate.review_status == LeadEnrichmentFieldReviewStatus.PENDING
    assert candidate.accepted_by is None
    assert candidate.accepted_at is None


def test_deep_enrichment_local_runtime_keeps_existing_summary_without_external_agent_id() -> None:
    session = FakeSession()
    service = LeadEnrichmentService(session)
    result = build_pending_enrichment_result()

    task_run = service.run_deep_enrichment_agent(
        result,
        runtime=LocalDeepEnrichmentRuntime(),
        now=datetime(2026, 6, 5, 15, tzinfo=UTC),
    )

    assert task_run.status == AgentTaskRunStatus.SUCCEEDED
    assert "external_agent_run_id" not in task_run.output_summary_json


def test_deep_enrichment_http_active_run_failure_preserves_external_agent_summary() -> None:
    session = FakeSession()
    service = LeadEnrichmentService(session)
    result = build_pending_enrichment_result()

    task_run = service.run_deep_enrichment_agent(
        result,
        runtime=FailedHttpDeepEnrichmentRuntime(),
        now=datetime(2026, 6, 5, 15, tzinfo=UTC),
        agents_base_url="http://agents.local:8010",
    )

    assert result.status == LeadEnrichmentResultStatus.FAILED
    assert task_run.status == AgentTaskRunStatus.FAILED
    assert "Deep Enrichment Agent 输出缺少结构化 output" in task_run.error_message
    summary = task_run.output_summary_json
    assert summary["external_agent_run_id"] == "55555555-5555-5555-5555-555555555555"
    assert summary["external_agent_status"] == "failed"
    assert summary["external_agent_error"]["error_type"] == "evidence_validation_error"
    assert summary["external_agent_audit"]["failed_node"] == "validate_evidence"


def test_deep_enrichment_runtime_selector_uses_http_runtime_only_when_switch_and_key_are_enabled() -> None:
    disabled = Settings(
        _env_file=None,
        AGENTS_API_KEY="agents-test-key",
        AGENT_DEEP_ENRICHMENT_HTTP_ACTIVE_ENABLED="false",
    )
    assert select_deep_enrichment_runtime(disabled) is None

    missing_key = Settings(
        _env_file=None,
        AGENTS_API_KEY="",
        AGENT_DEEP_ENRICHMENT_HTTP_ACTIVE_ENABLED="true",
    )
    assert select_deep_enrichment_runtime(missing_key) is None

    enabled = Settings(
        _env_file=None,
        AGENTS_BASE_URL="http://agents.local:8010",
        AGENTS_API_KEY="agents-test-key",
        AGENT_DEEP_ENRICHMENT_HTTP_ACTIVE_ENABLED="true",
    )
    runtime = select_deep_enrichment_runtime(enabled)
    assert isinstance(runtime, HttpAgentRuntime)
    assert runtime.settings.agents_base_url == "http://agents.local:8010"


def test_lead_enrichment_api_route_invokes_deep_enrichment_http_active_runtime_selector() -> None:
    api_text = (API_ROOT / "app" / "api" / "lead_enrichment.py").read_text(encoding="utf-8")

    assert "select_deep_enrichment_runtime(settings)" in api_text
    assert "service.run_deep_enrichment_agent(" in api_text
    assert "agents_base_url=settings.agents_base_url" in api_text
