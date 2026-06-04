from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC, datetime

from app.models.enums import AgentTaskRunStatus


@dataclass(frozen=True)
class AgentRetryDecision:
    should_retry: bool
    reason: str
    error_type: str | None


class AgentRetryPolicy:
    MAX_RETRY_COUNT = 3
    TECHNICAL_ERROR_TYPES = frozenset({"network_error", "timeout_error", "rate_limit_error"})
    NON_RETRYABLE_ERROR_TYPES = frozenset(
        {
            "schema_validation_error",
            "suspected_fabrication",
            "risk_blocked",
            "forbidden_risk",
            "high_risk_blocked",
            "source_risk_exception",
        }
    )

    @classmethod
    def evaluate(cls, *, error: dict | None, retry_count: int) -> AgentRetryDecision:
        error_type = error.get("type") if isinstance(error, dict) else None
        if retry_count >= cls.MAX_RETRY_COUNT:
            return AgentRetryDecision(False, "max_retry_count_reached", error_type)
        if error_type in cls.TECHNICAL_ERROR_TYPES:
            return AgentRetryDecision(True, "technical_failure_retry_allowed", error_type)
        if error_type in cls.NON_RETRYABLE_ERROR_TYPES:
            return AgentRetryDecision(False, "compliance_or_schema_failure_not_retryable", error_type)
        return AgentRetryDecision(False, "unknown_failure_not_retryable", error_type)


class AgentRetryRecoveryService:
    def __init__(
        self,
        *,
        timeout_seconds: int = 900,
        now_provider: Callable[[], datetime] | None = None,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.now_provider = now_provider or (lambda: datetime.now(UTC))

    def recover_timed_out_task(self, task_run: dict) -> dict:
        if task_run.get("status") != AgentTaskRunStatus.RUNNING:
            return task_run

        started_at = task_run.get("started_at")
        if started_at is None:
            return task_run

        now = self.now_provider()
        if started_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=UTC)
        if (now - started_at).total_seconds() < self.timeout_seconds:
            return task_run

        return self._mark_timeout(task_run, now=now)

    def _mark_timeout(self, task_run: dict, *, now: datetime) -> dict:
        next_run = deepcopy(task_run)
        error = {"type": "timeout_error", "message": "agent_task_timeout"}
        retry_count = int(next_run.get("retry_count", 0))
        decision = AgentRetryPolicy.evaluate(error=error, retry_count=retry_count)
        next_run["error_message"] = "agent_task_timeout"
        next_run["finished_at"] = now
        next_run["updated_at"] = now
        next_run["output_summary_json"] = {
            **(next_run.get("output_summary_json") or {}),
            "error": error,
            "retry_decision": {
                "should_retry": decision.should_retry,
                "reason": decision.reason,
                "error_type": decision.error_type,
            },
        }
        if decision.should_retry:
            next_run["status"] = AgentTaskRunStatus.RETRY_PENDING
            next_run["retry_count"] = retry_count + 1
            next_run["finished_at"] = None
        else:
            next_run["status"] = AgentTaskRunStatus.FAILED
        return next_run
