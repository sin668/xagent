from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AgentRunLog, AIAuditLog, ReviewLog, RiskEvent
from app.models.enums import AITaskType, ChannelRiskLevel, RiskEventSeverity, RiskEventStatus


PRIVATE_AUDIT_KEYS = {"password", "token", "secret", "private_chat", "private_note", "cookie", "authorization"}


class AuditRiskLogService:
    def __init__(self, session: Session) -> None:
        self.session = session

    @staticmethod
    def sanitize_audit_payload(payload: dict | None) -> dict | None:
        if payload is None:
            return None
        return {key: value for key, value in payload.items() if key.lower() not in PRIVATE_AUDIT_KEYS}

    @staticmethod
    def build_ai_audit_payload(
        *,
        prompt_version: str,
        model_name: str,
        output_json: dict,
        source_urls: list[str],
        channel_name: str | None = None,
    ) -> dict:
        return {
            "prompt_version": prompt_version,
            "model_name": model_name,
            "channel_name": channel_name,
            "output_json": output_json,
            "source_urls": source_urls,
        }

    @staticmethod
    def build_risk_event_payload(
        *,
        channel: str,
        risk_level: str,
        event_type: str,
        block_reason: str,
        severity: str | RiskEventSeverity | None = None,
        resolution_status: str | RiskEventStatus | None = None,
    ) -> dict:
        risk = ChannelRiskLevel(risk_level)
        resolved_severity = RiskEventSeverity(severity) if severity is not None else AuditRiskLogService.default_severity(risk)
        resolved_status = RiskEventStatus(resolution_status) if resolution_status is not None else RiskEventStatus.OPEN
        return {
            "channel": channel,
            "risk_level": risk.value,
            "event_type": event_type,
            "severity": resolved_severity,
            "resolution_status": resolved_status,
            "block_reason": block_reason,
        }

    @staticmethod
    def default_severity(risk_level: ChannelRiskLevel) -> RiskEventSeverity:
        if risk_level == ChannelRiskLevel.FORBIDDEN:
            return RiskEventSeverity.CRITICAL
        if risk_level == ChannelRiskLevel.HIGH:
            return RiskEventSeverity.HIGH
        if risk_level == ChannelRiskLevel.MEDIUM:
            return RiskEventSeverity.MEDIUM
        return RiskEventSeverity.LOW

    @staticmethod
    def should_suggest_channel_pause(
        *,
        event_type: str,
        severity: str | RiskEventSeverity,
        block_reason: str | None,
    ) -> bool:
        resolved_severity = RiskEventSeverity(severity)
        if resolved_severity in {RiskEventSeverity.HIGH, RiskEventSeverity.CRITICAL}:
            return True
        normalized_type = event_type.strip().lower()
        if normalized_type in {"complaint", "account_ban", "policy_violation", "platform_warning"}:
            return True
        reason = (block_reason or "").lower()
        return any(keyword in reason for keyword in ("投诉", "封禁", "违规", "complaint", "ban", "violation"))

    def record_ai_audit(
        self,
        *,
        task_type: str | AITaskType,
        model_name: str,
        prompt_version: str,
        output_json: dict,
        source_urls: list[str],
        input_payload: dict | None = None,
        channel_name: str | None = None,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        total_tokens: int | None = None,
        cost_amount: float | None = None,
        cost_currency: str | None = None,
        risk_blocked: bool = False,
        risk_block_reason: str | None = None,
    ) -> AIAuditLog:
        audit = AIAuditLog(
            task_type=AITaskType(task_type),
            model_name=model_name,
            prompt_version=prompt_version,
            channel_name=channel_name,
            source_url=source_urls[0] if source_urls else None,
            source_urls=source_urls,
            input_payload=self.sanitize_audit_payload(input_payload),
            output_payload=output_json,
            output_json=output_json,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            cost_amount=cost_amount,
            cost_currency=cost_currency,
            risk_blocked=risk_blocked,
            risk_block_reason=risk_block_reason,
            executed_at=datetime.utcnow(),
        )
        self.session.add(audit)
        self.session.flush()
        return audit

    def record_agent_run(
        self,
        *,
        task_id: str | None,
        agent_name: str,
        action: str,
        input_ref: str | None,
        output_ref: str | None,
        result: str,
        error_message: str | None = None,
    ) -> AgentRunLog:
        log = AgentRunLog(
            task_id=task_id,
            agent_name=agent_name,
            action=action,
            input_ref=input_ref,
            output_ref=output_ref,
            result=result,
            error_message=error_message,
            created_at=datetime.utcnow(),
        )
        self.session.add(log)
        self.session.flush()
        return log

    def record_review_log(
        self,
        *,
        task_id: str | None,
        agent_name: str | None,
        action: str,
        reviewer: str | None,
        input_ref: str | None,
        output_ref: str | None,
        result: str,
        error_message: str | None = None,
    ) -> ReviewLog:
        log = ReviewLog(
            task_id=task_id,
            agent_name=agent_name,
            action=action,
            reviewer=reviewer,
            input_ref=input_ref,
            output_ref=output_ref,
            result=result,
            error_message=error_message,
            created_at=datetime.utcnow(),
        )
        self.session.add(log)
        self.session.flush()
        return log

    def record_risk_event(
        self,
        *,
        channel: str,
        risk_level: str | ChannelRiskLevel,
        event_type: str,
        block_reason: str,
        channel_plan_id: UUID | str | None = None,
        task_id: str | None = None,
        agent_name: str | None = None,
        action: str | None = None,
        severity: str | RiskEventSeverity | None = None,
        resolution_status: str | RiskEventStatus | None = None,
        pause_suggested: bool | None = None,
        input_ref: str | None = None,
        output_ref: str | None = None,
        result: str = "blocked",
        error_message: str | None = None,
    ) -> RiskEvent:
        payload = self.build_risk_event_payload(
            channel=channel,
            risk_level=ChannelRiskLevel(risk_level).value,
            event_type=event_type,
            block_reason=block_reason,
            severity=severity,
            resolution_status=resolution_status,
        )
        resolved_pause_suggested = (
            pause_suggested
            if pause_suggested is not None
            else self.should_suggest_channel_pause(
                event_type=event_type,
                severity=payload["severity"],
                block_reason=block_reason,
            )
        )
        event = RiskEvent(
            channel_plan_id=UUID(str(channel_plan_id)) if channel_plan_id is not None else None,
            task_id=task_id,
            agent_name=agent_name,
            action=action,
            channel=channel,
            risk_level=ChannelRiskLevel(payload["risk_level"]),
            event_type=event_type,
            severity=payload["severity"],
            resolution_status=payload["resolution_status"],
            block_reason=block_reason,
            pause_suggested=resolved_pause_suggested,
            input_ref=input_ref,
            output_ref=output_ref,
            result=result,
            error_message=error_message,
            created_at=datetime.utcnow(),
        )
        self.session.add(event)
        self.session.flush()
        return event

    def list_risk_events(
        self,
        *,
        severity: str | RiskEventSeverity | None = None,
        resolution_status: str | RiskEventStatus | None = None,
        channel_plan_id: UUID | None = None,
        limit: int = 100,
    ) -> list[RiskEvent]:
        statement = select(RiskEvent).order_by(RiskEvent.created_at.desc()).limit(limit)
        if severity is not None:
            statement = statement.where(RiskEvent.severity == RiskEventSeverity(severity))
        if resolution_status is not None:
            statement = statement.where(RiskEvent.resolution_status == RiskEventStatus(resolution_status))
        if channel_plan_id is not None:
            statement = statement.where(RiskEvent.channel_plan_id == channel_plan_id)
        return list(self.session.scalars(statement).all())

    def resolve_risk_event(
        self,
        *,
        event_id: UUID,
        resolution_note: str,
        resolved_by: str | None = None,
    ) -> RiskEvent:
        if not resolution_note.strip():
            raise ValueError("风险事件处理必须记录处理说明。")
        event = self.session.get(RiskEvent, event_id)
        if event is None:
            raise ValueError("risk event 不存在。")
        event.resolution_status = RiskEventStatus.RESOLVED
        event.resolution_note = resolution_note.strip()
        event.resolved_by = resolved_by
        event.resolved_at = datetime.utcnow()
        self.session.flush()
        return event
