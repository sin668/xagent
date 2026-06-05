from pathlib import Path

from app.models.enums import AgentTaskRunStatus, AgentTaskType
from app.services.agent_task_runs import AgentTaskRunService


API_ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = API_ROOT / "alembic" / "versions" / "20260602_0021_create_agent_task_runs.py"


def test_agent_task_runs_migration_declares_required_table_and_fields() -> None:
    assert MIGRATION_PATH.exists()
    migration = MIGRATION_PATH.read_text(encoding="utf-8")

    assert 'revision = "20260602_0021"' in migration
    assert 'down_revision = "20260602_0020"' in migration
    assert '"agent_task_runs"' in migration
    for field_name in (
        "task_type",
        "status",
        "trigger_source",
        "input_json",
        "output_summary_json",
        "llm_provider",
        "llm_model",
        "prompt_template_id",
        "prompt_version",
        "token_usage_json",
        "latency_ms",
        "error_message",
        "retry_count",
        "started_at",
        "finished_at",
        "created_at",
        "updated_at",
    ):
        assert field_name in migration


def test_agent_task_run_model_and_schema_are_registered() -> None:
    models_init = (API_ROOT / "app" / "models" / "__init__.py").read_text(encoding="utf-8")
    schema_file = API_ROOT / "app" / "schemas" / "agent_task_run.py"

    assert "AgentTaskRun" in models_init
    assert schema_file.exists()


def test_agent_task_type_and_status_enums_are_available() -> None:
    assert AgentTaskType.SOURCE_DISCOVERY == "SOURCE_DISCOVERY"
    assert AgentTaskType.LEAD_EXTRACTION == "LEAD_EXTRACTION"
    assert AgentTaskType.LEAD_GRADING == "LEAD_GRADING"
    assert AgentTaskType.RETRY_WORKER == "RETRY_WORKER"
    assert AgentTaskType.EMAIL_REPLY == "EMAIL_REPLY"

    assert AgentTaskRunStatus.PENDING == "pending"
    assert AgentTaskRunStatus.RUNNING == "running"
    assert AgentTaskRunStatus.SUCCEEDED == "succeeded"
    assert AgentTaskRunStatus.FAILED == "failed"
    assert AgentTaskRunStatus.RETRY_PENDING == "retry_pending"
    assert AgentTaskRunStatus.PAUSED == "paused"
    assert AgentTaskRunStatus.CANCELLED == "cancelled"
    assert AgentTaskRunStatus.MANUAL_REVIEW_REQUIRED == "manual_review_required"


def test_agent_task_run_service_start_succeed_fail_and_retry_payloads() -> None:
    pending = AgentTaskRunService.build_initial_payload(
        task_type=AgentTaskType.SOURCE_DISCOVERY,
        trigger_source="manual",
        input_json={"country": "Russia"},
    )
    assert pending["status"] == AgentTaskRunStatus.PENDING
    assert pending["retry_count"] == 0
    assert pending["input_json"] == {"country": "Russia"}

    running = AgentTaskRunService.start(pending)
    assert running["status"] == AgentTaskRunStatus.RUNNING
    assert running["started_at"] is not None

    succeeded = AgentTaskRunService.succeed(running, output_summary_json={"created_count": 12})
    assert succeeded["status"] == AgentTaskRunStatus.SUCCEEDED
    assert succeeded["output_summary_json"] == {"created_count": 12}
    assert succeeded["finished_at"] is not None

    failed = AgentTaskRunService.fail(running, error_message="LLM timeout")
    assert failed["status"] == AgentTaskRunStatus.FAILED
    assert failed["error_message"] == "LLM timeout"
    assert failed["finished_at"] is not None

    retry = AgentTaskRunService.mark_retry_pending(failed)
    assert retry["status"] == AgentTaskRunStatus.RETRY_PENDING
    assert retry["retry_count"] == 1
    assert retry["finished_at"] is None


def test_agent_task_run_service_rejects_invalid_state_transitions() -> None:
    pending = AgentTaskRunService.build_initial_payload(
        task_type=AgentTaskType.LEAD_EXTRACTION,
        trigger_source="scheduler",
        input_json={},
    )

    try:
        AgentTaskRunService.succeed(pending, output_summary_json={})
    except ValueError as exc:
        assert "只有 running 状态可以标记为 succeeded" in str(exc)
    else:
        raise AssertionError("Pending task should not be marked succeeded")

    succeeded = AgentTaskRunService.succeed(AgentTaskRunService.start(pending), output_summary_json={})
    try:
        AgentTaskRunService.mark_retry_pending(succeeded)
    except ValueError as exc:
        assert "只有 failed 状态可以进入 retry_pending" in str(exc)
    else:
        raise AssertionError("Succeeded task should not be retried")


def test_agent_task_run_service_rejects_retry_after_max_attempts() -> None:
    failed = AgentTaskRunService.fail(
        AgentTaskRunService.start(
            AgentTaskRunService.build_initial_payload(
                task_type=AgentTaskType.RETRY_WORKER,
                trigger_source="scheduler",
                input_json={},
                retry_count=3,
            )
        ),
        error_message="network failed",
    )

    try:
        AgentTaskRunService.mark_retry_pending(failed)
    except ValueError as exc:
        assert "retry_count 已达到最大值 3" in str(exc)
    else:
        raise AssertionError("Task should reject retry after max attempts")
