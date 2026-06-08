from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.dialects import postgresql

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
from app.services.customers import CustomerWorkbenchFilters, CustomersWorkbenchService


client = TestClient(app)


class FakeScalarResult:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return self.rows


class FakeSession:
    def __init__(self, rows):
        self.rows = rows
        self.statements = []

    def scalars(self, statement):
        self.statements.append(statement)
        return FakeScalarResult(self.rows)


def build_customer(**overrides) -> Customer:
    payload = {
        "id": uuid4(),
        "external_id": f"customer:{uuid4()}",
        "name": "Ru Auto City",
        "normalized_name": "ru auto city",
        "country": "Russia",
        "city": "Moscow",
        "customer_type": CustomerType.LOCAL_DEALER_SECONDARY_DEALER,
        "grade": CustomerGrade.B,
        "status": CustomerStatus.READY_FOR_CUSTOMER_SERVICE,
        "owner": "cs-a",
        "owner_team": "customer_service",
        "do_not_contact": False,
        "missing_fields": "",
        "created_at": datetime(2026, 6, 4, 9, tzinfo=UTC),
        "updated_at": datetime(2026, 6, 4, 10, tzinfo=UTC),
    }
    payload.update(overrides)
    customer = Customer(**payload)
    customer.contact_methods = overrides.get("contact_methods", [])
    customer.sources = overrides.get("sources", [])
    customer.vehicle_intents = overrides.get("vehicle_intents", [])
    customer.outreach_records = overrides.get("outreach_records", [])
    customer.followups = overrides.get("followups", [])
    customer.compliance_reviews = overrides.get("compliance_reviews", [])
    return customer


def contact(customer_id, *, method_type=ContactMethodType.EMAIL, value="sales@example.ru", primary=True):
    return ContactMethod(
        id=uuid4(),
        customer_id=customer_id,
        method_type=method_type,
        value=value,
        label="primary",
        source_url="https://example.ru/contact",
        evidence_note="公开联系页展示联系方式。",
        is_primary=primary,
        is_verified=False,
    )


def source(customer_id, *, risk_level=ChannelRiskLevel.LOW):
    return LeadSource(
        id=uuid4(),
        customer_id=customer_id,
        platform=SourcePlatform.OFFICIAL_WEBSITE,
        source_url="https://example.ru",
        evidence_note="公开官网展示客户来源证据。",
        channel_risk_level=risk_level,
        collected_by="ops-a",
    )


def intent(customer_id, *, brand="Toyota", model="Camry"):
    return CustomerVehicleIntent(
        id=uuid4(),
        customer_id=customer_id,
        brand=brand,
        model=model,
        quantity=2,
        budget_range="15000-25000 USD",
        concerns=["物流", "车况"],
        source_type=CustomerVehicleIntentSourceType.MANUAL_BUSINESS_NOTE,
        status=CustomerVehicleIntentStatus.ACTIVE,
        created_by="sales-a",
    )


def followup(customer_id, *, next_followup_at, next_action="今日电话跟进"):
    return CustomerFollowup(
        id=uuid4(),
        customer_id=customer_id,
        owner_id="cs-a",
        team=CustomerFollowupTeam.CUSTOMER_SERVICE,
        followup_type=CustomerFollowupType.INTERNAL_NOTE,
        content="需要跟进客户反馈。",
        next_action=next_action,
        next_followup_at=next_followup_at,
        created_by="cs-a",
    )


def outreach(customer_id, *, status=OutreachStatus.REPLIED, next_action="交付销售"):
    return OutreachRecord(
        id=uuid4(),
        customer_id=customer_id,
        channel=ContactMethodType.EMAIL,
        status=status,
        response_summary="客户已回复，有采购意向。",
        next_action=next_action,
    )


def compliance(customer_id, *, status=ComplianceReviewStatus.PENDING):
    return ComplianceReview(
        id=uuid4(),
        customer_id=customer_id,
        status=status,
        reason="C级客户报价/合同前必须合规复核。",
    )


def attach_basics(customer: Customer) -> Customer:
    customer.contact_methods = [contact(customer.id)]
    customer.sources = [source(customer.id)]
    customer.vehicle_intents = [intent(customer.id)]
    return customer


def test_customers_route_supports_workbench_filters() -> None:
    openapi = client.get("/openapi.json").json()
    params = {
        param["name"]
        for param in openapi["paths"]["/customers"]["get"]["parameters"]
    }

    assert {"status", "grade", "owner", "country", "city", "limit"}.issubset(params)


