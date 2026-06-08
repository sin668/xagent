from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.models import Customer, CustomerFollowup
from app.models.enums import (
    CustomerFollowupTeam,
    CustomerFollowupType,
    CustomerGrade,
    CustomerStatus,
    CustomerType,
)
from app.schemas.customer_followup import CustomerFollowupCreate
from app.services.customer_followups import CustomerFollowupService


client = TestClient(app)


class FakeScalarResult:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return self.rows


class FakeSession:
    def __init__(self, *, customer=None, rows=None):
        self.customer = customer
        self.rows = rows or []
        self.added = []
        self.flushed = False

    def scalar(self, statement):
        return self.customer

    def scalars(self, statement):
        return FakeScalarResult(self.rows)

    def add(self, item):
        self.added.append(item)

    def flush(self):
        self.flushed = True
        for item in self.added:
            if getattr(item, "id", None) is None:
                item.id = uuid4()


def build_customer(**overrides) -> Customer:
    payload = {
        "id": uuid4(),
        "external_id": "customer:followup",
        "name": "Ru Auto City",
        "normalized_name": "ru auto city",
        "country": "Russia",
        "city": "Moscow",
        "customer_type": CustomerType.LOCAL_DEALER_SECONDARY_DEALER,
        "grade": CustomerGrade.B,
        "status": CustomerStatus.CUSTOMER_SERVICE_FOLLOWING,
        "owner": "cs-a",
        "owner_team": "customer_service",
        "do_not_contact": False,
    }
    payload.update(overrides)
    return Customer(**payload)


def build_followup(customer_id) -> CustomerFollowup:
    return CustomerFollowup(
        id=uuid4(),
        customer_id=customer_id,
        owner_id="cs-a",
        team=CustomerFollowupTeam.CUSTOMER_SERVICE,
        followup_type=CustomerFollowupType.INTERNAL_NOTE,
        content="人工记录客户反馈。",
        customer_feedback="客户关注 Camry。",
        next_action="明天电话确认预算",
        next_followup_at=datetime(2026, 6, 5, 10, tzinfo=UTC),
        triggered_dnc=False,
        triggered_compliance_review=False,
        created_by="cs-a",
        created_at=datetime(2026, 6, 4, 15, tzinfo=UTC),
        updated_at=datetime(2026, 6, 4, 15, tzinfo=UTC),
    )


def create_request(customer_id, **overrides) -> CustomerFollowupCreate:
    payload = {
        "customer_id": customer_id,
        "owner_id": "cs-a",
        "team": CustomerFollowupTeam.CUSTOMER_SERVICE,
        "followup_type": CustomerFollowupType.INTERNAL_NOTE,
        "content": "人工记录客户反馈。",
        "customer_feedback": "客户关注 Camry。",
        "next_action": "明天电话确认预算",
        "next_followup_at": datetime(2026, 6, 5, 10, tzinfo=UTC),
        "created_by": "cs-a",
    }
    payload.update(overrides)
    return CustomerFollowupCreate(**payload)


def test_customer_followup_routes_are_registered_without_auto_send() -> None:
    openapi = client.get("/openapi.json").json()
    paths = openapi["paths"]

    assert "/customers/{customer_id}/followups" in paths
    assert "get" in paths["/customers/{customer_id}/followups"]
    assert "post" in paths["/customers/{customer_id}/followups"]
    api_text = (Path(__file__).resolve().parents[1] / "app" / "api" / "customer_followups.py").read_text(encoding="utf-8")
    assert "auto_send" not in api_text
    assert "send_message" not in api_text


def test_list_customer_followups_returns_customer_scoped_rows() -> None:
    customer = build_customer()
    followup = build_followup(customer.id)
    service = CustomerFollowupService(FakeSession(customer=customer, rows=[followup]))

    rows = service.list_for_customer(customer.id)

    assert rows == [followup]


def test_create_customer_followup_records_required_fields_without_sending_message() -> None:
    customer = build_customer()
    session = FakeSession(customer=customer)
    service = CustomerFollowupService(session)

    followup = service.create_for_customer(
        customer.id,
        request=create_request(customer.id),
        now=datetime(2026, 6, 4, 16, tzinfo=UTC),
    )

    assert followup.owner_id == "cs-a"
    assert followup.team == CustomerFollowupTeam.CUSTOMER_SERVICE
    assert followup.followup_type == CustomerFollowupType.INTERNAL_NOTE
    assert followup.content == "人工记录客户反馈。"
    assert followup.customer_feedback == "客户关注 Camry。"
    assert followup.next_action == "明天电话确认预算"
    assert followup.next_followup_at == datetime(2026, 6, 5, 10, tzinfo=UTC)
    assert session.flushed is True
    assert not hasattr(followup, "sent_at")
    assert customer.do_not_contact is False


def test_followup_triggered_dnc_marks_customer_and_blocks_future_active_followups() -> None:
    customer = build_customer()
    session = FakeSession(customer=customer)
    service = CustomerFollowupService(session)

    followup = service.create_for_customer(
        customer.id,
        request=create_request(
            customer.id,
            triggered_dnc=True,
            customer_feedback="客户明确拒绝后续联系。",
            next_action="标记勿扰",
        ),
        now=datetime(2026, 6, 4, 16, tzinfo=UTC),
    )

    assert followup.triggered_dnc is True
    assert customer.do_not_contact is True
    assert customer.status == CustomerStatus.DO_NOT_CONTACT
    assert customer.do_not_contact_reason == "客户明确拒绝后续联系。"

    try:
        service.create_for_customer(customer.id, request=create_request(customer.id), now=datetime(2026, 6, 4, 17, tzinfo=UTC))
    except ValueError as exc:
        assert "勿扰客户" in str(exc)
    else:
        raise AssertionError("勿扰客户不得继续新增主动跟进")


def test_create_blocks_customer_id_mismatch() -> None:
    customer = build_customer()
    service = CustomerFollowupService(FakeSession(customer=customer))

    try:
        service.create_for_customer(uuid4(), request=create_request(customer.id), now=datetime(2026, 6, 4, 16, tzinfo=UTC))
    except ValueError as exc:
        assert "customer_id" in str(exc)
    else:
        raise AssertionError("路径 customer_id 与请求 customer_id 不一致时必须拒绝")
