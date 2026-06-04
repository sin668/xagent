import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.db.session import AsyncSessionLocal
from app.main import app
from app.models import InventoryItem


TEST_PREFIX = "TEST-E5S1-"


async def cleanup_inventory_records() -> None:
    async with AsyncSessionLocal() as async_session:
        await async_session.execute(delete(InventoryItem).where(InventoryItem.external_id.like(f"{TEST_PREFIX}%")))
        await async_session.commit()


@pytest.fixture(autouse=True)
def isolated_inventory():
    asyncio.run(cleanup_inventory_records())
    yield
    asyncio.run(cleanup_inventory_records())


def test_inventory_api_creates_lists_required_fields_and_flags_expired_items() -> None:
    client = TestClient(app)
    now = datetime.now(UTC)

    create_response = client.post(
        "/inventory/items",
        json={
            "external_id": f"{TEST_PREFIX}BYD-001",
            "brand": "BYD",
            "model": "Song Plus",
            "year": 2023,
            "mileage_km": 12000,
            "vehicle_type": "SUV",
            "condition_summary": "准新车，检测报告可提供",
            "configuration": "旗舰版，四驱，黑色内饰",
            "quoted_price": 23800,
            "currency": "USD",
            "quote_status": "confirmed",
            "export_ready": True,
            "media_urls": [
                "https://example.com/byd-song-plus.jpg",
                "https://example.com/byd-song-plus-video.mp4",
            ],
            "valid_until": (now + timedelta(days=5)).isoformat(),
            "source_ref": "feishu:inventory:BYD-001",
        },
    )

    assert create_response.status_code == 200
    created = create_response.json()
    assert created["brand"] == "BYD"
    assert created["configuration"] == "旗舰版，四驱，黑色内饰"
    assert created["media_urls"] == [
        "https://example.com/byd-song-plus.jpg",
        "https://example.com/byd-song-plus-video.mp4",
    ]
    assert created["is_expired"] is False
    assert created["can_ai_quote"] is True
    assert created["priority_recommendable"] is True

    expired_response = client.post(
        "/inventory/items",
        json={
            "external_id": f"{TEST_PREFIX}OLD-001",
            "brand": "Geely",
            "model": "Monjaro",
            "year": 2021,
            "mileage_km": 58000,
            "condition_summary": "库存信息待复核",
            "configuration": "高配，白色",
            "quoted_price": 19900,
            "currency": "USD",
            "quote_status": "pending",
            "export_ready": True,
            "media_urls": [],
            "valid_until": (now - timedelta(days=1)).isoformat(),
        },
    )
    assert expired_response.status_code == 200

    list_response = client.get("/inventory/items")
    assert list_response.status_code == 200
    items = list_response.json()["items"]
    assert [item["external_id"] for item in items] == [f"{TEST_PREFIX}BYD-001", f"{TEST_PREFIX}OLD-001"]
    expired = items[1]
    assert expired["is_expired"] is True
    assert expired["priority_recommendable"] is False
    assert expired["can_ai_quote"] is False
    assert "过期" in expired["risk_flags"]
    assert "价格未确认" in expired["risk_flags"]


def test_inventory_api_blocks_ai_quote_for_unconfirmed_or_expired_price() -> None:
    client = TestClient(app)
    now = datetime.now(UTC)

    for external_id, quote_status, valid_until in [
        (f"{TEST_PREFIX}PENDING", "pending", now + timedelta(days=3)),
        (f"{TEST_PREFIX}EXPIRED", "confirmed", now - timedelta(days=1)),
    ]:
        response = client.post(
            "/inventory/items",
            json={
                "external_id": external_id,
                "brand": "Changan",
                "model": "CS75 Plus",
                "year": 2023,
                "mileage_km": 8600,
                "condition_summary": "准新车",
                "configuration": "豪华版",
                "quoted_price": 21500,
                "currency": "USD",
                "quote_status": quote_status,
                "export_ready": True,
                "media_urls": ["https://example.com/changan.jpg"],
                "valid_until": valid_until.isoformat(),
            },
        )
        assert response.status_code == 200

    ai_quote_response = client.get(f"/inventory/items/{TEST_PREFIX}PENDING/ai-quote-safety")
    assert ai_quote_response.status_code == 200
    pending = ai_quote_response.json()
    assert pending["can_ai_quote"] is False
    assert "价格未确认" in pending["blocking_reasons"]

    expired_quote_response = client.get(f"/inventory/items/{TEST_PREFIX}EXPIRED/ai-quote-safety")
    assert expired_quote_response.status_code == 200
    expired = expired_quote_response.json()
    assert expired["can_ai_quote"] is False
    assert "车源已过期" in expired["blocking_reasons"]
