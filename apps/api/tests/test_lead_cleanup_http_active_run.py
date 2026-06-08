from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from app.agents.http_runtime import HttpAgentRuntime
from app.models import AgentTaskRun, LeadCleanupRun, LeadCleanupSuggestion
from app.models.enums import (
    AgentTaskRunStatus,
    LeadCleanupRunStatus,
    LeadCleanupSuggestionReviewStatus,
)
from app.services.lead_cleanup import LeadCleanupSuggestionService, select_lead_cleanup_runtime
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


class SuccessfulHttpLeadCleanupRuntime:
    def run_lead_cleanup_response(self, *, cleanup_run_id, leads):
        lead_id = leads[0]["staging_lead_id"]
        return {
            "schema_version": "phase4.agent.run.v1",
            "agent_service_run_id": "66666666-6666-6666-6666-666666666666",
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
                        "confidence_score": 0.82,
                        "reason": "线索为 Invalid，建议人工确认无效原因。",
                        "evidence_json": {"invalid_reason": "非车辆销售客户。"},
                        "recommended_action": "人工确认无效原因后保留清洗结论",
                        "review_status": "pending",
                    }
                ],
                "blocked_items": [],
                "audit": {"writes_core_tables": False, "output_table": "lead_cleanup_suggestions"},
            },
            "audit": {
                "writes_core_tables": False,
                "executed_nodes": [{"node": "validate_suggestions", "status": "succeeded"}],
                "risk_flags": [],
                "source_urls": [],
            },
            "error": None,
        }


class FailedHttpLeadCleanupRuntime:
    def run_lead_cleanup_response(self, *, cleanup_run_id, leads):
        return {
            "schema_version": "phase4.agent.run.v1",
            "agent_service_run_id": "77777777-7777-7777-7777-777777777777",
            "request_id": str(cleanup_run_id),
            "status": "failed",
            "agent_type": "lead_cleanup",
            "agent_mode": "active",
            "output": None,
            "audit": {"writes_core_tables": False, "failed_node": "validate_suggestions"},
            "error": {
                "error_type": "cleanup_validation_error",
                "message": "invalid suggestion payload",
                "retryable": False,
                "failed_node": "validate_suggestions",
            },
        }


class LocalLeadCleanupRuntime:
    def run_lead_cleanup(self, *, cleanup_run_id, leads):
        return {
            "schema_version": "phase3.agent.lead_cleanup.v1",
            "cleanup_run_id": str(cleanup_run_id),
            "suggestions": [],
            "blocked_items": [],
            "audit": {"writes_core_tables": False, "output_table": "lead_cleanup_suggestions"},
        }


def build_cleanup_run() -> LeadCleanupRun:
    return LeadCleanupRun(
        id=uuid4(),
        trigger_source="manual-agent-runtime-test",
        status=LeadCleanupRunStatus.PENDING,
        input_filter_json={"grades": ["Watch", "Invalid"]},
        output_summary_json=None,
        created_at=datetime(2026, 6, 5, tzinfo=UTC),
        updated_at=datetime(2026, 6, 5, tzinfo=UTC),
    )


def test_lead_cleanup_http_active_run_saves_external_agent_summary_and_pending_suggestions() -> None:
    session = FakeSession()
    service = LeadCleanupSuggestionService(session)
    cleanup_run = build_cleanup_run()
    lead_id = uuid4()

    task_run = service.run_cleanup_agent(
        cleanup_run,
        leads=[{"staging_lead_id": lead_id, "recommended_grade": "Invalid"}],
        runtime=SuccessfulHttpLeadCleanupRuntime(),
        now=datetime(2026, 6, 5, 16, tzinfo=UTC),
        agents_base_url="http://agents.local:8010",
    )

    assert isinstance(task_run, AgentTaskRun)
    assert task_run.status == AgentTaskRunStatus.SUCCEEDED
    assert cleanup_run.status == LeadCleanupRunStatus.SUCCEEDED
    assert cleanup_run.output_summary_json["suggestion_count"] == 1
    summary = task_run.output_summary_json
    assert summary["external_agent_run_id"] == "66666666-6666-6666-6666-666666666666"
    assert summary["external_agent_status"] == "succeeded"
    assert summary["external_agent_type"] == "lead_cleanup"
    assert summary["external_agent_mode"] == "active"
    assert summary["agents_base_url"] == "http://agents.local:8010"
    assert summary["external_agent_audit"]["writes_core_tables"] is False

    suggestion = next(item for item in session.added if isinstance(item, LeadCleanupSuggestion))
    assert suggestion.review_status == LeadCleanupSuggestionReviewStatus.PENDING
    assert suggestion.executed_by is None
    assert suggestion.executed_at is None


