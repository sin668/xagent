from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.models import ComplianceReview, ContactMethod, Customer, CustomerFollowup, CustomerVehicleIntent, LeadSource, OutreachRecord
from app.models.enums import (
    ChannelRiskLevel,
    ComplianceReviewStatus,
    ContactMethodType,
    CustomerFollowupTeam,
    CustomerFollowupType,
    CustomerGrade,
    CustomerStatus,
    CustomerType,
    CustomerVehicleIntentSourceType,
    CustomerVehicleIntentStatus,
    OutreachStatus,
    SourcePlatform,
)
from app.schemas.customer import CustomerDetailResponse
from app.services.customers import CustomersWorkbenchService


client = TestClient(app)


class FakeSession:
    def __init__(self, customer=None):
        self.customer = customer
        self.statements = []

    def scalar(self, statement):
        self.statements.append(statement)
        return self.customer


def build_customer(**overrides) -> Customer:
    payload = {
        "id": uuid4(),
        "external_id": "customer:detail",
        "name": "Ru Auto City",
        "normalized_name": "ru auto city",
        "country": "Russia",
        "city": "Moscow",
        "customer_type": CustomerType.LOCAL_DEALER_SECONDARY_DEALER,
        "grade": CustomerGrade.C,
        "status": CustomerStatus.READY_FOR_SALES,
        "owner": "sales-a",
        "owner_team": "sales",
        "do_not_contact": False,
        "ai_recommended_grade": CustomerGrade.C,
        "ai_recommendation_reason": "有公开联系方式，需合规复核。",
        "missing_fields": "scale_signal, purchase_frequency",
        "created_at": datetime(2026, 6, 4, 9, tzinfo=UTC),
        "updated_at": datetime(2026, 6, 4, 10, tzinfo=UTC),
    }
    payload.update(overrides)
    customer = Customer(**payload)
    customer.contact_methods = []
    customer.sources = []
    customer.vehicle_intents = []
    customer.outreach_records = []
    customer.followups = []
    customer.compliance_reviews = []
    return customer


def attach_detail_relations(customer: Customer) -> Customer:
    customer.contact_methods = [
        ContactMethod(
            id=uuid4(),
            customer_id=customer.id,
            method_type=ContactMethodType.EMAIL,
            value="sales@example.ru",
            label="main",
            source_url="https://example.ru/contact",
            evidence_note="公开联系页展示邮箱。",
            is_primary=True,
            is_verified=False,
        )
    ]
    customer.sources = [
        LeadSource(
            id=uuid4(),
            customer_id=customer.id,
            platform=SourcePlatform.OFFICIAL_WEBSITE,
            source_url="https://example.ru",
            source_title="Ru Auto City",
            evidence_note="公开官网展示公司名称和库存。",
            evidence_excerpt="Used cars import from China.",
            channel_risk_level=ChannelRiskLevel.LOW,
            collected_by="ops-a",
        )
    ]
    customer.vehicle_intents = [
        CustomerVehicleIntent(
            id=uuid4(),
            customer_id=customer.id,
            brand="Toyota",
            model="Camry",
            year_range="2020-2023",
            quantity=3,
            budget_range="15000-25000 USD",
            concerns=["物流", "车况"],
            source_type=CustomerVehicleIntentSourceType.MANUAL_BUSINESS_NOTE,
            source_note="销售记录客户关注 Camry。",
            status=CustomerVehicleIntentStatus.ACTIVE,
            created_by="sales-a",
            created_at=datetime(2026, 6, 4, 11, tzinfo=UTC),
        )
    ]
    customer.outreach_records = [
        OutreachRecord(
            id=uuid4(),
            customer_id=customer.id,
            channel=ContactMethodType.EMAIL,
            status=OutreachStatus.REPLIED,
            sent_by="cs-a",
            owner="cs-a",
            response_summary="客户回复关注 Toyota Camry。",
            next_action="交付销售跟进",
            sent_at=datetime(2026, 6, 4, 12, tzinfo=UTC),
            created_at=datetime(2026, 6, 4, 12, tzinfo=UTC),
        )
    ]
    customer.followups = [
        CustomerFollowup(
            id=uuid4(),
            customer_id=customer.id,
            owner_id="sales-a",
            team=CustomerFollowupTeam.SALES,
            followup_type=CustomerFollowupType.INTERNAL_NOTE,
            content="销售准备确认预算和交付地。",
            customer_feedback="需要 Camry 报价范围。",
            next_action="确认预算",
            next_followup_at=datetime(2026, 6, 4, 16, tzinfo=UTC),
            triggered_compliance_review=True,
            created_by="sales-a",
            created_at=datetime(2026, 6, 4, 13, tzinfo=UTC),
        )
    ]
    customer.compliance_reviews = [
        ComplianceReview(
            id=uuid4(),
            customer_id=customer.id,
            status=ComplianceReviewStatus.PENDING,
            reason="C级客户报价/合同前必须合规复核。",
            risk_note="待复核付款、物流、清关。",
            created_at=datetime(2026, 6, 4, 14, tzinfo=UTC),
        )
    ]
    return customer


