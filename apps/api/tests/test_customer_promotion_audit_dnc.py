from types import SimpleNamespace
from uuid import uuid4

from sqlalchemy import select

from app.models import ContactMethod, Customer, ReviewLog
from app.models.enums import (
    ChannelRiskLevel,
    CustomerGrade,
    CustomerType,
    SourcePlatform,
    StagingQueueStatus,
    StagingReviewStatus,
)
from app.schemas.customer_promotion import PromoteStagingLeadToCustomerRequest
from app.services.customer_promotion import CustomerPromotionService


class CapturingSession:
    def __init__(self, scalar_results=None):
        self.scalar_results = list(scalar_results or [])
        self.scalars_called = []

    def scalar(self, statement):
        self.scalars_called.append(statement)
        return self.scalar_results.pop(0) if self.scalar_results else None


def build_lead(**overrides):
    candidate = overrides.pop(
        "candidate_url",
        SimpleNamespace(
            id=uuid4(),
            url="https://dealer.example.ru",
            source_platform=SourcePlatform.OFFICIAL_WEBSITE,
            source_risk_level=ChannelRiskLevel.LOW,
        ),
    )
    payload = {
        "id": uuid4(),
        "candidate_url": candidate,
        "customer_name": "Auto City Moscow",
        "country": "Russia",
        "city": "Moscow",
        "customer_type": CustomerType.LOCAL_DEALER_SECONDARY_DEALER,
        "contacts_json": [
            {"type": "email", "value": "SALES@DEALER.EXAMPLE.RU", "usage": "公开邮箱"},
            {"type": "telegram", "value": "@dealer_ru", "usage": "公开 Telegram"},
        ],
        "activity_level": "active",
        "scale_signal": "公开页面展示多台库存。",
        "import_used_car_relevance": "high",
        "source_evidence": "官网公开展示车辆销售、库存和联系方式。",
        "recommended_grade": CustomerGrade.B,
        "recommended_reason": "满足平衡准入。",
        "missing_fields": ["vehicle_intents"],
        "review_status": StagingReviewStatus.PENDING_REVIEW,
        "queue_status": StagingQueueStatus.PENDING_REVIEW,
        "requires_compliance_review": False,
    }
    payload.update(overrides)
    return SimpleNamespace(**payload)


def build_request(**overrides):
    payload = {
        "actor": "ops-a",
        "review_note": "人工确认来源、联系方式和勿扰校验。",
        "accepted_fields_json": {
            "customer_name": {"source": "accepted_field_candidate", "candidate_id": "fc-name"},
            "contacts_json": {"source": "manual_public_info", "candidate_id": "fc-contact"},
            "source_evidence": {"source": "staging_lead"},
        },
    }
    payload.update(overrides)
    return PromoteStagingLeadToCustomerRequest(**payload)


def test_promotion_audit_payload_records_required_reviewer_note_fields_and_event() -> None:
    lead = build_lead()
    request = build_request()

    payloads = CustomerPromotionService.build_promotion_payloads(
        lead,
        request=request,
        has_do_not_contact_match=False,
    )

    assert payloads.review_log["action"] == "lead_promoted_to_customer"
    assert payloads.review_log["reviewer"] == "ops-a"
    assert payloads.review_log["error_message"] == "人工确认来源、联系方式和勿扰校验。"
    assert f"staging:{lead.id}" in payloads.review_log["input_ref"]
    assert "accepted_fields_json=" in payloads.review_log["input_ref"]
    assert "fc-name" in payloads.review_log["input_ref"]
    assert "fc-contact" in payloads.review_log["input_ref"]
    assert payloads.review_log["output_ref"] == f"customer_external_id:staging:{lead.id}"
    assert payloads.review_log["result"] == "approved"


def test_do_not_contact_match_blocks_manual_promotion_even_with_accepted_fields() -> None:
    lead = build_lead()
    request = build_request(
        accepted_fields_json={
            "customer_name": {"source": "manual_public_info"},
            "contacts_json": {"source": "manual_public_info"},
            "source_evidence": {"source": "manual_public_info"},
        },
    )

    try:
        CustomerPromotionService.build_promotion_payloads(
            lead,
            request=request,
            has_do_not_contact_match=True,
        )
    except ValueError as exc:
        assert "命中勿扰客户" in str(exc)
    else:
        raise AssertionError("勿扰命中线索不得通过手动准入晋级客户")


def test_do_not_contact_lookup_matches_existing_customer_name_case_insensitively() -> None:
    lead = build_lead(customer_name="Auto City Moscow")
    customer_id = uuid4()
    session = CapturingSession(scalar_results=[customer_id])
    service = CustomerPromotionService(session)

    assert service.find_do_not_contact_customer_id(lead) == customer_id
    session = CapturingSession(scalar_results=[customer_id])
    service = CustomerPromotionService(session)
    assert service.has_do_not_contact_match(lead) is True

    compiled = str(session.scalars_called[0].compile(compile_kwargs={"literal_binds": True}))
    assert "lower(customers.name)" in compiled
    assert "auto city moscow" in compiled


def test_do_not_contact_lookup_matches_contact_method_value_case_insensitively() -> None:
    lead = build_lead(customer_name="Different Dealer")
    customer_id = uuid4()
    session = CapturingSession(scalar_results=[None, customer_id])
    service = CustomerPromotionService(session)

    assert service.find_do_not_contact_customer_id(lead) == customer_id
    session = CapturingSession(scalar_results=[None, customer_id])
    service = CustomerPromotionService(session)
    assert service.has_do_not_contact_match(lead) is True

    compiled = str(session.scalars_called[1].compile(compile_kwargs={"literal_binds": True}))
    assert "lower(contact_methods.value)" in compiled
    assert "sales@dealer.example.ru" in compiled


def test_do_not_contact_lookup_targets_only_customers_marked_do_not_contact() -> None:
    lead = build_lead()
    session = CapturingSession(scalar_results=[None, None])
    service = CustomerPromotionService(session)

    assert service.find_do_not_contact_customer_id(lead) is None
    session = CapturingSession(scalar_results=[None, None])
    service = CustomerPromotionService(session)
    assert service.has_do_not_contact_match(lead) is False

    name_statement = str(session.scalars_called[0])
    contact_statement = str(session.scalars_called[1])
    assert "customers.do_not_contact IS true" in name_statement
    assert "customers.do_not_contact IS true" in contact_statement


def test_promotion_audit_event_name_is_queryable_from_review_log_contract() -> None:
    statement = select(ReviewLog.id).where(
        ReviewLog.action == "lead_promoted_to_customer",
        ReviewLog.reviewer == "ops-a",
    )

    compiled = str(statement.compile(compile_kwargs={"literal_binds": True}))
    assert "review_logs" in compiled
    assert "lead_promoted_to_customer" in compiled
    assert "ops-a" in compiled
