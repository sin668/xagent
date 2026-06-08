from datetime import UTC, datetime
from uuid import uuid4

from app.models import Customer, ReviewLog
from app.models.candidate_url import CandidateUrl
from app.models.enums import (
    ChannelRiskLevel,
    CustomerGrade,
    CustomerStatus,
    CustomerType,
    LeadEnrichmentFieldReviewStatus,
    LeadEnrichmentFieldSourceType,
)
from app.models.lead_enrichment_field_candidate import LeadEnrichmentFieldCandidate
from app.models.staging_lead import StagingLead
from app.schemas.lead_enrichment import LeadEnrichmentRunCreate
from app.schemas.lead_enrichment_field_candidate import LeadEnrichmentFieldCandidateAccept, LeadEnrichmentFieldCandidateReject
from app.services.audit_events import Phase3AuditEventService
from app.services.customer_dnc import CustomerDncService
from app.services.lead_enrichment import LeadEnrichmentService


class FakeSession:
    def __init__(self, scalar_result=None):
        self.added = []
        self.flushed = False
        self.scalar_result = scalar_result

    def add(self, item):
        self.added.append(item)

    def add_all(self, items):
        self.added.extend(items)

    def flush(self):
        self.flushed = True

    def scalar(self, statement):
        return self.scalar_result

    def execute(self, statement):
        return FakeExecuteResult()


class FakeExecuteResult:
    def scalar_one(self):
        return 0

    def scalar_one_or_none(self):
        return None


def latest_review_log(session: FakeSession, action: str) -> ReviewLog:
    return next(item for item in reversed(session.added) if isinstance(item, ReviewLog) and item.action == action)


def build_staging_lead() -> StagingLead:
    lead = StagingLead(
        id=uuid4(),
        candidate_url_id=uuid4(),
        customer_name="Ru Auto City",
        country="Russia",
        city="Moscow",
        contacts_json=[{"type": "email", "value": "sales@example.com"}],
        source_evidence="公开官网展示车商名称和联系方式。",
        recommended_grade=CustomerGrade.B,
        review_status="pending_review",
        queue_status="pending_review",
        missing_fields=["vehicle_intents"],
        requires_compliance_review=False,
    )
    lead.candidate_url = CandidateUrl(
        id=lead.candidate_url_id,
        task_id=uuid4(),
        url="https://dealer.example/contact",
        url_hash="hash",
        source_platform="official_website",
        source_risk_level=ChannelRiskLevel.LOW,
        source_usage_type="automatic_collection",
        discovery_reason="公开官网。",
        queue_eligible=True,
        requires_secondary_verification=False,
        status="new",
    )
    return lead


def build_field_candidate(**overrides) -> LeadEnrichmentFieldCandidate:
    payload = {
        "id": uuid4(),
        "enrichment_result_id": uuid4(),
        "staging_lead_id": uuid4(),
        "field_name": "contacts_json",
        "candidate_value": [{"type": "email", "value": "sales@example.com"}],
        "source_type": LeadEnrichmentFieldSourceType.AI_PUBLIC_SOURCE,
        "source_url": "https://dealer.example/contact",
        "evidence_note": "公开联系页展示邮箱。",
        "confidence_score": 0.86,
        "review_status": LeadEnrichmentFieldReviewStatus.PENDING,
        "accepted_by": None,
        "accepted_at": None,
        "rejected_reason": None,
    }
    payload.update(overrides)
    return LeadEnrichmentFieldCandidate(**payload)


def build_customer(**overrides) -> Customer:
    payload = {
        "id": uuid4(),
        "external_id": "customer:audit",
        "name": "Ru Auto City",
        "normalized_name": "ru auto city",
        "country": "Russia",
        "city": "Moscow",
        "customer_type": CustomerType.LOCAL_DEALER_SECONDARY_DEALER,
        "grade": CustomerGrade.B,
        "status": CustomerStatus.READY_FOR_CUSTOMER_SERVICE,
        "do_not_contact": False,
    }
    payload.update(overrides)
    return Customer(**payload)


def test_phase3_audit_event_service_records_required_context() -> None:
    session = FakeSession()
    entity_id = uuid4()
    occurred_at = datetime(2026, 6, 4, 15, 30, tzinfo=UTC)

    log = Phase3AuditEventService.record_event(
        session,
        event_name="lead_enrichment_field_accepted",
        actor="ops-a",
        entity_type="lead_enrichment_field_candidate",
        entity_id=entity_id,
        reason="公开官网证据充分。",
        evidence={"source_url": "https://dealer.example", "field_name": "contact_methods"},
        occurred_at=occurred_at,
    )

    assert isinstance(log, ReviewLog)
    assert log.action == "lead_enrichment_field_accepted"
    assert log.reviewer == "ops-a"
    assert log.task_id == str(entity_id)
    assert log.agent_name == "phase3-audit-event"
    assert log.result == "recorded"
    assert "entity_type=lead_enrichment_field_candidate" in log.input_ref
    assert "occurred_at=2026-06-04T15:30:00+00:00" in log.input_ref
    assert "source_url=https://dealer.example" in log.output_ref
    assert log.error_message == "公开官网证据充分。"
    assert session.added == [log]
    assert session.flushed is True