def test_workbench_query_filters_status_grade_owner_country_city_and_excludes_watch_invalid() -> None:
    query = CustomersWorkbenchService.build_workbench_query(
        CustomerWorkbenchFilters(
            status=CustomerStatus.READY_FOR_SALES,
            grade=CustomerGrade.C,
            owner="sales-a",
            country="Russia",
            city="Moscow",
            limit=20,
        )
    )

    compiled = str(query.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))
    assert "customers.status = 'ready_for_sales'" in compiled
    assert "customers.grade = 'C'" in compiled
    assert "customers.owner = 'sales-a'" in compiled
    assert "customers.country = 'Russia'" in compiled
    assert "customers.city = 'Moscow'" in compiled
    assert "customers.do_not_contact IS false" in compiled
    assert "Watch" in compiled
    assert "Invalid" in compiled
    assert "LIMIT 20" in compiled


def test_workbench_list_excludes_watch_invalid_and_do_not_contact_customers() -> None:
    visible = attach_basics(build_customer(name="Visible", grade=CustomerGrade.A))
    rows = [
        visible,
        attach_basics(build_customer(name="Watch", grade=CustomerGrade.WATCH, status=CustomerStatus.WATCH)),
        attach_basics(build_customer(name="Invalid", grade=CustomerGrade.INVALID, status=CustomerStatus.INVALID)),
        attach_basics(build_customer(name="DNC", do_not_contact=True, status=CustomerStatus.DO_NOT_CONTACT)),
    ]
    service = CustomersWorkbenchService(FakeSession(rows))

    items = service.list_workbench_customers(CustomerWorkbenchFilters())

    assert [item.name for item in items] == ["Visible"]


def test_workbench_default_order_follows_next_action_priority() -> None:
    now = datetime(2026, 6, 4, 12, tzinfo=UTC)
    first_outreach = attach_basics(build_customer(name="待首次触达", status=CustomerStatus.READY_FOR_CUSTOMER_SERVICE))
    missing_info = build_customer(name="待补全", missing_fields="scale_signal, vehicle_intents")
    missing_info.contact_methods = [contact(missing_info.id)]
    missing_info.sources = [source(missing_info.id)]
    replied = attach_basics(build_customer(name="已回复待销售", status=CustomerStatus.CUSTOMER_SERVICE_FOLLOWING))
    replied.outreach_records = [outreach(replied.id)]
    c_compliance = attach_basics(build_customer(name="C级待合规", grade=CustomerGrade.C, status=CustomerStatus.READY_FOR_SALES))
    c_compliance.compliance_reviews = [compliance(c_compliance.id)]
    today = attach_basics(build_customer(name="今日待跟进", status=CustomerStatus.CUSTOMER_SERVICE_FOLLOWING))
    today.followups = [followup(today.id, next_followup_at=now - timedelta(hours=1))]

    service = CustomersWorkbenchService(FakeSession([first_outreach, missing_info, replied, c_compliance, today]))

    items = service.list_workbench_customers(CustomerWorkbenchFilters(), now=now)

    assert [item.name for item in items] == ["今日待跟进", "C级待合规", "已回复待销售", "待首次触达", "待补全"]
    assert [item.next_action for item in items] == ["今日待跟进", "C级待合规复核", "已回复待销售承接", "待首次触达", "待补全客户信息"]


def test_workbench_item_returns_contact_source_intent_and_next_action_summaries() -> None:
    customer = build_customer(name="Summary Customer", status=CustomerStatus.SALES_FOLLOWING, missing_fields="")
    customer.contact_methods = [
        contact(customer.id, method_type=ContactMethodType.EMAIL, value="sales@example.ru", primary=True),
        contact(customer.id, method_type=ContactMethodType.TELEGRAM, value="@dealer", primary=False),
    ]
    customer.sources = [source(customer.id)]
    customer.vehicle_intents = [intent(customer.id, brand="Toyota", model="Camry")]
    service = CustomersWorkbenchService(FakeSession([customer]))

    item = service.list_workbench_customers(CustomerWorkbenchFilters())[0]

    assert item.contact_summary["total"] == 2
    assert item.contact_summary["primary"] == "email:sales@example.ru"
    assert item.source_completeness["source_count"] == 1
    assert item.source_completeness["has_evidence"] is True
    assert item.vehicle_intent_summary["total"] == 1
    assert item.vehicle_intent_summary["items"][0]["label"] == "Toyota Camry"
    assert item.completeness_score >= 80
    assert item.next_action == "销售跟进中"
