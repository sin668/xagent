from copy import deepcopy
from datetime import UTC, datetime

from app.models.enums import AgentTaskRunStatus, AgentTaskType
from app.services.agent_retries import AgentRetryPolicy


class AgentTaskRunService:
    MAX_RETRY_COUNT = 3

    @staticmethod
    def _now() -> datetime:
        return datetime.now(UTC)

    @staticmethod
    def build_initial_payload(
        *,
        task_type: AgentTaskType,
        trigger_source: str,
        input_json: dict,
        retry_count: int = 0,
    ) -> dict:
        now = AgentTaskRunService._now()
        return {
            "task_type": task_type,
            "status": AgentTaskRunStatus.PENDING,
            "trigger_source": trigger_source,
            "input_json": input_json,
            "output_summary_json": None,
            "llm_provider": None,
            "llm_model": None,
            "prompt_template_id": None,
            "prompt_version": None,
            "token_usage_json": None,
            "latency_ms": None,
            "error_message": None,
            "retry_count": retry_count,
            "started_at": None,
            "finished_at": None,
            "created_at": now,
            "updated_at": now,
        }

    @staticmethod
    def start(task_run: dict) -> dict:
        if task_run.get("status") not in {AgentTaskRunStatus.PENDING, AgentTaskRunStatus.RETRY_PENDING}:
            raise ValueError("只有 pending 或 retry_pending 状态可以启动")
        next_run = deepcopy(task_run)
        now = AgentTaskRunService._now()
        next_run["status"] = AgentTaskRunStatus.RUNNING
        next_run["started_at"] = now
        next_run["finished_at"] = None
        next_run["updated_at"] = now
        return next_run

    @staticmethod
    def succeed(task_run: dict, *, output_summary_json: dict) -> dict:
        if task_run.get("status") != AgentTaskRunStatus.RUNNING:
            raise ValueError("只有 running 状态可以标记为 succeeded")
        next_run = deepcopy(task_run)
        now = AgentTaskRunService._now()
        next_run["status"] = AgentTaskRunStatus.SUCCEEDED
        next_run["output_summary_json"] = output_summary_json
        next_run["error_message"] = None
        next_run["finished_at"] = now
        next_run["updated_at"] = now
        return next_run

    @staticmethod
    def fail(task_run: dict, *, error_message: str, error: dict | None = None) -> dict:
        if task_run.get("status") != AgentTaskRunStatus.RUNNING:
            raise ValueError("只有 running 状态可以标记为 failed")
        next_run = deepcopy(task_run)
        now = AgentTaskRunService._now()
        retry_count = int(next_run.get("retry_count", 0))
        decision = AgentRetryPolicy.evaluate(error=error, retry_count=retry_count)
        next_run["status"] = AgentTaskRunStatus.RETRY_PENDING if decision.should_retry else AgentTaskRunStatus.FAILED
        next_run["error_message"] = error_message
        next_run["finished_at"] = None if decision.should_retry else now
        next_run["updated_at"] = now
        if decision.should_retry:
            next_run["retry_count"] = retry_count + 1
        if error is not None:
            next_run["output_summary_json"] = {
                **(next_run.get("output_summary_json") or {}),
                "error": error,
                "retry_decision": {
                    "should_retry": decision.should_retry,
                    "reason": decision.reason,
                    "error_type": decision.error_type,
                },
            }
        return next_run

    @classmethod
    def mark_retry_pending(cls, task_run: dict) -> dict:
        if task_run.get("status") != AgentTaskRunStatus.FAILED:
            raise ValueError("只有 failed 状态可以进入 retry_pending")
        retry_count = int(task_run.get("retry_count", 0))
        if retry_count >= cls.MAX_RETRY_COUNT:
            raise ValueError("retry_count 已达到最大值 3")
        next_run = deepcopy(task_run)
        now = cls._now()
        next_run["status"] = AgentTaskRunStatus.RETRY_PENDING
        next_run["retry_count"] = retry_count + 1
        next_run["finished_at"] = None
        next_run["updated_at"] = now
        return next_run