def test_lead_cleanup_local_runtime_keeps_existing_summary_without_external_agent_id() -> None:
    session = FakeSession()
    service = LeadCleanupSuggestionService(session)
    cleanup_run = build_cleanup_run()

    task_run = service.run_cleanup_agent(
        cleanup_run,
        leads=[{"staging_lead_id": uuid4(), "recommended_grade": "Invalid"}],
        runtime=LocalLeadCleanupRuntime(),
        now=datetime(2026, 6, 5, 16, tzinfo=UTC),
    )

    assert task_run.status == AgentTaskRunStatus.SUCCEEDED
    assert "external_agent_run_id" not in task_run.output_summary_json


def test_lead_cleanup_http_active_run_failure_preserves_external_agent_summary() -> None:
    session = FakeSession()
    service = LeadCleanupSuggestionService(session)
    cleanup_run = build_cleanup_run()

    task_run = service.run_cleanup_agent(
        cleanup_run,
        leads=[{"staging_lead_id": uuid4(), "recommended_grade": "Invalid"}],
        runtime=FailedHttpLeadCleanupRuntime(),
        now=datetime(2026, 6, 5, 16, tzinfo=UTC),
        agents_base_url="http://agents.local:8010",
    )

    assert cleanup_run.status == LeadCleanupRunStatus.FAILED
    assert task_run.status == AgentTaskRunStatus.FAILED
    assert "Lead Cleanup Agent 输出缺少结构化 output" in task_run.error_message
    summary = task_run.output_summary_json
    assert summary["external_agent_run_id"] == "77777777-7777-7777-7777-777777777777"
    assert summary["external_agent_status"] == "failed"
    assert summary["external_agent_error"]["error_type"] == "cleanup_validation_error"
    assert summary["external_agent_audit"]["failed_node"] == "validate_suggestions"


def test_lead_cleanup_runtime_selector_uses_http_runtime_only_when_switch_and_key_are_enabled() -> None:
    disabled = Settings(
        _env_file=None,
        AGENTS_API_KEY="agents-test-key",
        AGENT_LEAD_CLEANUP_HTTP_ACTIVE_ENABLED="false",
    )
    assert select_lead_cleanup_runtime(disabled) is None

    missing_key = Settings(
        _env_file=None,
        AGENTS_API_KEY="",
        AGENT_LEAD_CLEANUP_HTTP_ACTIVE_ENABLED="true",
    )
    assert select_lead_cleanup_runtime(missing_key) is None

    enabled = Settings(
        _env_file=None,
        AGENTS_BASE_URL="http://agents.local:8010",
        AGENTS_API_KEY="agents-test-key",
        AGENT_LEAD_CLEANUP_HTTP_ACTIVE_ENABLED="true",
    )
    runtime = select_lead_cleanup_runtime(enabled)
    assert isinstance(runtime, HttpAgentRuntime)
    assert runtime.settings.agents_base_url == "http://agents.local:8010"


def test_lead_cleanup_api_keeps_review_execution_boundary_without_create_run_route() -> None:
    api_text = (API_ROOT / "app" / "api" / "lead_cleanup.py").read_text(encoding="utf-8")

    assert "run_cleanup_agent(" not in api_text
    assert "execute" in api_text
    assert "approve" in api_text