def test_phase3_audit_event_service_covers_frozen_story_events() -> None:
    required_events = {
        "lead_deep_enrichment_started",
        "lead_enrichment_field_accepted",
        "lead_enrichment_field_rejected",
        "lead_promoted_to_customer",
        "lead_cleanup_suggestion_created",
        "lead_cleanup_suggestion_approved",
        "lead_cleanup_suggestion_executed",
        "customer_assigned",
        "customer_do_not_contact_marked",
    }

    assert required_events.issubset(Phase3AuditEventService.SUPPORTED_EVENTS)


def test_phase3_audit_event_service_rejects_unknown_event_name() -> None:
    session = FakeSession()

    try:
        Phase3AuditEventService.record_event(
            session,
            event_name="auto_social_message_sent",
            actor="agent",
            entity_type="customer",
            entity_id=uuid4(),
            reason="不允许的自动触达事件。",
            evidence={},
        )
    except ValueError as exc:
        assert "不支持的第三阶段审计事件" in str(exc)
    else:
        raise AssertionError("未知事件不得写入第三阶段审计")


def test_create_pending_deep_enrichment_run_records_unified_started_event() -> None:
    session = FakeSession()
    service = LeadEnrichmentService(session)
    lead = build_staging_lead()
    request = LeadEnrichmentRunCreate(
        triggered_by="ops-a",
        manual_keywords=["Toyota"],
        allowed_channel_scope=["official_website"],
        note="人工触发深挖。",
    )

    run, quota = service.create_pending_run(
        lead,
        request=request,
        daily_limit=3,
        now=datetime(2026, 6, 4, 16, tzinfo=UTC),
    )

    assert quota.used_today == 1
    audit = latest_review_log(session, "lead_deep_enrichment_started")
    assert audit.task_id == str(run.id)
    assert audit.reviewer == "ops-a"
    assert "entity_type=lead_enrichment_result" in audit.input_ref
    assert "occurred_at=2026-06-04T16:00:00+00:00" in audit.input_ref
    assert "source_url=https://dealer.example/contact" in audit.output_ref
    assert audit.error_message == "人工触发深挖。"


def test_field_candidate_accept_and_reject_record_unified_audit_events() -> None:
    session = FakeSession()
    service = LeadEnrichmentService(session)
    accepted_candidate = build_field_candidate()
    rejected_candidate = build_field_candidate(field_name="vehicle_intents")

    service.accept_field_candidate_with_audit(
        accepted_candidate,
        request=LeadEnrichmentFieldCandidateAccept(accepted_by="reviewer-a"),
        now=datetime(2026, 6, 4, 17, tzinfo=UTC),
    )
    service.reject_field_candidate_with_audit(
        rejected_candidate,
        request=LeadEnrichmentFieldCandidateReject(rejected_reason="证据不足。"),
        now=datetime(2026, 6, 4, 17, 30, tzinfo=UTC),
    )

    accepted_audit = latest_review_log(session, "lead_enrichment_field_accepted")
    assert accepted_audit.task_id == str(accepted_candidate.id)
    assert accepted_audit.reviewer == "reviewer-a"
    assert "field_name=contacts_json" in accepted_audit.output_ref
    assert "source_url=https://dealer.example/contact" in accepted_audit.output_ref

    rejected_audit = latest_review_log(session, "lead_enrichment_field_rejected")
    assert rejected_audit.task_id == str(rejected_candidate.id)
    assert rejected_audit.reviewer is None
    assert rejected_audit.error_message == "证据不足。"
    assert "field_name=vehicle_intents" in rejected_audit.output_ref


def test_mark_do_not_contact_records_unified_audit_event() -> None:
    customer = build_customer()
    session = FakeSession(scalar_result=customer)
    service = CustomerDncService(session)

    service.mark_do_not_contact(
        customer_id=customer.id,
        marked_by="cs-a",
        reason="客户明确拒绝继续联系。",
    )

    audit = latest_review_log(session, "customer_do_not_contact_marked")
    assert audit.task_id == str(customer.id)
    assert audit.reviewer == "cs-a"
    assert "entity_type=customer" in audit.input_ref
    assert "status=do_not_contact" in audit.output_ref
    assert audit.error_message == "客户明确拒绝继续联系。"