def test_customer_detail_route_uses_full_detail_response_schema() -> None:
    openapi = client.get("/openapi.json").json()

    assert "/customers/{customer_id}" in openapi["paths"]
    assert openapi["paths"]["/customers/{customer_id}"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith(
        "CustomerDetailResponse"
    )


def test_customer_detail_aggregates_profile_contacts_sources_intents_outreach_followups_and_compliance() -> None:
    customer = attach_detail_relations(build_customer())
    service = CustomersWorkbenchService(FakeSession(customer))

    detail = service.get_customer_detail(customer.id, now=datetime(2026, 6, 4, 15, tzinfo=UTC))

    assert isinstance(detail, CustomerDetailResponse)
    assert detail.profile["name"] == "Ru Auto City"
    assert detail.profile["grade"] == "C"
    assert detail.pending_fields == ["scale_signal", "purchase_frequency"]
    assert detail.do_not_contact["enabled"] is False
    assert detail.compliance_status["requires_review"] is True
    assert detail.compliance_status["latest_status"] == "pending"
    assert detail.contacts[0]["value"] == "sales@example.ru"
    assert detail.sources[0]["source_url"] == "https://example.ru"
    assert detail.sources[0]["evidence_note"] == "公开官网展示公司名称和库存。"
    assert detail.vehicle_intents[0]["label"] == "Toyota Camry"
    assert detail.outreach_history[0]["status"] == "replied"
    assert detail.followups[0]["next_action"] == "确认预算"
    assert detail.next_action == "今日待跟进"
    assert detail.source_traceability["lead_sources_count"] == 1
    assert detail.source_traceability["has_enrichment_evidence"] is True


def test_customer_detail_marks_do_not_contact_and_blocks_next_outreach_action() -> None:
    customer = attach_detail_relations(
        build_customer(
            do_not_contact=True,
            status=CustomerStatus.DO_NOT_CONTACT,
            do_not_contact_reason="客户拒绝继续联系。",
            do_not_contact_marked_by="cs-a",
            do_not_contact_marked_at=datetime(2026, 6, 4, 12, tzinfo=UTC),
        )
    )
    service = CustomersWorkbenchService(FakeSession(customer))

    detail = service.get_customer_detail(customer.id, now=datetime(2026, 6, 4, 15, tzinfo=UTC))

    assert detail.do_not_contact["enabled"] is True
    assert detail.do_not_contact["reason"] == "客户拒绝继续联系。"
    assert detail.next_action == "勿扰客户，不得触达"


def test_customer_detail_reports_missing_customer_for_404_mapping() -> None:
    service = CustomersWorkbenchService(FakeSession(None))

    try:
        service.get_customer_detail(uuid4(), now=datetime(2026, 6, 4, 15, tzinfo=UTC))
    except ValueError as exc:
        assert "客户不存在" in str(exc)
    else:
        raise AssertionError("missing customer should raise ValueError")
