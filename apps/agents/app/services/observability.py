from __future__ import annotations

from datetime import datetime
from typing import Any

from app.models.agent_service_run import AgentServiceRun


SENSITIVE_KEYS = {
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
    "source_content",
    "source_text",
    "text",
    "token",
}


class AgentServiceRunObservabilityService:
    @classmethod
    def snapshot(cls, run: AgentServiceRun) -> dict[str, Any]:
        audit = run.audit_json or {}
        executed_nodes = cls.extract_executed_nodes(audit.get("executed_nodes"))
        source_urls = audit.get("source_urls") if isinstance(audit.get("source_urls"), list) else []
        return {
            "id": str(run.id),
            "request_id": str(run.request_id),
            "agent_type": run.agent_type,
            "agent_mode": run.agent_mode,
            "status": run.status,
            "trigger_source": run.trigger_source,
            "retry_count": run.retry_count,
            "max_retries": run.max_retries,
            "error_type": run.error_type,
            "error_message": run.error_message,
            "started_at": run.started_at,
            "finished_at": run.finished_at,
            "duration_ms": cls.duration_ms(run.started_at, run.finished_at),
            "executed_nodes": executed_nodes,
            "executed_node_count": len(executed_nodes),
            "failed_node": audit.get("failed_node"),
            "risk_flags": cls.unique_strings(audit.get("risk_flags") if isinstance(audit.get("risk_flags"), list) else []),
            "source_url_count": len(source_urls),
            "input_summary": cls.redact(run.input_json or {}),
            "output_summary_json": cls.redact(run.output_summary_json or {}),
            "audit_summary": cls.audit_summary(audit),
        }

    @classmethod
    def audit_summary(cls, audit: dict[str, Any]) -> dict[str, Any]:
        return {
            "writes_core_tables": audit.get("writes_core_tables"),
            "executed_node_count": len(cls.extract_executed_nodes(audit.get("executed_nodes"))),
            "failed_node": audit.get("failed_node"),
            "risk_flags": cls.unique_strings(audit.get("risk_flags") if isinstance(audit.get("risk_flags"), list) else []),
            "source_url_count": len(audit.get("source_urls") if isinstance(audit.get("source_urls"), list) else []),
        }

    @staticmethod
    def duration_ms(started_at: datetime | None, finished_at: datetime | None) -> int | None:
        if not isinstance(started_at, datetime) or not isinstance(finished_at, datetime):
            return None
        return int((finished_at - started_at).total_seconds() * 1000)

    @staticmethod
    def extract_executed_nodes(raw_nodes: Any) -> list[str]:
        if not isinstance(raw_nodes, list):
            return []
        nodes: list[str] = []
        for item in raw_nodes:
            if isinstance(item, str):
                nodes.append(item)
            elif isinstance(item, dict) and item.get("node"):
                nodes.append(str(item["node"]))
        return nodes

    @classmethod
    def redact(cls, value: Any) -> Any:
        if isinstance(value, dict):
            return {
                str(key): "[REDACTED]" if str(key).lower() in SENSITIVE_KEYS else cls.redact(item)
                for key, item in value.items()
            }
        if isinstance(value, list):
            return [cls.redact(item) for item in value]
        return value

    @staticmethod
    def unique_strings(values: list) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for item in values:
            value = str(item)
            if value in seen:
                continue
            seen.add(value)
            result.append(value)
        return result
