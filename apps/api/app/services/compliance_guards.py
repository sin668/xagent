from typing import Any

from sqlalchemy.orm import Session

from app.models import Customer, LeadEnrichmentFieldCandidate, ReviewLog
from app.models.enums import ChannelRiskLevel, CustomerGrade, CustomerStatus, OutreachStatus
from app.services.audit_events import Phase3AuditEventService


class Phase3ComplianceGuardService:
    CRITICAL_PROMOTION_FIELDS = {"customer_name", "contacts_json", "contact_methods", "source_evidence", "country", "city"}

    @staticmethod
    def _has_text(value: object) -> bool:
        text = str(value or "").strip()
        return bool(text) and text.lower() != "unknown"

    @classmethod
    def audit_block(
        cls,
        *,
        session: Session | Any | None,
        actor: str | None,
        target_ref: str,
        block_type: str,
        reason: str,
        input_ref: str | None = None,
    ) -> ReviewLog | None:
        if session is None:
            return None
        entity_type, _, entity_id = target_ref.partition(":")
        log = Phase3AuditEventService.record_event(
            session,
            event_name="phase3_compliance_block",
            actor=actor,
            entity_type=entity_type or "unknown",
            entity_id=entity_id or target_ref,
            reason=reason,
            evidence={
                "block_type": block_type,
                "input_ref": input_ref or "",
                "target_ref": target_ref,
            },
        )
        log.input_ref = f"{target_ref};{log.input_ref};block_type={block_type};{input_ref or ''}".strip(";")
        log.result = "blocked"
        log.output_ref = "blocked"
        flush = getattr(session, "flush", None)
        if callable(flush):
            flush()
        return log

    @classmethod
    def block(
        cls,
        *,
        session: Session | Any | None,
        actor: str | None,
        target_ref: str,
        block_type: str,
        reason: str,
        input_ref: str | None = None,
    ) -> None:
        cls.audit_block(
            session=session,
            actor=actor,
            target_ref=target_ref,
            block_type=block_type,
            reason=reason,
            input_ref=input_ref,
        )
        raise ValueError(reason)

    @classmethod
    def ensure_customer_can_receive_outreach(
        cls,
        customer: Customer,
        *,
        session: Session | Any | None = None,
        actor: str | None = None,
        action: str = "outreach",
    ) -> None:
        if bool(getattr(customer, "do_not_contact", False)) or CustomerStatus(getattr(customer, "status")) == CustomerStatus.DO_NOT_CONTACT:
            cls.block(
                session=session,
                actor=actor,
                target_ref=f"customer:{customer.id}",
                block_type="do_not_contact",
                reason="勿扰客户不得生成触达草稿或新增主动触达记录。",
                input_ref=f"action={action};do_not_contact=True",
            )

    @classmethod
    def ensure_source_can_be_promotion_key_evidence(
        cls,
        risk_level: ChannelRiskLevel | str,
        *,
        session: Session | Any | None = None,
        actor: str | None = None,
        target_ref: str = "unknown",
    ) -> None:
        normalized = ChannelRiskLevel(risk_level)
        if normalized == ChannelRiskLevel.FORBIDDEN:
            cls.block(
                session=session,
                actor=actor,
                target_ref=target_ref,
                block_type="forbidden_key_source",
                reason="Forbidden 来源不得作为客户晋级关键来源。",
                input_ref=f"risk_level={normalized.value}",
            )

    @classmethod
    def ensure_c_grade_trade_action_allowed(
        cls,
        customer: Customer,
        *,
        trade_action: str,
        compliance_approved: bool,
        session: Session | Any | None = None,
        actor: str | None = None,
    ) -> None:
        if CustomerGrade(getattr(customer, "grade")) == CustomerGrade.C and not compliance_approved:
            cls.block(
                session=session,
                actor=actor,
                target_ref=f"customer:{customer.id}",
                block_type="c_grade_compliance_review_required",
                reason="C 级客户报价/合同/付款/物流/清关/交付周期动作前必须完成合规复核。",
                input_ref=f"trade_action={trade_action};compliance_approved=False",
            )

    @classmethod
    def ensure_field_candidate_has_evidence(
        cls,
        candidate: LeadEnrichmentFieldCandidate,
        *,
        session: Session | Any | None = None,
        actor: str | None = None,
    ) -> None:
        if str(candidate.field_name) not in cls.CRITICAL_PROMOTION_FIELDS:
            return
        has_source_url = cls._has_text(getattr(candidate, "source_url", None))
        has_evidence_note = cls._has_text(getattr(candidate, "evidence_note", None))
        if not has_source_url and not has_evidence_note:
            cls.block(
                session=session,
                actor=actor,
                target_ref=f"field_candidate:{candidate.id}",
                block_type="missing_field_evidence",
                reason="关键字段缺少来源证据，不得采纳为晋级关键字段。",
                input_ref=f"field_name={candidate.field_name}",
            )

    @classmethod
    def ensure_outreach_is_not_automatic(
        cls,
        status: OutreachStatus | str,
        *,
        manual_confirmed: bool,
        session: Session | Any | None = None,
        actor: str | None = None,
        target_ref: str = "unknown",
    ) -> None:
        normalized = OutreachStatus(status)
        if normalized == OutreachStatus.SENT and not manual_confirmed:
            cls.block(
                session=session,
                actor=actor,
                target_ref=target_ref,
                block_type="automatic_outreach_forbidden",
                reason="已发送必须对应人工确认动作。",
                input_ref="status=sent;manual_confirmed=False",
            )
