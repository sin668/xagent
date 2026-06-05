from copy import deepcopy
from datetime import UTC, datetime

from app.models.enums import AgentTaskRunStatus, AgentTaskType
from app.services.agent_retries import AgentRetryPolicy


class AgentTaskRunService:
    MAX_RETRY_COUNT = 3
    SENSITIVE_SUMMARY_KEYS = {
        "api_key",
        "authorization",
        "body",
        "content",
        "cookie",
        "html",
        "input_json",
        "page_text",
        "password",
        "raw_text",
        "secret",
        "source_text",
        "text",
        "token",
    }

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
    def succeed_with_external_agent_summary(
        cls,
        task_run: dict,
        *,
        output_summary_json: dict,
        external_agent_response: dict,
        agents_base_url: str,
    ) -> dict:
        summary = cls.merge_external_agent_summary(
            output_summary_json,
            external_agent_response=external_agent_response,
            agents_base_url=agents_base_url,
        )
        return cls.succeed(task_run, output_summary_json=summary)

    @classmethod
    def fail_with_external_agent_summary(
        cls,
        task_run: dict,
        *,
        error_message: str,
        error: dict | None,
        external_agent_response: dict | None,
        agents_base_url: str,
    ) -> dict:
        failed = cls.fail(task_run, error_message=error_message, error=error)
        failed["output_summary_json"] = cls.merge_external_agent_summary(
            failed.get("output_summary_json") or {},
            external_agent_response=external_agent_response,
            agents_base_url=agents_base_url,
        )
        return failed

    @classmethod
    def merge_external_agent_summary(
        cls,
        output_summary_json: dict | None,
        *,
        external_agent_response: dict | None,
        agents_base_url: str,
    ) -> dict:
        summary = cls._redact_summary(output_summary_json or {})
        if not external_agent_response:
            return summary

        summary.update(
            {
                "external_agent_run_id": external_agent_response.get("agent_service_run_id"),
                "external_agent_status": external_agent_response.get("status"),
                "external_agent_type": external_agent_response.get("agent_type"),
                "external_agent_mode": external_agent_response.get("agent_mode"),
                "agents_base_url": agents_base_url,
            }
        )
        if isinstance(external_agent_response.get("error"), dict):
            summary["external_agent_error"] = cls._redact_summary(external_agent_response["error"])

        audit = external_agent_response.get("audit")
        if isinstance(audit, dict):
            summary["external_agent_audit"] = cls._summarize_external_audit(audit)
        return summary

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

    @classmethod
    def _summarize_external_audit(cls, audit: dict) -> dict:
        executed_nodes = audit.get("executed_nodes") if isinstance(audit.get("executed_nodes"), list) else []
        source_urls = audit.get("source_urls") if isinstance(audit.get("source_urls"), list) else []
        summary = {
            "writes_core_tables": audit.get("writes_core_tables"),
            "executed_node_count": len(executed_nodes),
            "failed_node": audit.get("failed_node"),
            "risk_flags": cls._unique_strings(audit.get("risk_flags") if isinstance(audit.get("risk_flags"), list) else []),
            "source_url_count": len(source_urls),
        }
        for key, value in audit.items():
            if key not in {"writes_core_tables", "executed_nodes", "failed_node", "risk_flags", "source_urls"}:
                summary[key] = "[REDACTED]" if str(key).lower() in cls.SENSITIVE_SUMMARY_KEYS else cls._redact_summary(value)
        return summary

    @classmethod
    def _redact_summary(cls, value):
        if isinstance(value, dict):
            return {
                str(key): "[REDACTED]" if str(key).lower() in cls.SENSITIVE_SUMMARY_KEYS else cls._redact_summary(item)
                for key, item in value.items()
            }
        if isinstance(value, list):
            return [cls._redact_summary(item) for item in value]
        return value

    @staticmethod
    def _unique_strings(values: list) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for item in values:
            value = str(item)
            if value in seen:
                continue
            seen.add(value)
            result.append(value)
        return result
