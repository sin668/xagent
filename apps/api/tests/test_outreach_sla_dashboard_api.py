import asyncio
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.db.session import AsyncSessionLocal
from app.main import app
from app.models import ComplianceReview, Customer, OutreachRecord
from app.models.enums import (
    ChannelRiskLevel,
    ComplianceReviewStatus,
    ContactMethodType,
    CustomerGrade,
    CustomerStatus,
    CustomerType,
    OutreachStatus,
)


TEST_PREFIX = "TEST-E7S2-"


async def cleanup_records() -> None:
    async with AsyncSessionLocal() as async_session:
        customer_ids = (
            await async_session.execute(select(Customer.id).where(Customer.external_id.like(f"{TEST_PREFIX}%")))
        ).scalars().all()
        if customer_ids:
            await async_session.execute(delete(OutreachRecord).where(OutreachRecord.customer_id.in_(customer_ids)))
            await async_session.execute(delete(ComplianceReview).where(ComplianceReview.customer_id.in_(customer_ids)))
        await async_session.execute(delete(Customer).where(Customer.external_id.like(f"{TEST_PREFIX}%")))
        await async_session.commit()


async def seed_sla_records() -> None:
    async with AsyncSessionLocal() as async_session:
        def add(sync_session):
            now = datetime.utcnow()

            def customer(suffix, grade, status, owner, hours_old, *, do_not_contact=False):
                item = Customer(
                    external_id=f"{TEST_PREFIX}{suffix}",
                    name=f"{TEST_PREFIX}{suffix} Dealer",
                    country="Russia",
                    city="Moscow",
                    customer_type=CustomerType.LOCAL_DEALER_SECONDARY_DEALER,
                    grade=grade,
                    status=status,
                    owner=owner,
                    do_not_contact=do_not_contact,
                    updated_at=now - timedelta(hours=hours_old),
                )
                sync_session.add(item)
                sync_session.flush()
                return item

            b_overdue = customer("B-OVERDUE", CustomerGrade.B, CustomerStatus.CUSTOMER_SERVICE_FOLLOWING, "Anna", 50)
            customer("B-OK", CustomerGrade.B, CustomerStatus.READY_FOR_CUSTOMER_SERVICE, "Anna", 10)
            customer("B-DNC", CustomerGrade.B, CustomerStatus.DO_NOT_CONTACT, "Anna", 72, do_not_contact=True)
            c_waiting = customer("C-WAITING", CustomerGrade.C, CustomerStatus.READY_FOR_SALES, "Boris", 30)
            c_overdue = customer("C-OVERDUE", CustomerGrade.C, CustomerStatus.SALES_FOLLOWING, "Boris", 26)

            sync_session.add_all(
                [
                    ComplianceReview(
                        customer_id=c_waiting.id,
                        status=ComplianceReviewStatus.PENDING,
                        reason="等待 C 级报价前合规复核",
                    ),
                    ComplianceReview(
                        customer_id=c_overdue.id,
                        status=ComplianceReviewStatus.APPROVED,
                        reviewer="Compliance Anna",
                        reviewed_at=now - timedelta(hours=28),
                        reason="贸易路径初步可行",
                    ),
                    OutreachRecord(
                        external_id=f"{TEST_PREFIX}OUT-SENT",
                        customer_id=b_overdue.id,
                        channel=ContactMethodType.EMAIL,
                        status=OutreachStatus.SENT,
                        owner="Anna",
                        sent_by="Anna",
                        sent_at=now - timedelta(hours=20),
                    ),
                    OutreachRecord(
                        external_id=f"{TEST_PREFIX}OUT-REPLIED",
                        customer_id=c_overdue.id,
                        channel=ContactMethodType.EMAIL,
                        status=OutreachStatus.REPLIED,
                        owner="Boris",
                        sent_by="Boris",
                        sent_at=now - timedelta(hours=18),
                        response_summary="客户回复需要报价",
                    ),
                    OutreachRecord(
                        external_id=f"{TEST_PREFIX}OUT-NO-RESPONSE",
                        customer_id=c_overdue.id,
                        channel=ContactMethodType.TELEGRAM,
                        status=OutreachStatus.NO_RESPONSE,
                        owner="Boris",
                        sent_by="Boris",
                        sent_at=now - timedelta(hours=12),
                    ),
                ]
            )

        await async_session.run_sync(add)
        await async_session.commit()


@pytest.fixture(autouse=True)
def isolated_sla_records():
    asyncio.run(cleanup_records())
    asyncio.run(seed_sla_records())
    yield
    asyncio.run(cleanup_records())


def test_outreach_sla_dashboard_counts_replies_sla_and_excludes_do_not_contact() -> None:
    client = TestClient(app)

    response = client.get("/dashboard/outreach-sla")

    assert response.status_code == 200
    payload = response.json()
    summary = payload["summary"]

    assert summary["sent_count"] == 3
    assert summary["replied_count"] == 1
    assert summary["response_rate"] == pytest.approx(1 / 3)
    assert summary["pending_count"] == 4
    assert summary["overdue_count"] == 2
    assert summary["compliance_waiting_count"] == 1
    assert summary["sla_risk_count"] == 3

    queue_names = {item["customer_name"] for item in payload["queue"]}
    assert f"{TEST_PREFIX}B-DNC Dealer" not in queue_names

    b_item = next(item for item in payload["queue"] if item["customer_name"] == f"{TEST_PREFIX}B-OVERDUE Dealer")
    assert b_item["grade"] == "B"
    assert b_item["sla_hours"] == 48
    assert b_item["risk_status"] == "overdue"

    c_waiting = next(item for item in payload["queue"] if item["customer_name"] == f"{TEST_PREFIX}C-WAITING Dealer")
    assert c_waiting["grade"] == "C"
    assert c_waiting["sla_hours"] == 24
    assert c_waiting["risk_status"] == "compliance_waiting"
    assert c_waiting["next_action"] == "等待合规复核"


def test_outreach_sla_dashboard_supports_owner_grade_and_channel_filters() -> None:
    client = TestClient(app)

    owner_response = client.get("/dashboard/outreach-sla?owner=Anna&grade=B")
    assert owner_response.status_code == 200
    owner_payload = owner_response.json()
    assert owner_payload["summary"]["pending_count"] == 2
    assert all(item["owner"] == "Anna" for item in owner_payload["queue"])
    assert all(item["grade"] == "B" for item in owner_payload["queue"])

    channel_response = client.get("/dashboard/outreach-sla?channel=email")
    assert channel_response.status_code == 200
    channel_summary = channel_response.json()["summary"]
    assert channel_summary["sent_count"] == 2
    assert channel_summary["replied_count"] == 1
    assert channel_summary["response_rate"] == pytest.approx(0.5)
    assert {item["customer_name"] for item in channel_response.json()["queue"]} == {
        f"{TEST_PREFIX}B-OVERDUE Dealer",
        f"{TEST_PREFIX}C-OVERDUE Dealer",
    }
