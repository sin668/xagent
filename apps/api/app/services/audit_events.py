from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import ReviewLog


class Phase3AuditEventService:
    SUPPORTED_EVENTS = {
        "lead_deep_enrichment_started",
        "lead_enrichment_field_accepted",
        "lead_enrichment_field_rejected",
        "lead_promoted_to_customer",
        "lead_cleanup_suggestion_created",
        "lead_cleanup_suggestion_approved",
        "lead_cleanup_suggestion_executed",
        "customer_assigned",
        "customer_do_not_contact_marked",
        "phase3_compliance_block",
    }

    @staticmethod
    def serialize_evidence(evidence: dict[str, Any] | None) -> str:
        if not evidence:
            return "evidence={}"
        parts = []
        for key in sorted(evidence):
            value = evidence[key]
            parts.append(f"{key}={value}")
        return ";".join(parts)

    @classmethod
    def record_event(
        cls,
        session: Session | Any,
        *,
        event_name: str,
        actor: str | None,
        entity_type: str,
        entity_id: UUID | str,
        reason: str | None,
        evidence: dict[str, Any] | None,
        occurred_at: datetime | None = None,
    ) -> ReviewLog:
        if event_name not in cls.SUPPORTED_EVENTS:
            raise ValueError(f"不支持的第三阶段审计事件: {event_name}")
        timestamp = occurred_at or datetime.now(UTC)
        entity_ref = f"{entity_type}:{entity_id}"
        log = ReviewLog(
            task_id=str(entity_id),
            agent_name="phase3-audit-event",
            action=event_name,
            reviewer=actor,
            input_ref=f"entity_type={entity_type};entity_id={entity_id};occurred_at={timestamp.isoformat()}",
            output_ref=cls.serialize_evidence(evidence),
            result="recorded",
            error_message=reason,
        )
        session.add(log)
        flush = getattr(session, "flush", None)
        if callable(flush):
            flush()
        return log
