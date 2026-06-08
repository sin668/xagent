from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.models import Customer, CustomerVehicleIntent
from app.models.enums import (
    CustomerGrade,
    CustomerStatus,
    CustomerType,
    CustomerVehicleIntentSourceType,
    CustomerVehicleIntentStatus,
)
from app.schemas.customer_vehicle_intent import CustomerVehicleIntentCreate, CustomerVehicleIntentUpdate
from app.services.customer_vehicle_intents import CustomerVehicleIntentService


client = TestClient(app)


class FakeScalarResult:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return self.rows


class FakeSession:
    def __init__(self, *, customer=None, intent=None, rows=None):
        self.customer = customer
        self.intent = intent
        self.rows = rows or []
        self.added = []
        self.flushed = False
        self.scalar_calls = 0

    def scalar(self, statement):
        self.scalar_calls += 1
        text = str(statement)
        if "customer_vehicle_intents" in text:
            return self.intent
        if "customers" in text:
            return self.customer
        return None

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
        "external_id": "customer:intent",
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
        "created_at": datetime(2026, 6, 4, 9, tzinfo=UTC),
        "updated_at": datetime(2026, 6, 4, 10, tzinfo=UTC),
    }
    payload.update(overrides)
    return Customer(**payload)


def build_intent(customer_id, **overrides) -> CustomerVehicleIntent:
    payload = {
        "id": uuid4(),
        "customer_id": customer_id,
        "brand": "Toyota",
        "model": "Camry",
        "year_range": "2020-2023",
        "vehicle_age": None,
        "quantity": 2,
        "budget_range": "15000-25000 USD",
        "purchase_frequency": "monthly",
        "delivery_country": "Russia",
        "delivery_city": "Moscow",
        "concerns": ["物流", "车况"],
        "source_type": CustomerVehicleIntentSourceType.MANUAL_BUSINESS_NOTE,
        "source_note": "销售记录客户关注 Camry。",
        "status": CustomerVehicleIntentStatus.ACTIVE,
        "created_by": "sales-a",
        "created_at": datetime(2026, 6, 4, 11, tzinfo=UTC),
        "updated_at": datetime(2026, 6, 4, 11, tzinfo=UTC),
    }
    payload.update(overrides)
    return CustomerVehicleIntent(**payload)


def create_payload(customer_id) -> CustomerVehicleIntentCreate:
    return CustomerVehicleIntentCreate(
        customer_id=customer_id,
        brand="Toyota",
        model="Camry",
        quantity=2,
        budget_range="15000-25000 USD",
        concerns=["物流", "车况"],
        source_type=CustomerVehicleIntentSourceType.MANUAL_BUSINESS_NOTE,
        source_note="销售记录客户关注 Camry。",
        created_by="sales-a",
    )


def test_customer_vehicle_intent_routes_are_registered_without_quote_or_contract_endpoints() -> None:
    openapi = client.get("/openapi.json").json()
    paths = openapi["paths"]

    assert "/customers/{customer_id}/vehicle-intents" in paths
    assert "get" in paths["/customers/{customer_id}/vehicle-intents"]
    assert "post" in paths["/customers/{customer_id}/vehicle-intents"]
    assert "/customer-vehicle-intents/{intent_id}" in paths
    assert "patch" in paths["/customer-vehicle-intents/{intent_id}"]
    intent_paths = [path for path in paths if "vehicle-intents" in path]
    assert all("quote" not in path.lower() and "contract" not in path.lower() for path in intent_paths)
    api_text = (Path(__file__).resolve().parents[1] / "app" / "api" / "customer_vehicle_intents.py").read_text(encoding="utf-8")
    assert "quote" not in api_text.lower()
    assert "contract" not in api_text.lower()


def test_list_customer_vehicle_intents_returns_customer_scoped_rows() -> None:
    customer = build_customer()
    intent = build_intent(customer.id)
    service = CustomerVehicleIntentService(FakeSession(customer=customer, rows=[intent]))

    rows = service.list_for_customer(customer.id)

    assert rows == [intent]


def test_create_customer_vehicle_intent_records_source_type_source_note_and_keeps_sales_candidate_signal() -> None:
    customer = build_customer(grade=CustomerGrade.C, status=CustomerStatus.READY_FOR_SALES)
    session = FakeSession(customer=customer)
    service = CustomerVehicleIntentService(session)

    intent = service.create_for_customer(
        customer.id,
        request=create_payload(customer.id),
        now=datetime(2026, 6, 4, 12, tzinfo=UTC),
    )

    assert intent.customer_id == customer.id
    assert intent.source_type == CustomerVehicleIntentSourceType.MANUAL_BUSINESS_NOTE
    assert intent.source_note == "销售记录客户关注 Camry。"
    assert intent.status == CustomerVehicleIntentStatus.ACTIVE
    assert intent.created_by == "sales-a"
    assert session.flushed is True
    assert service.is_sales_candidate_customer(customer, [intent]) is True
    assert not hasattr(intent, "quote_id")
    assert not hasattr(intent, "contract_id")


def test_create_blocks_customer_id_mismatch_and_do_not_contact_customer() -> None:
    customer = build_customer(do_not_contact=True, status=CustomerStatus.DO_NOT_CONTACT)
    service = CustomerVehicleIntentService(FakeSession(customer=customer))

    try:
        service.create_for_customer(uuid4(), request=create_payload(customer.id), now=datetime(2026, 6, 4, 12, tzinfo=UTC))
    except ValueError as exc:
        assert "customer_id" in str(exc)
    else:
        raise AssertionError("路径 customer_id 与请求 customer_id 不一致时必须拒绝")

    try:
        service.create_for_customer(customer.id, request=create_payload(customer.id), now=datetime(2026, 6, 4, 12, tzinfo=UTC))
    except ValueError as exc:
        assert "勿扰客户" in str(exc)
    else:
        raise AssertionError("勿扰客户不得新增意向车型")


def test_update_customer_vehicle_intent_supports_fields_and_status_update() -> None:
    customer = build_customer()
    intent = build_intent(customer.id)
    session = FakeSession(customer=customer, intent=intent)
    service = CustomerVehicleIntentService(session)

    updated = service.update_intent(
        intent.id,
        request=CustomerVehicleIntentUpdate(
            brand="Honda",
            model="CR-V",
            quantity=3,
            status=CustomerVehicleIntentStatus.PENDING_CONFIRMATION,
            source_type=CustomerVehicleIntentSourceType.MANUAL_CUSTOMER_REPLY,
            source_note="客户回复确认关注 CR-V。",
        ),
        now=datetime(2026, 6, 4, 13, tzinfo=UTC),
    )

    assert updated.brand == "Honda"
    assert updated.model == "CR-V"
    assert updated.quantity == 3
    assert updated.status == CustomerVehicleIntentStatus.PENDING_CONFIRMATION
    assert updated.source_type == CustomerVehicleIntentSourceType.MANUAL_CUSTOMER_REPLY
    assert updated.source_note == "客户回复确认关注 CR-V。"
    assert updated.updated_at == datetime(2026, 6, 4, 13, tzinfo=UTC)
