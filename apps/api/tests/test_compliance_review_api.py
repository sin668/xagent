import asyncio

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.db.session import AsyncSessionLocal
from app.main import app
from app.models import ComplianceReview, Customer
from app.models.enums import CustomerGrade, CustomerStatus, CustomerType


TEST_PREFIX = "TEST-E6S3-"


async def cleanup_records() -> None:
    async with AsyncSessionLocal() as async_session:
        customer_ids = (
            await async_session.execute(select(Customer.id).where(Customer.external_id.like(f"{TEST_PREFIX}%")))
        ).scalars().all()
        if customer_ids:
            await async_session.execute(delete(ComplianceReview).where(ComplianceReview.customer_id.in_(customer_ids)))
        await async_session.execute(delete(Customer).where(Customer.external_id.like(f"{TEST_PREFIX}%")))
        await async_session.commit()


async def create_customer(external_id: str, grade: CustomerGrade = CustomerGrade.C) -> str:
    async with AsyncSessionLocal() as async_session:
        def add(sync_session):
            customer = Customer(
                external_id=external_id,
                name=f"{external_id} Dealer",
                country="Russia",
                city="Moscow",
                customer_type=CustomerType.LOCAL_DEALER_SECONDARY_DEALER,
                grade=grade,
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


def test_c_grade_customer_enters_pending_review_queue_and_blocks_quoted_until_approved() -> None:
    client = TestClient(app)
    customer_id = asyncio.run(create_customer(f"{TEST_PREFIX}C-001"))

    queue = client.get("/compliance/reviews/pending")
    assert queue.status_code == 200
    assert customer_id in [item["customer_id"] for item in queue.json()["items"]]

    status = client.get(f"/compliance/customers/{customer_id}/status")
    assert status.status_code == 200
    payload = status.json()
    assert payload["status"] == "pending"
    assert payload["quote_contract_blocked"] is True
    assert "AI仅提示风险" in payload["ai_risk_tip"]

    quoted = client.post(f"/compliance/customers/{customer_id}/mark-quoted", json={"actor": "sales"})
    assert quoted.status_code == 400
    assert "合规复核" in quoted.json()["detail"]


def test_compliance_review_records_reviewer_time_decision_and_prevents_non_compliance_override() -> None:
    client = TestClient(app)
    customer_id = asyncio.run(create_customer(f"{TEST_PREFIX}C-002"))

    rejected = client.post(
        f"/compliance/customers/{customer_id}/review",
        json={
            "actor": "sales-user",
            "actor_role": "sales",
            "status": "approved",
            "reason": "贸易路径可行",
            "risk_note": "支付路径待复核",
        },
    )
    assert rejected.status_code == 403

    approved = client.post(
        f"/compliance/customers/{customer_id}/review",
        json={
            "actor": "Compliance Anna",
            "actor_role": "compliance",
            "status": "approved",
            "reason": "贸易路径初步可行",
            "risk_note": "付款、物流、清关仍需人工确认",
        },
    )
    assert approved.status_code == 200
    review = approved.json()
    assert review["reviewer"] == "Compliance Anna"
    assert review["status"] == "approved"
    assert review["reason"] == "贸易路径初步可行"
    assert review["risk_note"] == "付款、物流、清关仍需人工确认"
    assert review["reviewed_at"]

    quoted = client.post(f"/compliance/customers/{customer_id}/mark-quoted", json={"actor": "sales"})
    assert quoted.status_code == 200
    assert quoted.json()["quoted_status"] == "quoted"
