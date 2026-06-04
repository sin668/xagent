import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.db.session import AsyncSessionLocal
from app.main import app
from app.models import Customer, InventoryItem, LeadInventoryMatch
from app.models.enums import CustomerGrade, CustomerStatus, CustomerType


TEST_PREFIX = "TEST-E5S2-"


async def cleanup_records() -> None:
    async with AsyncSessionLocal() as async_session:
        customer_ids = (
            await async_session.execute(select(Customer.id).where(Customer.external_id.like(f"{TEST_PREFIX}%")))
        ).scalars().all()
        inventory_ids = (
            await async_session.execute(select(InventoryItem.id).where(InventoryItem.external_id.like(f"{TEST_PREFIX}%")))
        ).scalars().all()
        if customer_ids:
            await async_session.execute(delete(LeadInventoryMatch).where(LeadInventoryMatch.customer_id.in_(customer_ids)))
        if inventory_ids:
            await async_session.execute(delete(LeadInventoryMatch).where(LeadInventoryMatch.inventory_item_id.in_(inventory_ids)))
        await async_session.execute(delete(Customer).where(Customer.external_id.like(f"{TEST_PREFIX}%")))
        await async_session.execute(delete(InventoryItem).where(InventoryItem.external_id.like(f"{TEST_PREFIX}%")))
        await async_session.commit()


async def create_customer() -> str:
    async with AsyncSessionLocal() as async_session:
        def add(sync_session):
            customer = Customer(
                external_id=f"{TEST_PREFIX}CUSTOMER",
                name="Siberia Auto Trade",
                country="Russia",
                city="Novosibirsk",
                customer_type=CustomerType.LOCAL_DEALER_SECONDARY_DEALER,
                grade=CustomerGrade.C,
                status=CustomerStatus.READY_FOR_SALES,
            )
            sync_session.add(customer)
            sync_session.flush()
            return str(customer.id)

        customer_id = await async_session.run_sync(add)
        await async_session.commit()
        return customer_id


@pytest.fixture(autouse=True)
def isolated_records():
    asyncio.run(cleanup_records())
    yield
    asyncio.run(cleanup_records())


def seed_inventory(client: TestClient) -> None:
    now = datetime.now(UTC)
    for payload in [
        {
            "external_id": f"{TEST_PREFIX}BYD",
            "brand": "BYD",
            "model": "Song Plus",
            "year": 2023,
            "mileage_km": 12000,
            "vehicle_type": "SUV",
            "condition_summary": "准新车，检测报告可提供",
            "configuration": "旗舰版，四驱",
            "quoted_price": 23800,
            "currency": "USD",
            "quote_status": "confirmed",
            "export_ready": True,
            "media_urls": ["https://example.com/byd.jpg"],
            "valid_until": (now + timedelta(days=5)).isoformat(),
        },
        {
            "external_id": f"{TEST_PREFIX}GEELY",
            "brand": "Geely",
            "model": "Monjaro",
            "year": 2021,
            "mileage_km": 38000,
            "vehicle_type": "SUV",
            "condition_summary": "库存车",
            "configuration": "高配",
            "quoted_price": 19800,
            "currency": "USD",
            "quote_status": "pending",
            "export_ready": True,
            "media_urls": [],
            "valid_until": (now + timedelta(days=3)).isoformat(),
        },
        {
            "external_id": f"{TEST_PREFIX}OLD",
            "brand": "Changan",
            "model": "CS75 Plus",
            "year": 2020,
            "mileage_km": 8600,
            "vehicle_type": "SUV",
            "condition_summary": "准新车",
            "configuration": "豪华版",
            "quoted_price": 21500,
            "currency": "USD",
            "quote_status": "confirmed",
            "export_ready": True,
            "media_urls": [],
            "valid_until": (now - timedelta(days=1)).isoformat(),
        },
    ]:
        response = client.post("/inventory/items", json=payload)
        assert response.status_code == 200


def test_inventory_matching_recommends_export_ready_items_with_reason_and_compliance_warning() -> None:
    client = TestClient(app)
    customer_id = asyncio.run(create_customer())
    seed_inventory(client)

    response = client.post(
        f"/inventory/matches/{customer_id}/recommendations",
        json={
            "vehicle_type": "SUV",
            "min_year": 2022,
            "max_price": 25000,
            "requires_compliance_review": True,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["customer_id"] == customer_id
    assert payload["quote_disclaimer"] == "推荐车源仅用于人工报价前评估，不等同于正式报价。"
    assert len(payload["items"]) == 1
    item = payload["items"][0]
    assert item["inventory_external_id"] == f"{TEST_PREFIX}BYD"
    assert item["priority_recommendable"] is True
    assert item["requires_compliance_review"] is True
    assert "车型匹配 SUV" in item["recommendation_reason"]
    assert "年份满足 2022+" in item["recommendation_reason"]
    assert "车况: 准新车" in item["recommendation_reason"]
    assert "价格有效期" in item["recommendation_reason"]
    assert "可出口" in item["recommendation_reason"]
    assert "C级线索报价前必须合规复核" in item["risk_tips"]


def test_inventory_match_decision_records_advance_quote_and_not_match() -> None:
    client = TestClient(app)
    customer_id = asyncio.run(create_customer())
    seed_inventory(client)
    recommendations = client.post(
        f"/inventory/matches/{customer_id}/recommendations",
        json={"vehicle_type": "SUV", "min_year": 2022, "max_price": 25000, "requires_compliance_review": True},
    ).json()["items"]
    match_id = recommendations[0]["match_id"]

    advance = client.post(
        f"/inventory/matches/{match_id}/decision",
        json={"decision": "advance_quote", "owner": "Nikita", "note": "进入报价前合规复核"},
    )
    assert advance.status_code == 200
    assert advance.json()["decision"] == "advance_quote"
    assert advance.json()["formal_quote_allowed"] is False
    assert "合规复核" in advance.json()["next_gate"]

    not_match = client.post(
        f"/inventory/matches/{match_id}/decision",
        json={"decision": "not_match", "owner": "Nikita", "note": "客户预算不匹配"},
    )
    assert not_match.status_code == 200
    assert not_match.json()["decision"] == "not_match"
