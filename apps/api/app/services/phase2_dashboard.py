from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.agent_task_run import AgentTaskRun
from app.models.enums import (
    AgentTaskRunStatus,
    AgentTaskType,
    ChannelRiskLevel,
    LeadSourceCandidateExtractionStatus,
    LeadSourceCandidateReviewStatus,
    RiskEventStatus,
)
from app.models.lead_source_candidate import LeadSourceCandidate
from app.models.risk_event import RiskEvent


class Phase2DashboardService:
    GUARDRAIL = (
        "第二阶段 dashboard 仅用于运行监控；不自动社交私信、不自动加好友、不登录后批量采集、"
        "不反爬规避；High/Forbidden 风险必须单独复核。"
    )

    def __init__(self, session: Session) -> None:
        self.session = session

    def metrics(self, *, channel_prefix: str | None = None) -> dict[str, Any]:
        candidates = self._load_candidates(channel_prefix=channel_prefix)
        task_runs = self._load_task_runs(channel_prefix=channel_prefix)
        risk_events = self._load_risk_events(channel_prefix=channel_prefix)

        risk_distribution = self._distribution(
            [candidate.risk_level.value for candidate in candidates],
            [risk.value for risk in ChannelRiskLevel],
        )
        review_backlog = self._review_backlog(candidates)
        extraction_distribution = self._distribution(
            [candidate.extraction_status.value for candidate in candidates],
            [status.value for status in LeadSourceCandidateExtractionStatus],
        )
        failure_reasons = self._failure_reasons(task_runs)
        llm_costs = self._llm_costs(task_runs)
        high_forbidden_risk_events = [
            self._serialize_risk_event(event)
            for event in risk_events
            if event.risk_level in {ChannelRiskLevel.HIGH, ChannelRiskLevel.FORBIDDEN}
        ]

        return {
            "summary": {
                "source_candidate_count": len(candidates),
                "review_backlog_count": sum(review_backlog.values()),
                "auto_extraction_count": sum(
                    1 for candidate in candidates if candidate.extraction_status == LeadSourceCandidateExtractionStatus.SUCCEEDED
                ),
                "agent_task_count": len(task_runs),
                "failed_task_count": sum(1 for task in task_runs if task.status == AgentTaskRunStatus.FAILED),
                "llm_cost_total": llm_costs["total_cost"],
                "risk_event_count": len(risk_events),
                "high_forbidden_risk_event_count": len(high_forbidden_risk_events),
            },
            "risk_distribution": risk_distribution,
            "review_backlog": dict(review_backlog),
            "extraction_status_distribution": extraction_distribution,
            "failure_reasons": failure_reasons,
            "llm_costs": llm_costs,
            "high_forbidden_risk_events": high_forbidden_risk_events,
            "guardrail": self.GUARDRAIL,
        }

    def _load_candidates(self, *, channel_prefix: str | None) -> list[LeadSourceCandidate]:
        statement = select(LeadSourceCandidate)
        if channel_prefix:
            statement = statement.where(LeadSourceCandidate.channel_name.like(f"{channel_prefix}%"))
        return list(self.session.scalars(statement).all())

    def _load_task_runs(self, *, channel_prefix: str | None) -> list[AgentTaskRun]:
        statement = select(AgentTaskRun).where(
            AgentTaskRun.task_type.in_(
                [
                    AgentTaskType.SOURCE_DISCOVERY,
                    AgentTaskType.LEAD_EXTRACTION,
                    AgentTaskType.LEAD_GRADING,
                    AgentTaskType.RETRY_WORKER,
                ]
            )
        )
        if channel_prefix:
            statement = statement.where(AgentTaskRun.trigger_source.like(f"{channel_prefix}%"))
        return list(self.session.scalars(statement).all())

    def _load_risk_events(self, *, channel_prefix: str | None) -> list[RiskEvent]:
        statement = select(RiskEvent).order_by(RiskEvent.created_at.desc())
        if channel_prefix:
            statement = statement.where(RiskEvent.channel.like(f"{channel_prefix}%"))
        return list(self.session.scalars(statement).all())

    def _review_backlog(self, candidates: list[LeadSourceCandidate]) -> dict[str, int]:
        backlog_statuses = {
            LeadSourceCandidateReviewStatus.PENDING,
            LeadSourceCandidateReviewStatus.HIGH_RISK_REVIEW,
            LeadSourceCandidateReviewStatus.NEEDS_RECHECK,
        }
        counter: Counter[str] = Counter()
        for candidate in candidates:
            if candidate.review_status in backlog_statuses:
                counter[candidate.review_status.value] += 1
        return dict(counter)

    def _failure_reasons(self, task_runs: list[AgentTaskRun]) -> list[dict[str, Any]]:
        grouped: dict[str, list[str]] = defaultdict(list)
        for task in task_runs:
            if task.status != AgentTaskRunStatus.FAILED:
                continue
            reason = self._failure_reason(task)
            grouped[reason].append(str(task.id))
        return [
            {"reason": reason, "count": len(ids), "agent_task_run_ids": ids}
            for reason, ids in sorted(grouped.items(), key=lambda item: (-len(item[1]), item[0]))
        ]

    def _failure_reason(self, task: AgentTaskRun) -> str:
        summary = task.output_summary_json if isinstance(task.output_summary_json, dict) else {}
        error = summary.get("error") if isinstance(summary.get("error"), dict) else {}
        return str(error.get("type") or task.error_message or "unknown_failure")

    def _llm_costs(self, task_runs: list[AgentTaskRun]) -> dict[str, Any]:
        items = []
        total_cost = 0.0
        currency = "USD"
        for task in task_runs:
            summary = task.output_summary_json if isinstance(task.output_summary_json, dict) else {}
            cost_amount = float(summary.get("cost_amount") or 0)
            token_usage = task.token_usage_json if isinstance(task.token_usage_json, dict) else {}
            total_tokens = int(token_usage.get("total_tokens") or 0)
            if cost_amount <= 0 and total_tokens <= 0:
                continue
            cost_currency = str(summary.get("cost_currency") or currency)
            currency = cost_currency
            total_cost += cost_amount
            items.append(
                {
                    "agent_task_run_id": str(task.id),
                    "task_type": task.task_type.value,
                    "status": task.status.value,
                    "model": task.llm_model,
                    "prompt_version": task.prompt_version,
                    "cost_amount": cost_amount,
                    "cost_currency": cost_currency,
                    "total_tokens": total_tokens,
                }
            )
        return {"total_cost": round(total_cost, 4), "currency": currency, "items": items}

    def _serialize_risk_event(self, event: RiskEvent) -> dict[str, Any]:
        return {
            "id": str(event.id),
            "task_id": event.task_id,
            "channel": event.channel,
            "risk_level": event.risk_level.value,
            "severity": event.severity.value,
            "resolution_status": event.resolution_status.value if isinstance(event.resolution_status, RiskEventStatus) else str(event.resolution_status),
            "event_type": event.event_type,
            "block_reason": event.block_reason,
            "pause_suggested": event.pause_suggested,
            "created_at": event.created_at.isoformat(),
        }

    def _distribution(self, values: list[str], keys: list[str]) -> dict[str, int]:
        counter = Counter(values)
        return {key: counter.get(key, 0) for key in keys if counter.get(key, 0) > 0}
