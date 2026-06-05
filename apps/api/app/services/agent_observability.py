from __future__ import annotations

from datetime import datetime
from typing import Any

from app.services.agent_task_runs import AgentTaskRunService


class AgentObservabilitySummaryService:
    @classmethod
    def demo_summaries(cls) -> list[dict]:
        started_at = datetime(2026, 6, 5, 9, 0, 0)
        succeeded_task = {
            "id": "22222222-2222-2222-2222-222222222222",
            "status": "succeeded",
            "retry_count": 1,
            "latency_ms": 980,
            "output_summary_json": {
                "external_agent_run_id": "44444444-4444-4444-4444-444444444444",
                "external_agent_status": "succeeded",
                "external_agent_type": "lead_extraction_grading",
                "external_agent_mode": "shadow",
                "agents_base_url": "http://localhost:8010",
            },
        }
        succeeded_agent = {
            "id": "44444444-4444-4444-4444-444444444444",
            "agent_type": "lead_extraction_grading",
            "agent_mode": "shadow",
            "status": "succeeded",
            "retry_count": 0,
            "started_at": started_at,
            "finished_at": started_at.replace(microsecond=900000),
            "output_summary_json": {"hard_rules_applied": False, "risk_flags": []},
            "audit_json": {
                "writes_core_tables": False,
                "executed_nodes": [
                    "lead_extraction.load_source_content",
                    "lead_extraction.extract_candidate_fields",
                    "lead_grading.apply_hard_rules",
                ],
                "risk_flags": [],
                "source_urls": ["https://autocity.example"],
            },
        }
        failed_task = {
            "id": "33333333-3333-3333-3333-333333333333",
            "status": "retry_pending",
            "retry_count": 2,
            "latency_ms": None,
            "output_summary_json": {
                "external_agent_run_id": "55555555-5555-5555-5555-555555555555",
                "external_agent_status": "failed",
                "external_agent_type": "source_discovery",
                "external_agent_mode": "shadow",
                "agents_base_url": "http://localhost:8010",
            },
        }
        failed_agent = {
            "id": "55555555-5555-5555-5555-555555555555",
            "agent_type": "source_discovery",
            "agent_mode": "shadow",
            "status": "failed",
            "retry_count": 2,
            "error_type": "risk_blocked",
            "error_message": "Forbidden source",
            "started_at": started_at,
            "finished_at": started_at.replace(second=2),
            "output_summary_json": {"candidate_count": 0, "blocked_item_count": 1},
            "audit_json": {
                "writes_core_tables": False,
                "executed_nodes": ["load_channel_strategy", "validate_source_evidence"],
                "failed_node": "validate_source_evidence",
                "risk_flags": ["forbidden_source"],
                "source_urls": [],
            },
        }
        return [
            cls.build_summary(api_task_run=succeeded_task, agent_service_run=succeeded_agent),
            cls.build_summary(api_task_run=failed_task, agent_service_run=failed_agent),
        ]

    @classmethod
    def build_summary(cls, *, api_task_run: dict, agent_service_run: dict | None) -> dict:
        api_summary = cls.redact(api_task_run.get("output_summary_json") or {})
        external_agent_run_id = api_summary.get("external_agent_run_id")
        agent_service_run_id = cls.safe_str(agent_service_run.get("id")) if agent_service_run else None
        agent_audit = agent_service_run.get("audit_json") if isinstance(agent_service_run, dict) else {}
        agent_audit = agent_audit if isinstance(agent_audit, dict) else {}

        link_status = cls.link_status(
            external_agent_run_id=external_agent_run_id,
            agent_service_run_id=agent_service_run_id,
            agent_service_run=agent_service_run,
        )
        executed_nodes = cls.extract_executed_nodes(agent_audit.get("executed_nodes"))
        risk_flags = cls.unique_strings(agent_audit.get("risk_flags") if isinstance(agent_audit.get("risk_flags"), list) else [])
        source_urls = agent_audit.get("source_urls") if isinstance(agent_audit.get("source_urls"), list) else []

        agent_mode = cls.safe_str(agent_service_run.get("agent_mode")) if agent_service_run else api_summary.get("external_agent_mode")
        return {
            "api_task_run_id": cls.safe_str(api_task_run.get("id")),
            "external_agent_run_id": external_agent_run_id,
            "agent_service_run_id": agent_service_run_id,
            "link_status": link_status,
            "agent_type": cls.safe_str(agent_service_run.get("agent_type")) if agent_service_run else api_summary.get("external_agent_type"),
            "agent_mode": agent_mode,
            "is_active_run": agent_mode == "active",
            "is_shadow_run": agent_mode == "shadow",
            "api_status": cls.enum_or_str(api_task_run.get("status")),
            "agent_status": cls.safe_str(agent_service_run.get("status")) if agent_service_run else None,
            "duration_ms": cls.duration_ms(agent_service_run),
            "api_latency_ms": api_task_run.get("latency_ms"),
            "api_retry_count": int(api_task_run.get("retry_count") or 0),
            "agent_retry_count": int(agent_service_run.get("retry_count") or 0) if agent_service_run else None,
            "error_type": cls.safe_str(agent_service_run.get("error_type")) if agent_service_run else None,
            "error_message": cls.safe_str(agent_service_run.get("error_message")) if agent_service_run else None,
            "failed_node": cls.safe_str(agent_audit.get("failed_node")),
            "executed_nodes": executed_nodes,
            "executed_node_count": len(executed_nodes),
            "risk_flags": risk_flags,
            "source_url_count": len(source_urls),
            "api_summary": api_summary,
            "agent_output_summary": cls.redact(agent_service_run.get("output_summary_json") if agent_service_run else {}),
            "agent_audit_summary": cls.audit_summary(agent_audit),
        }

    @classmethod
    def render_markdown(cls, summaries: list[dict]) -> str:
        lines = [
            "# 第四阶段 Agent 观测摘要",
            "",
            "生成方式：汇总 `apps/api.agent_task_runs.output_summary_json` 与 `apps/agents.agent_service_runs` 脱敏快照。",
            "",
            "| API Task Run | External Run | 关联状态 | Agent | 模式 | API 状态 | Agent 状态 | 耗时(ms) | retry | 节点数 | 风险标记 |",
            "|---|---|---|---|---|---|---|---:|---:|---:|---|",
        ]
        for item in summaries:
            lines.append(
                "| {api_task_run_id} | {external_agent_run_id} | {link_status} | {agent_type} | {agent_mode} | {api_status} | {agent_status} | {duration_ms} | {retry_count} | {executed_node_count} | {risk_flags} |".format(
                    api_task_run_id=item.get("api_task_run_id") or "",
                    external_agent_run_id=item.get("external_agent_run_id") or "",
                    link_status=item.get("link_status") or "",
                    agent_type=item.get("agent_type") or "",
                    agent_mode=item.get("agent_mode") or "",
                    api_status=item.get("api_status") or "",
                    agent_status=item.get("agent_status") or "",
                    duration_ms=item.get("duration_ms") if item.get("duration_ms") is not None else "",
                    retry_count=item.get("agent_retry_count") if item.get("agent_retry_count") is not None else "",
                    executed_node_count=item.get("executed_node_count") or 0,
                    risk_flags=", ".join(item.get("risk_flags") or []),
                )
            )
        lines.extend(["", "## 节点 Trace 摘要", ""])
        for item in summaries:
            lines.append(f"### {item.get('external_agent_run_id') or '未关联外部 run'}")
            lines.append("")
            if item.get("executed_nodes"):
                for node in item["executed_nodes"]:
                    lines.append(f"- {node}")
            else:
                lines.append("- 无 executed_nodes。")
            lines.append("")
        return "\n".join(lines)

    @classmethod
    def link_status(
        cls,
        *,
        external_agent_run_id: Any,
        agent_service_run_id: str | None,
        agent_service_run: dict | None,
    ) -> str:
        if not external_agent_run_id:
            return "missing_external_agent_run_id"
        if agent_service_run is None:
            return "missing_agent_service_run"
        if str(external_agent_run_id) != str(agent_service_run_id):
            return "mismatched_agent_service_run"
        return "linked"

    @classmethod
    def duration_ms(cls, agent_service_run: dict | None) -> int | None:
        if not agent_service_run:
            return None
        started_at = agent_service_run.get("started_at")
        finished_at = agent_service_run.get("finished_at")
        if not isinstance(started_at, datetime) or not isinstance(finished_at, datetime):
            return None
        return int((finished_at - started_at).total_seconds() * 1000)

    @classmethod
    def extract_executed_nodes(cls, raw_nodes: Any) -> list[str]:
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
    def audit_summary(cls, audit: dict) -> dict:
        return {
            "writes_core_tables": audit.get("writes_core_tables"),
            "failed_node": audit.get("failed_node"),
            "executed_node_count": len(cls.extract_executed_nodes(audit.get("executed_nodes"))),
            "risk_flags": cls.unique_strings(audit.get("risk_flags") if isinstance(audit.get("risk_flags"), list) else []),
            "source_url_count": len(audit.get("source_urls") if isinstance(audit.get("source_urls"), list) else []),
        }

    @classmethod
    def redact(cls, value):
        return AgentTaskRunService._redact_summary(value or {})

    @staticmethod
    def safe_str(value: Any) -> str | None:
        if value is None:
            return None
        return str(value)

    @staticmethod
    def enum_or_str(value: Any) -> str | None:
        if value is None:
            return None
        return str(getattr(value, "value", value))

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
