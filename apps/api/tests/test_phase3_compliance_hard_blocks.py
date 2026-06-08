from uuid import uuid4

import pytest

from app.models import Customer, LeadEnrichmentFieldCandidate, ReviewLog
from app.models.enums import (
    ChannelRiskLevel,
    CustomerGrade,
    CustomerStatus,
    CustomerType,
    LeadEnrichmentFieldReviewStatus,
    LeadEnrichmentFieldSourceType,
    OutreachStatus,
    StagingQueueStatus,
    StagingReviewStatus,
)
from app.services.compliance_guards import Phase3ComplianceGuardService
from app.services.outreach_draft import OutreachDraftService
from app.services.staging_leads import StagingLeadService


class FakeSession:
    def __init__(self):
        self.added = []
        self.flushed = False

    def add(self, item):
        self.added.append(item)

    def flush(self):
        self.flushed = True


def build_customer(**overrides) -> Customer:
    payload = {
        "id": uuid4(),
        "external_id": "customer:guard",
        "name": "Guard Customer",
        "normalized_name": "guard customer",
        "country": "Russia",
        "city": "Moscow",
        "customer_type": CustomerType.LOCAL_DEALER_SECONDARY_DEALER,
        "grade": CustomerGrade.B,
        "status": CustomerStatus.READY_FOR_CUSTOMER_SERVICE,
        "do_not_contact": False,
    }
    payload.update(overrides)
    return Customer(**payload)


def build_candidate(**overrides) -> LeadEnrichmentFieldCandidate:
    payload = {
        "id": uuid4(),
        "enrichment_result_id": uuid4(),
        "staging_lead_id": uuid4(),
        "field_name": "contact_methods",
        "candidate_value": [{"type": "email", "value": "sales@example.test"}],
        "source_type": LeadEnrichmentFieldSourceType.AI_PUBLIC_SOURCE,
        "source_url": "",
        "evidence_note": "",
        "confidence_score": 0.8,
        "review_status": LeadEnrichmentFieldReviewStatus.PENDING,
        "accepted_by": None,
        "accepted_at": None,
        "rejected_reason": None,
    }
    payload.update(overrides)
    return LeadEnrichmentFieldCandidate(**payload)


def latest_audit(session: FakeSession) -> ReviewLog:
    return next(item for item in reversed(session.added) if isinstance(item, ReviewLog))


def test_dnc_blocks_outreach_and_records_audit() -> None:
    session = FakeSession()
    customer = build_customer(do_not_contact=True, status=CustomerStatus.DO_NOT_CONTACT)

    with pytest.raises(ValueError, match="勿扰客户不得生成触达草稿或新增主动触达记录"):
        Phase3ComplianceGuardService.ensure_customer_can_receive_outreach(
            customer,
            session=session,
            actor="cs-a",
            action="outreach_record_create",
        )

    audit = latest_audit(session)
    assert audit.action == "phase3_compliance_block"
    assert audit.result == "blocked"
    assert "do_not_contact" in audit.input_ref
    assert audit.reviewer == "cs-a"
    assert session.flushed is True


def test_forbidden_blocks_customer_promotion_key_source_and_records_audit() -> None:
    session = FakeSession()

    with pytest.raises(ValueError, match="Forbidden 来源不得作为客户晋级关键来源"):
        Phase3ComplianceGuardService.ensure_source_can_be_promotion_key_evidence(
            ChannelRiskLevel.FORBIDDEN,
            session=session,
            actor="ops-a",
            target_ref="staging:forbidden",
        )

    audit = latest_audit(session)
    assert "Forbidden" in audit.error_message
    assert "staging:forbidden" in audit.input_ref


def test_c_grade_trade_action_requires_compliance_review_and_records_audit() -> None:
    session = FakeSession()
    customer = build_customer(grade=CustomerGrade.C, status=CustomerStatus.READY_FOR_SALES)

    with pytest.raises(ValueError, match="C 级客户报价/合同/付款/物流/清关/交付周期动作前必须完成合规复核"):
        Phase3ComplianceGuardService.ensure_c_grade_trade_action_allowed(
            customer,
            trade_action="quote",
            compliance_approved=False,
            session=session,
            actor="sales-a",
        )

    audit = latest_audit(session)
    assert "trade_action=quote" in audit.input_ref
    assert "C 级客户" in audit.error_message


def test_critical_field_without_evidence_cannot_be_accepted_and_records_audit() -> None:
    session = FakeSession()
    candidate = build_candidate()

    with pytest.raises(ValueError, match="关键字段缺少来源证据，不得采纳为晋级关键字段"):
        Phase3ComplianceGuardService.ensure_field_candidate_has_evidence(
            candidate,
            session=session,
            actor="ops-a",
        )

    audit = latest_audit(session)
    assert "field_name=contact_methods" in audit.input_ref
    assert "缺少来源证据" in audit.error_message


def test_sent_outreach_requires_manual_confirmation_and_records_audit() -> None:
    session = FakeSession()

    with pytest.raises(ValueError, match="已发送必须对应人工确认动作"):
        Phase3ComplianceGuardService.ensure_outreach_is_not_automatic(
            OutreachStatus.SENT,
            manual_confirmed=False,
            session=session,
            actor="cs-a",
            target_ref="customer:guard",
        )

    audit = latest_audit(session)
    assert "manual_confirmed=False" in audit.input_ref
    assert audit.result == "blocked"


def test_forbidden_source_is_blocked_by_staging_core_gate() -> None:
    gate = StagingLeadService.core_gate_status(
        source_url="https://blocked.example/dealer",
        has_evidence=True,
        source_risk_level=ChannelRiskLevel.FORBIDDEN,
        recommended_grade=CustomerGrade.B,
        review_status=StagingReviewStatus.APPROVED,
        queue_status=StagingQueueStatus.ELIGIBLE,
    )

    assert gate["can_promote_to_core"] is False
    assert "Forbidden 来源不得作为客户晋级关键来源" in gate["reasons"]


def test_outreach_draft_dnc_block_uses_unified_guard_and_records_audit() -> None:
    session = FakeSession()
    customer = build_customer(do_not_contact=True, status=CustomerStatus.DO_NOT_CONTACT)

    payload = OutreachDraftService().get_existing_draft(
        customer_id=customer.id,
        risk_level=ChannelRiskLevel.LOW.value,
        do_not_contact=True,
        session=session,
        actor="cs-a",
    )

    assert payload["can_generate_draft"] is False
    assert "客户已标记勿扰" in payload["block_reasons"]
    audit = latest_audit(session)
    assert audit.action == "phase3_compliance_block"
    assert audit.result == "blocked"
    assert "do_not_contact" in audit.input_ref
    assert audit.reviewer == "cs-a"
