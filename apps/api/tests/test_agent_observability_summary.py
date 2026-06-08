from datetime import UTC, datetime, timedelta

from app.models.enums import AgentTaskRunStatus, AgentTaskType
from app.services.agent_observability import AgentObservabilitySummaryService
from app.services.agent_task_runs import AgentTaskRunService


def build_task_run() -> dict:
    task = AgentTaskRunService.build_initial_payload(
        task_type=AgentTaskType.LEAD_GRADING,
        trigger_source="phase4_http_agent_runtime",
        input_json={
            "api_key": "sk-should-not-leak",
            "raw_text": "private source text should not leak",
            "staging_lead_id": "33333333-3333-3333-3333-333333333333",
        },
    )
    task["id"] = "22222222-2222-2222-2222-222222222222"
    task["status"] = AgentTaskRunStatus.SUCCEEDED
    task["retry_count"] = 1
    task["latency_ms"] = 980
    task["output_summary_json"] = {
        "external_agent_run_id": "44444444-4444-4444-4444-444444444444",
        "external_agent_status": "succeeded",
        "external_agent_type": "lead_extraction_grading",
        "external_agent_mode": "shadow",
        "agents_base_url": "http://localhost:8010",
        "api_key": "agents-secret",
        "raw_text": "full text should not leak",
    }
    return task


def build_agent_service_run_snapshot() -> dict:
    started_at = datetime(2026, 6, 5, 9, 0, 0, tzinfo=UTC)
    finished_at = started_at + timedelta(milliseconds=1234)
    return {
        "id": "44444444-4444-4444-4444-444444444444",
        "request_id": "11111111-1111-1111-1111-111111111111",
        "agent_type": "lead_extraction_grading",
        "agent_mode": "shadow",
        "status": "succeeded",
        "trigger_source": "shadow_run",
        "retry_count": 2,
        "error_type": None,
        "error_message": None,
        "started_at": started_at,
        "finished_at": finished_at,
        "input_json": {
            "api_key": "agents-api-key",
            "source_content": "private source text",
            "source_url": "https://autocity.example",
        },
        "output_summary_json": {
            "hard_rules_applied": False,
            "risk_flags": ["low_evidence"],
        },
        "audit_json": {
            "writes_core_tables": False,
            "executed_nodes": [
                "lead_extraction.load_source_content",
                {"node": "lead_grading.apply_hard_rules", "status": "succeeded"},
            ],
            "failed_node": None,
            "risk_flags": ["low_evidence"],
            "source_urls": ["https://autocity.example"],
            "input_summary": {"token": "secret-token", "raw_text": "private source text", "lead_count": 1},
        },
    }


def test_observability_summary_links_api_task_run_to_agent_service_run_without_sensitive_leaks() -> None:
    summary = AgentObservabilitySummaryService.build_summary(
        api_task_run=build_task_run(),
        agent_service_run=build_agent_service_run_snapshot(),
    )

    assert summary["api_task_run_id"] == "22222222-2222-2222-2222-222222222222"
    assert summary["external_agent_run_id"] == "44444444-4444-4444-4444-444444444444"
    assert summary["link_status"] == "linked"
    assert summary["agent_type"] == "lead_extraction_grading"
    assert summary["agent_mode"] == "shadow"
    assert summary["is_shadow_run"] is True
    assert summary["is_active_run"] is False
    assert summary["api_status"] == "succeeded"
    assert summary["agent_status"] == "succeeded"
    assert summary["duration_ms"] == 1234
    assert summary["api_retry_count"] == 1
    assert summary["agent_retry_count"] == 2
    assert summary["error_type"] is None
    assert summary["executed_nodes"] == [
        "lead_extraction.load_source_content",
        "lead_grading.apply_hard_rules",
    ]
    assert summary["executed_node_count"] == 2
    assert summary["risk_flags"] == ["low_evidence"]
    assert summary["source_url_count"] == 1

    summary_text = str(summary)
    assert "sk-should-not-leak" not in summary_text
    assert "agents-secret" not in summary_text
    assert "agents-api-key" not in summary_text
    assert "secret-token" not in summary_text
    assert "private source text" not in summary_text
    assert "full text should not leak" not in summary_text


def test_observability_summary_reports_missing_external_agent_run() -> None:
    task = build_task_run()

    summary = AgentObservabilitySummaryService.build_summary(
        api_task_run=task,
        agent_service_run=None,
    )

    assert summary["external_agent_run_id"] == "44444444-4444-4444-4444-444444444444"
    assert summary["link_status"] == "missing_agent_service_run"
    assert summary["agent_status"] is None
    assert summary["executed_nodes"] == []
    assert summary["executed_node_count"] == 0


def test_observability_summary_rejects_mismatched_agent_run_id() -> None:
    snapshot = build_agent_service_run_snapshot()
    snapshot["id"] = "99999999-9999-9999-9999-999999999999"

    summary = AgentObservabilitySummaryService.build_summary(
        api_task_run=build_task_run(),
        agent_service_run=snapshot,
    )

    assert summary["link_status"] == "mismatched_agent_service_run"
    assert summary["external_agent_run_id"] == "44444444-4444-4444-4444-444444444444"
    assert summary["agent_service_run_id"] == "99999999-9999-9999-9999-999999999999"
    assert summary["agent_status"] == "succeeded"


def test_observability_markdown_report_renders_core_fields_without_sensitive_values() -> None:
    summary = AgentObservabilitySummaryService.build_summary(
        api_task_run=build_task_run(),
        agent_service_run=build_agent_service_run_snapshot(),
    )

    report = AgentObservabilitySummaryService.render_markdown([summary])

    assert "# 第四阶段 Agent 观测摘要" in report
    assert "lead_extraction_grading" in report
    assert "shadow" in report
    assert "lead_extraction.load_source_content" in report
    assert "lead_grading.apply_hard_rules" in report
    assert "sk-should-not-leak" not in report
    assert "private source text" not in report
