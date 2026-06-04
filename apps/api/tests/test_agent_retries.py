from datetime import UTC, datetime, timedelta

from app.models.enums import AgentTaskRunStatus, AgentTaskType
from app.services.agent_retries import AgentRetryPolicy, AgentRetryRecoveryService
from app.services.agent_task_runs import AgentTaskRunService


def make_running_task(*, started_delta: timedelta, retry_count: int = 0, error_type: str | None = None) -> dict:
    now = datetime(2026, 6, 2, 8, 0, 0, tzinfo=UTC)
    task = AgentTaskRunService.build_initial_payload(
        task_type=AgentTaskType.SOURCE_DISCOVERY,
        trigger_source="scheduler",
        input_json={"country": "Russia"},
        retry_count=retry_count,
    )
    task["status"] = AgentTaskRunStatus.RUNNING
    task["started_at"] = now - started_delta
    task["updated_at"] = now - started_delta
    task["error_message"] = error_type or None
    return task


def test_agent_retry_policy_allows_only_technical_failures_until_max_retry_count() -> None:
    for error_type in ("network_error", "timeout_error", "rate_limit_error"):
        decision = AgentRetryPolicy.evaluate(error={"type": error_type}, retry_count=2)
        assert decision.should_retry is True
        assert decision.reason == "technical_failure_retry_allowed"

    maxed = AgentRetryPolicy.evaluate(error={"type": "timeout_error"}, retry_count=3)
    assert maxed.should_retry is False
    assert maxed.reason == "max_retry_count_reached"


def test_agent_retry_policy_blocks_schema_risk_and_forbidden_failures() -> None:
    for error_type in (
        "schema_validation_error",
        "suspected_fabrication",
        "risk_blocked",
        "forbidden_risk",
        "high_risk_blocked",
        "source_risk_exception",
    ):
        decision = AgentRetryPolicy.evaluate(error={"type": error_type}, retry_count=0)

        assert decision.should_retry is False
        assert decision.reason == "compliance_or_schema_failure_not_retryable"


def test_agent_task_run_service_fail_can_mark_retry_pending_for_retryable_technical_failure() -> None:
    running = AgentTaskRunService.start(
        AgentTaskRunService.build_initial_payload(
            task_type=AgentTaskType.LEAD_EXTRACTION,
            trigger_source="scheduler",
            input_json={},
            retry_count=1,
        )
    )

    failed = AgentTaskRunService.fail(
        running,
        error_message="LLM timeout",
        error={"type": "timeout_error", "message": "LLM timeout"},
    )

    assert failed["status"] == AgentTaskRunStatus.RETRY_PENDING
    assert failed["retry_count"] == 2
    assert failed["output_summary_json"]["error"]["type"] == "timeout_error"


def test_agent_task_run_service_fail_keeps_schema_and_forbidden_failures_failed() -> None:
    running = AgentTaskRunService.start(
        AgentTaskRunService.build_initial_payload(
            task_type=AgentTaskType.LEAD_EXTRACTION,
            trigger_source="scheduler",
            input_json={},
        )
    )

    failed = AgentTaskRunService.fail(
        running,
        error_message="Forbidden 来源不得进入自动抽取",
        error={"type": "forbidden_risk", "message": "Forbidden 来源不得进入自动抽取"},
    )

    assert failed["status"] == AgentTaskRunStatus.FAILED
    assert failed["retry_count"] == 0
    assert failed["output_summary_json"]["error"]["type"] == "forbidden_risk"


def test_recovery_marks_timed_out_running_task_retry_pending_when_retryable() -> None:
    now = datetime(2026, 6, 2, 8, 0, 0, tzinfo=UTC)
    service = AgentRetryRecoveryService(timeout_seconds=600, now_provider=lambda: now)
    stale = make_running_task(started_delta=timedelta(seconds=900), retry_count=0)

    recovered = service.recover_timed_out_task(stale)

    assert recovered["status"] == AgentTaskRunStatus.RETRY_PENDING
    assert recovered["retry_count"] == 1
    assert recovered["error_message"] == "agent_task_timeout"
    assert recovered["output_summary_json"]["error"]["type"] == "timeout_error"


def test_recovery_leaves_fresh_running_task_unchanged() -> None:
    now = datetime(2026, 6, 2, 8, 0, 0, tzinfo=UTC)
    service = AgentRetryRecoveryService(timeout_seconds=600, now_provider=lambda: now)
    fresh = make_running_task(started_delta=timedelta(seconds=120), retry_count=0)

    recovered = service.recover_timed_out_task(fresh)

    assert recovered is fresh
    assert recovered["status"] == AgentTaskRunStatus.RUNNING


def test_recovery_marks_timed_out_task_failed_after_max_retry_count() -> None:
    now = datetime(2026, 6, 2, 8, 0, 0, tzinfo=UTC)
    service = AgentRetryRecoveryService(timeout_seconds=600, now_provider=lambda: now)
    stale = make_running_task(started_delta=timedelta(seconds=900), retry_count=3)

    recovered = service.recover_timed_out_task(stale)

    assert recovered["status"] == AgentTaskRunStatus.FAILED
    assert recovered["retry_count"] == 3
    assert recovered["error_message"] == "agent_task_timeout"
    assert recovered["output_summary_json"]["retry_decision"]["reason"] == "max_retry_count_reached"
