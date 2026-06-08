from pathlib import Path

from pydantic import ValidationError
from sqlalchemy import insert, select
from sqlalchemy.dialects import postgresql

from app.db.base import Base
from app.models import CustomerFollowup, CustomerVehicleIntent
from app.models.enums import (
    CustomerFollowupTeam,
    CustomerFollowupType,
    CustomerVehicleIntentSourceType,
    CustomerVehicleIntentStatus,
)
from app.schemas.customer_followup import CustomerFollowupCreate, CustomerFollowupUpdate
from app.schemas.customer_vehicle_intent import CustomerVehicleIntentCreate, CustomerVehicleIntentUpdate


API_ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = API_ROOT / "alembic" / "versions" / "20260604_0027_create_customer_intents_followups.py"


def test_customer_intents_followups_migration_declares_required_tables_and_fields() -> None:
    assert MIGRATION_PATH.exists()
    migration = MIGRATION_PATH.read_text(encoding="utf-8")

    assert 'revision = "20260604_0027"' in migration
    assert 'down_revision = "20260604_0026"' in migration
    assert '"customer_vehicle_intents"' in migration
    assert '"customer_followups"' in migration

    for field_name in (
        "customer_id",
        "brand",
        "model",
        "year_range",
        "vehicle_age",
        "quantity",
        "budget_range",
        "purchase_frequency",
        "delivery_country",
        "delivery_city",
        "concerns",
        "source_type",
        "source_note",
        "status",
        "created_by",
        "created_at",
        "updated_at",
    ):
        assert field_name in migration

    for field_name in (
        "customer_id",
        "owner_id",
        "team",
        "followup_type",
        "content",
        "customer_feedback",
        "next_action",
        "next_followup_at",
        "triggered_dnc",
        "triggered_compliance_review",
        "created_by",
        "created_at",
        "updated_at",
    ):
        assert field_name in migration
    assert '["customers.id"]' in migration


def test_customer_intents_followups_models_are_registered_for_alembic_metadata() -> None:
    table_names = set(Base.metadata.tables.keys())
    models_init = (API_ROOT / "app" / "models" / "__init__.py").read_text(encoding="utf-8")

    assert "customer_vehicle_intents" in table_names
    assert "customer_followups" in table_names
    assert "CustomerVehicleIntent" in models_init
    assert "CustomerFollowup" in models_init
    assert "CustomerVehicleIntentStatus" in models_init
    assert "CustomerFollowupType" in models_init


def test_customer_model_does_not_store_intents_or_followups_as_json() -> None:
    customer_columns = set(Base.metadata.tables["customers"].columns.keys())

    assert "vehicle_intents_json" not in customer_columns
    assert "followups_json" not in customer_columns


def test_vehicle_intent_schema_defaults_and_validation() -> None:
    payload = CustomerVehicleIntentCreate(
        customer_id="11111111-1111-1111-1111-111111111111",
        brand="Toyota",
        model="Camry",
        year_range="2020-2024",
        vehicle_age="0-5 years",
        quantity=3,
        budget_range="20000-30000 USD",
        purchase_frequency="monthly",
        delivery_country="Russia",
        delivery_city="Moscow",
        concerns=["price", "logistics"],
        source_type=CustomerVehicleIntentSourceType.MANUAL_CUSTOMER_REPLY,
        source_note="客户回复中提到。",
        created_by="sales-a",
    )

    assert payload.status == CustomerVehicleIntentStatus.ACTIVE
    assert payload.concerns == ["price", "logistics"]

    try:
        CustomerVehicleIntentCreate(
            customer_id="11111111-1111-1111-1111-111111111111",
            quantity=0,
            source_type=CustomerVehicleIntentSourceType.MANUAL_BUSINESS_NOTE,
            created_by="sales-a",
        )
    except ValidationError as exc:
        assert "quantity" in str(exc)
    else:
        raise AssertionError("quantity below 1 should be rejected")


def test_followup_schema_captures_dnc_and_compliance_triggers() -> None:
    payload = CustomerFollowupCreate(
        customer_id="11111111-1111-1111-1111-111111111111",
        owner_id="sales-a",
        team=CustomerFollowupTeam.SALES,
        followup_type=CustomerFollowupType.MANUAL_CALL,
        content="客户询问付款和交付周期，需合规复核。",
        customer_feedback="希望确认清关责任。",
        next_action="提交合规复核。",
        triggered_compliance_review=True,
        created_by="sales-a",
    )

    assert payload.triggered_dnc is False
    assert payload.triggered_compliance_review is True

    try:
        CustomerFollowupCreate(
            customer_id="11111111-1111-1111-1111-111111111111",
            owner_id="sales-a",
            team=CustomerFollowupTeam.SALES,
            followup_type=CustomerFollowupType.MANUAL_MESSAGE,
            content="客户拒绝继续联系。",
            triggered_dnc=True,
            created_by="sales-a",
        )
    except ValidationError as exc:
        assert "customer_feedback" in str(exc)
    else:
        raise AssertionError("DNC-triggering followup should include customer_feedback")


def test_update_schemas_preserve_audit_bounds() -> None:
    try:
        CustomerVehicleIntentUpdate(quantity=0)
    except ValidationError as exc:
        assert "quantity" in str(exc)
    else:
        raise AssertionError("quantity below 1 should be rejected")

    try:
        CustomerFollowupUpdate(triggered_dnc=True)
    except ValidationError as exc:
        assert "customer_feedback" in str(exc)
    else:
        raise AssertionError("DNC-triggering update should include customer_feedback")


def test_customer_intents_followups_can_compile_minimal_insert_and_select_sql() -> None:
    intent_insert = insert(CustomerVehicleIntent).values(
        customer_id="11111111-1111-1111-1111-111111111111",
        brand="Toyota",
        model="Camry",
        quantity=2,
        source_type=CustomerVehicleIntentSourceType.MANUAL_CUSTOMER_REPLY,
        status=CustomerVehicleIntentStatus.ACTIVE,
        created_by="sales-a",
    )
    followup_insert = insert(CustomerFollowup).values(
        customer_id="11111111-1111-1111-1111-111111111111",
        owner_id="sales-a",
        team=CustomerFollowupTeam.SALES,
        followup_type=CustomerFollowupType.MANUAL_CALL,
        content="客户要求补充报价前资料。",
        triggered_dnc=False,
        triggered_compliance_review=False,
        created_by="sales-a",
    )
    query = select(CustomerFollowup).where(CustomerFollowup.team == CustomerFollowupTeam.SALES)

    compiled_intent = str(intent_insert.compile(dialect=postgresql.dialect()))
    compiled_followup = str(followup_insert.compile(dialect=postgresql.dialect()))
    compiled_query = str(query.compile(dialect=postgresql.dialect()))

    assert "INSERT INTO customer_vehicle_intents" in compiled_intent
    assert "INSERT INTO customer_followups" in compiled_followup
    assert "customer_followups" in compiled_query
