from pathlib import Path

from app.models.enums import AgentTaskRunStatus, AgentTaskType
from app.services.agent_task_runs import AgentTaskRunService


API_ROOT = Path(__file__).resolve().parents[2]
MIGRATION_PATH = API_ROOT / "alembic" / "versions" / "20260602_0021_create_agent_task_runs.py"


def build_running_task() -> dict:
    return AgentTaskRunService.start(
        AgentTaskRunService.build_initial_payload(
            task_type=AgentTaskType.LEAD_GRADING,
            trigger_source="phase4_http_agent_runtime",
            input_json={"staging_lead_id": "33333333-3333-3333-3333-333333333333"},
        )
    )


def test_external_agent_success_summary_is_saved_without_schema_change() -> None:
    migration = MIGRATION_PATH.read_text(encoding="utf-8")
    assert "external_agent_run_id" not in migration
    assert "external_agent_status" not in migration

    task = AgentTaskRunService.succeed_with_external_agent_summary(
        build_running_task(),
        output_summary_json={"field_candidate_count": 1, "writes_core_tables": False},
        external_agent_response={
            "agent_service_run_id": "44444444-4444-4444-4444-444444444444",
            "status": "succeeded",
            "agent_type": "deep_enrichment",
            "agent_mode": "active",
            "audit": {
                "writes_core_tables": False,
                "executed_nodes": [{"node": "validate_evidence", "status": "succeeded"}],
                "risk_flags": ["low_evidence"],
                "source_urls": ["https://dealer.example.ru/contact"],
            },
        },
        agents_base_url="http://localhost:8010",
    )

    assert task["status"] == AgentTaskRunStatus.SUCCEEDED
    summary = task["output_summary_json"]
    assert summary["field_candidate_count"] == 1
    assert summary["external_agent_run_id"] == "44444444-4444-4444-4444-444444444444"
    assert summary["external_agent_status"] == "succeeded"
    assert summary["external_agent_type"] == "deep_enrichment"
    assert summary["external_agent_mode"] == "active"
    assert summary["agents_base_url"] == "http://localhost:8010"
    assert summary["external_agent_audit"]["writes_core_tables"] is False
    assert summary["external_agent_audit"]["executed_node_count"] == 1
    assert summary["external_agent_audit"]["risk_flags"] == ["low_evidence"]
    assert summary["external_agent_audit"]["source_url_count"] == 1


def test_external_agent_failure_summary_preserves_error_semantics() -> None:
    task = AgentTaskRunService.fail_with_external_agent_summary(
        build_running_task(),
        error_message="apps/agents deep enrichment failed",
        error={
            "type": "rate_limit_error",
            "message": "provider rate limited",
            "retryable": True,
        },
        external_agent_response={
            "agent_service_run_id": "55555555-5555-5555-5555-555555555555",
            "status": "failed",
            "agent_type": "deep_enrichment",
            "agent_mode": "active",
            "error": {
                "error_type": "provider_rate_limited",
                "message": "provider rate limited",
                "retryable": True,
                "failed_node": "call_llm",
            },
            "audit": {"writes_core_tables": False, "failed_node": "call_llm"},
        },
        agents_base_url="http://localhost:8010",
    )

    assert task["status"] == AgentTaskRunStatus.RETRY_PENDING
    assert task["error_message"] == "apps/agents deep enrichment failed"
    summary = task["output_summary_json"]
    assert summary["error"] == {
        "type": "rate_limit_error",
        "message": "provider rate limited",
        "retryable": True,
    }
    assert summary["retry_decision"]["should_retry"] is True
    assert summary["external_agent_run_id"] == "55555555-5555-5555-5555-555555555555"
    assert summary["external_agent_status"] == "failed"
    assert summary["external_agent_error"] == {
        "error_type": "provider_rate_limited",
        "message": "provider rate limited",
        "retryable": True,
        "failed_node": "call_llm",
    }
    assert summary["external_agent_audit"]["failed_node"] == "call_llm"


def test_external_agent_summary_redacts_sensitive_values_and_input_full_text() -> None:
    task = AgentTaskRunService.succeed_with_external_agent_summary(
        build_running_task(),
        output_summary_json={"api_key": "sk-should-not-appear", "input_json": {"raw_text": "very long lead data"}},
        external_agent_response={
            "agent_service_run_id": "44444444-4444-4444-4444-444444444444",
            "status": "succeeded",
            "agent_type": "lead_cleanup",
            "agent_mode": "active",
            "audit": {
                "writes_core_tables": False,
                "source_urls": ["https://dealer.example.ru/contact"],
                "api_key": "agents-secret",
                "input_summary": {"token": "secret-token", "raw_text": "private lead page body", "lead_count": 3},
            },
        },
        agents_base_url="http://localhost:8010",
    )

    summary_text = str(task["output_summary_json"])
    assert "sk-should-not-appear" not in summary_text
    assert "agents-secret" not in summary_text
    assert "secret-token" not in summary_text
    assert "very long lead data" not in summary_text
    assert "private lead page body" not in summary_text
    assert task["output_summary_json"]["api_key"] == "[REDACTED]"
    assert task["output_summary_json"]["input_json"] == "[REDACTED]"
    assert task["output_summary_json"]["external_agent_audit"]["input_summary"]["token"] == "[REDACTED]"
    assert task["output_summary_json"]["external_agent_audit"]["input_summary"]["raw_text"] == "[REDACTED]"
