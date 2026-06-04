import asyncio

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.db.session import AsyncSessionLocal
from app.main import app
from app.models import Customer, OutreachRecord
from app.models.enums import CustomerGrade, CustomerStatus, CustomerType


TEST_PREFIX = "TEST-E4S2-API-"


async def cleanup_test_records() -> None:
    async with AsyncSessionLocal() as async_session:
        customer_ids = (
            await async_session.execute(select(Customer.id).where(Customer.external_id.like(f"{TEST_PREFIX}%")))
        ).scalars().all()
        if customer_ids:
            await async_session.execute(delete(OutreachRecord).where(OutreachRecord.customer_id.in_(customer_ids)))
        await async_session.execute(delete(Customer).where(Customer.external_id.like(f"{TEST_PREFIX}%")))
        await async_session.commit()


async def create_customer(external_id: str, do_not_contact: bool = False) -> str:
    async with AsyncSessionLocal() as async_session:
        def add(sync_session):
            customer = Customer(
                external_id=external_id,
                name=f"{external_id} Dealer",
                country="Russia",
                city="Moscow",
                customer_type=CustomerType.LOCAL_DEALER_SECONDARY_DEALER,
                grade=CustomerGrade.B,
                status=CustomerStatus.READY_FOR_CUSTOMER_SERVICE,
                do_not_contact=do_not_contact,
            )
            if do_not_contact:
                customer.status = CustomerStatus.DO_NOT_CONTACT
                customer.do_not_contact_reason = "客户已拒绝"
            sync_session.add(customer)
            sync_session.flush()
            return str(customer.id)

        customer_id = await async_session.run_sync(add)
        await async_session.commit()
        return customer_id


@pytest.fixture(autouse=True)
def isolated_records():
    asyncio.run(cleanup_test_records())
    yield
    asyncio.run(cleanup_test_records())


def test_outreach_record_api_supports_required_statuses_and_lists_history() -> None:
    client = TestClient(app)
    customer_id = asyncio.run(create_customer(f"{TEST_PREFIX}LEAD-001"))

    statuses = ["sent", "replied", "no_response", "bad_contact", "rejected"]
    for index, status in enumerate(statuses):
        response = client.post(
            f"/customers/{customer_id}/outreach-records",
            json={
                "channel": "email",
                "status": status,
                "sent_by": "Anna Sender",
                "owner": "Boris Owner",
                "response_summary": f"状态 {status}",
                "next_action": "继续跟进" if status != "rejected" else "标记勿扰",
                "manual_confirmed": True,
                "script_version": "TMP-RU-B-001/v1",
                "external_id": f"{TEST_PREFIX}OUT-{index}",
                "do_not_contact_reason": "客户明确拒绝继续联系" if status == "rejected" else None,
            },
        )
        assert response.status_code == 200
        assert response.json()["status"] == status

    history_response = client.get(f"/customers/{customer_id}/outreach-records")
    assert history_response.status_code == 200
    history = history_response.json()["items"]
    assert [item["status"] for item in history] == statuses
    assert history[0]["sent_by"] == "Anna Sender"
    assert history[0]["owner"] == "Boris Owner"
    assert history[0]["script_version"] == "TMP-RU-B-001/v1"


def test_outreach_record_api_requires_manual_confirmation_for_sent() -> None:
    client = TestClient(app)
    customer_id = asyncio.run(create_customer(f"{TEST_PREFIX}LEAD-002"))

    response = client.post(
        f"/customers/{customer_id}/outreach-records",
        json={
            "channel": "email",
            "status": "sent",
            "sent_by": "Anna",
            "owner": "Anna",
            "response_summary": "已人工发送",
            "next_action": "等待回复",
            "manual_confirmed": False,
        },
    )

    assert response.status_code == 400
    assert "人工确认" in response.json()["detail"]


def test_outreach_record_api_blocks_do_not_contact_customer() -> None:
    client = TestClient(app)
    customer_id = asyncio.run(create_customer(f"{TEST_PREFIX}LEAD-003", do_not_contact=True))

    response = client.post(
        f"/customers/{customer_id}/outreach-records",
        json={
            "channel": "email",
            "status": "sent",
            "sent_by": "Anna",
            "owner": "Anna",
            "response_summary": "已人工发送",
            "next_action": "等待回复",
            "manual_confirmed": True,
        },
    )

    assert response.status_code == 400
    assert "勿扰" in response.json()["detail"]


def test_rejected_outreach_marks_customer_do_not_contact() -> None:
    client = TestClient(app)
    customer_id = asyncio.run(create_customer(f"{TEST_PREFIX}LEAD-004"))

    response = client.post(
        f"/customers/{customer_id}/outreach-records",
        json={
            "channel": "email",
            "status": "rejected",
            "sent_by": "Anna",
            "owner": "Anna",
            "response_summary": "客户回复不要再联系",
            "next_action": "标记勿扰",
            "manual_confirmed": True,
            "do_not_contact_reason": "客户明确拒绝继续联系",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["triggers_do_not_contact"] is True
    assert payload["do_not_contact_reason"] == "客户明确拒绝继续联系"

    customer_response = client.get(f"/customers/{customer_id}")
    assert customer_response.status_code == 200
    customer = customer_response.json()
    assert customer["do_not_contact"] is True
    assert customer["status"] == "do_not_contact"
