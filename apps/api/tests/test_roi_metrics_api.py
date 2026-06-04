import asyncio
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.db.session import AsyncSessionLocal
from app.main import app
from app.models import Customer, LeadSource, OutreachRecord, RoiCostEntry
from app.models.enums import ChannelRiskLevel, ContactMethodType, CustomerGrade, CustomerStatus, CustomerType, OutreachStatus, SourcePlatform


TEST_PREFIX = "TEST-E7S3-"


async def cleanup_records() -> None:
    async with AsyncSessionLocal() as async_session:
        customer_ids = (
            await async_session.execute(select(Customer.id).where(Customer.external_id.like(f"{TEST_PREFIX}%")))
        ).scalars().all()
        if customer_ids:
            await async_session.execute(delete(OutreachRecord).where(OutreachRecord.customer_id.in_(customer_ids)))
            await async_session.execute(delete(LeadSource).where(LeadSource.customer_id.in_(customer_ids)))
        await async_session.execute(delete(Customer).where(Customer.external_id.like(f"{TEST_PREFIX}%")))
        await async_session.execute(delete(RoiCostEntry).where(RoiCostEntry.external_id.like(f"{TEST_PREFIX}%")))
        await async_session.commit()


async def seed_roi_records() -> None:
    async with AsyncSessionLocal() as async_session:
        def add(sync_session):
            customers = []
            for suffix, grade in [("B-001", CustomerGrade.B), ("C-001", CustomerGrade.C), ("INVALID", CustomerGrade.INVALID)]:
                customer = Customer(
                    external_id=f"{TEST_PREFIX}{suffix}",
                    name=f"{TEST_PREFIX}{suffix} Dealer",
                    country="Russia",
                    city="Moscow",
                    customer_type=CustomerType.LOCAL_DEALER_SECONDARY_DEALER,
                    grade=grade,
                    status=CustomerStatus.READY_FOR_SALES,
                    owner="Anna",
                )
                sync_session.add(customer)
                sync_session.flush()
                sync_session.add(
                    LeadSource(
                        external_id=f"{TEST_PREFIX}SRC-{suffix}",
                        customer_id=customer.id,
                        platform=SourcePlatform.OFFICIAL_WEBSITE,
                        source_url=f"https://example.com/{suffix}",
                        evidence_note="公开来源证据",
                        channel_risk_level=ChannelRiskLevel.LOW,
                    )
                )
                customers.append(customer)

            sync_session.add(
                OutreachRecord(
                    external_id=f"{TEST_PREFIX}OUT-REPLIED",
                    customer_id=customers[1].id,
                    channel=ContactMethodType.EMAIL,
                    status=OutreachStatus.REPLIED,
                    owner="Anna",
                    sent_by="Anna",
                    sent_at=datetime.utcnow(),
                    response_summary="客户回复需要报价",
                )
            )
            sync_session.add_all(
                [
                    RoiCostEntry(
                        external_id=f"{TEST_PREFIX}COST-LABOR",
                        cost_type="labor",
                        amount=120,
                        currency="USD",
                        labor_hours=4,
                        hourly_rate=30,
                        channel_name="official_website",
                        notes="人工收集与清洗",
                    ),
                    RoiCostEntry(
                        external_id=f"{TEST_PREFIX}COST-AI",
                        cost_type="ai_api",
                        amount=20,
                        currency="USD",
                        channel_name="official_website",
                        notes="AI 抽取与分级",
                    ),
                    RoiCostEntry(
                        external_id=f"{TEST_PREFIX}COST-TOOL",
                        cost_type="tool",
                        amount=60,
                        currency="USD",
                        channel_name="official_website",
                        notes="工具订阅折算",
                    ),
                ]
            )

        await async_session.run_sync(add)
        await async_session.commit()


@pytest.fixture(autouse=True)
def isolated_roi_records():
    asyncio.run(cleanup_records())
    asyncio.run(seed_roi_records())
    yield
    asyncio.run(cleanup_records())


def test_roi_metrics_show_cost_per_effective_lead_reply_and_sales_opportunity() -> None:
    client = TestClient(app)

    response = client.get("/dashboard/roi-metrics")

    assert response.status_code == 200
    payload = response.json()
    summary = payload["summary"]

    assert summary["total_cost"] == pytest.approx(200)
    assert summary["labor_cost"] == pytest.approx(120)
    assert summary["ai_api_cost"] == pytest.approx(20)
    assert summary["tool_cost"] == pytest.approx(60)
    assert summary["effective_lead_count"] == 2
    assert summary["reply_count"] == 1
    assert summary["sales_opportunity_count"] == 1
    assert summary["cost_per_effective_lead"] == pytest.approx(100)
    assert summary["cost_per_reply"] == pytest.approx(200)
    assert summary["cost_per_sales_opportunity"] == pytest.approx(200)
    assert "不能作为绕过合规限制" in payload["compliance_guardrail"]


def test_roi_cost_api_records_labor_ai_and_tool_costs() -> None:
    client = TestClient(app)

    created = client.post(
        "/dashboard/roi-costs",
        json={
            "external_id": f"{TEST_PREFIX}COST-NEW-LABOR",
            "cost_type": "labor",
            "currency": "USD",
            "labor_hours": 5,
            "hourly_rate": 40,
            "channel_name": "youtube",
            "notes": "新增人工复核成本",
        },
    )

    assert created.status_code == 200
    cost = created.json()
    assert cost["amount"] == pytest.approx(200)
    assert cost["cost_type"] == "labor"
    assert cost["labor_hours"] == pytest.approx(5)
    assert cost["hourly_rate"] == pytest.approx(40)

    metrics = client.get("/dashboard/roi-metrics?channel=official_website")
    assert metrics.status_code == 200
    official_summary = metrics.json()["summary"]
    assert official_summary["total_cost"] == pytest.approx(200)
    assert official_summary["effective_lead_count"] == 2
    assert official_summary["reply_count"] == 1

    youtube_metrics = client.get("/dashboard/roi-metrics?channel=youtube")
    assert youtube_metrics.status_code == 200
    youtube_summary = youtube_metrics.json()["summary"]
    assert youtube_summary["total_cost"] == pytest.approx(200)
    assert youtube_summary["effective_lead_count"] == 0
    assert youtube_summary["cost_per_effective_lead"] is None


def test_roi_cost_api_returns_400_for_incomplete_labor_cost() -> None:
    client = TestClient(app)

    response = client.post(
        "/dashboard/roi-costs",
        json={
            "external_id": f"{TEST_PREFIX}COST-BAD-LABOR",
            "cost_type": "labor",
            "currency": "USD",
            "labor_hours": 5,
        },
    )

    assert response.status_code == 400
    assert "人工成本" in response.json()["detail"]
