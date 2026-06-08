from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import app
from app.models.enums import (
    ChannelRiskLevel,
    ContactMethodType,
    CustomerGrade,
    CustomerStatus,
    CustomerType,
    SourcePlatform,
    StagingQueueStatus,
    StagingReviewStatus,
)
from app.schemas.customer_promotion import PromoteStagingLeadToCustomerRequest, PromoteStagingLeadToCustomerResponse
from app.services.customer_promotion import CustomerPromotionService


client = TestClient(app)


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
            {"type": "email", "value": "sales@dealer.example.ru", "usage": "公开邮箱"},
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


def test_promote_to_customer_route_is_registered_without_auto_trigger() -> None:
    openapi = client.get("/openapi.json").json()
    paths = openapi["paths"]

    assert "/staging-leads/{lead_id}/promote-to-customer" in paths
    assert "post" in paths["/staging-leads/{lead_id}/promote-to-customer"]
    assert "delete" not in paths["/staging-leads/{lead_id}/promote-to-customer"]


def test_promote_request_requires_actor_and_accepted_fields_audit() -> None:
    try:
        PromoteStagingLeadToCustomerRequest(actor="", accepted_fields_json={})
    except ValidationError as exc:
        assert "actor" in str(exc)
        assert "accepted_fields_json" in str(exc)
    else:
        raise AssertionError("manual promotion should require actor and accepted_fields_json")


def test_build_promotion_payloads_writes_customer_source_contacts_and_audit() -> None:
    lead = build_lead()
    request = PromoteStagingLeadToCustomerRequest(
        actor="ops-a",
        review_note="人工确认满足平衡准入。",
        accepted_fields_json={
            "customer_name": {"source": "accepted_field_candidate", "candidate_id": "fc-1"},
            "contacts_json": {"source": "manual_public_info", "candidate_id": "fc-2"},
            "source_evidence": {"source": "staging_lead"},
        },
    )

    payloads = CustomerPromotionService.build_promotion_payloads(
        lead,
        request=request,
        has_do_not_contact_match=False,
    )

    assert payloads.eligibility.can_promote is True
    assert payloads.customer["external_id"] == f"staging:{lead.id}"
    assert payloads.customer["name"] == "Auto City Moscow"
    assert payloads.customer["status"] == CustomerStatus.READY_FOR_CUSTOMER_SERVICE
    assert payloads.customer["grade"] == CustomerGrade.B
    assert payloads.customer["missing_fields"] == "vehicle_intents"
    assert payloads.lead_source["external_id"] == f"staging:{lead.id}"
    assert payloads.lead_source["source_url"] == "https://dealer.example.ru"
    assert payloads.lead_source["evidence_note"] == "官网公开展示车辆销售、库存和联系方式。"
    assert payloads.contact_methods[0]["method_type"] == ContactMethodType.EMAIL
    assert payloads.contact_methods[0]["value"] == "sales@dealer.example.ru"
    assert payloads.contact_methods[1]["method_type"] == ContactMethodType.TELEGRAM
    assert payloads.review_log["action"] == "lead_promoted_to_customer"
    assert payloads.review_log["reviewer"] == "ops-a"
    assert "accepted_fields_json" in payloads.review_log["input_ref"]
    assert "fc-1" in payloads.review_log["input_ref"]


def test_build_promotion_payloads_is_idempotent_by_external_id_and_contact_key() -> None:
    lead = build_lead()
    request = PromoteStagingLeadToCustomerRequest(
        actor="ops-a",
        accepted_fields_json={"customer_name": {"source": "accepted_field_candidate"}},
    )

    payloads = CustomerPromotionService.build_promotion_payloads(
        lead,
        request=request,
        has_do_not_contact_match=False,
    )

    assert payloads.customer["external_id"] == f"staging:{lead.id}"
    assert payloads.lead_source["external_id"] == f"staging:{lead.id}"
    assert payloads.contact_methods[0]["dedupe_key"] == ("email", "sales@dealer.example.ru")
    assert payloads.contact_methods[1]["dedupe_key"] == ("telegram", "@dealer_ru")


def test_build_promotion_payloads_blocks_ineligible_lead() -> None:
    lead = build_lead(
        recommended_grade=CustomerGrade.WATCH,
        queue_status=StagingQueueStatus.NOT_ELIGIBLE,
        candidate_url=SimpleNamespace(
            id=uuid4(),
            url="https://blocked.example",
            source_platform=SourcePlatform.OFFICIAL_WEBSITE,
            source_risk_level=ChannelRiskLevel.FORBIDDEN,
        ),
    )
    request = PromoteStagingLeadToCustomerRequest(
        actor="ops-a",
        accepted_fields_json={"customer_name": {"source": "accepted_field_candidate"}},
    )

    try:
        CustomerPromotionService.build_promotion_payloads(lead, request=request, has_do_not_contact_match=False)
    except ValueError as exc:
        assert "Forbidden 来源不得作为客户晋级关键来源" in str(exc)
        assert "Watch 不得晋级客户或进入触达队列" in str(exc)
    else:
        raise AssertionError("ineligible lead should not be promoted")


def test_promote_response_schema_exposes_idempotent_core_ids_and_audit() -> None:
    response = PromoteStagingLeadToCustomerResponse(
        staging_lead_id=uuid4(),
        customer_id=uuid4(),
        customer_external_id="staging:lead-1",
        lead_source_id=uuid4(),
        contact_method_ids=[uuid4()],
        customer_status=CustomerStatus.READY_FOR_CUSTOMER_SERVICE,
        do_not_contact=False,
        requires_compliance_review=False,
        compliance_review_id=None,
        review_log_id=uuid4(),
    )

    assert response.customer_external_id == "staging:lead-1"
    assert len(response.contact_method_ids) == 1
