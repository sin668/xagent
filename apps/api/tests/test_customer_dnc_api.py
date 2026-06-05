import asyncio

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.db.session import AsyncSessionLocal
from app.main import app
from app.models import Customer, OutreachRecord
from app.models.enums import CustomerGrade, CustomerStatus, CustomerType


TEST_PREFIX = "TEST-E6S2-API-"


async def cleanup_test_records() -> None:
    async with AsyncSessionLocal() as async_session:
        customer_ids = (
            await async_session.execute(select(Customer.id).where(Customer.external_id.like(f"{TEST_PREFIX}%")))
        ).scalars().all()
        if customer_ids:
            await async_session.execute(delete(OutreachRecord).where(OutreachRecord.customer_id.in_(customer_ids)))
        await async_session.execute(delete(Customer).where(Customer.external_id.like(f"{TEST_PREFIX}%")))
        await async_session.commit()


async def create_customer(external_id: str, grade: CustomerGrade = CustomerGrade.B) -> str:
    async with AsyncSessionLocal() as async_session:
        def add(sync_session):
            customer = Customer(
                external_id=external_id,
                name=f"{external_id} Dealer",
                country="Russia",
                city="Moscow",
                customer_type=CustomerType.LOCAL_DEALER_SECONDARY_DEALER,
                grade=grade,
                status=CustomerStatus.READY_FOR_CUSTOMER_SERVICE,
                do_not_contact=False,
            )
            sync_session.add(customer)
            sync_session.flush()
            return str(customer.id)

        customer_id = await async_session.run_sync(add)
        await async_session.commit()
        return customer_id


@pytest.fixture(autouse=True)
def isolated_api_records():
    asyncio.run(cleanup_test_records())
    yield
    asyncio.run(cleanup_test_records())


def test_customer_api_marks_and_unmarks_do_not_contact() -> None:
    client = TestClient(app)
    customer_id = asyncio.run(create_customer(f"{TEST_PREFIX}LEAD-001"))

    mark_response = client.post(
        f"/customers/{customer_id}/do-not-contact",
        json={"actor": "客服A", "reason": "客户明确拒绝继续联系"},
    )
    assert mark_response.status_code == 200
    marked = mark_response.json()
    assert marked["do_not_contact"] is True
    assert marked["do_not_contact_reason"] == "客户明确拒绝继续联系"
    assert marked["do_not_contact_marked_by"] == "客服A"
    assert marked["status"] == "do_not_contact"

    unmark_response = client.post(
        f"/customers/{customer_id}/do-not-contact/cancel",
        json={"actor": "主管B", "actor_role": "admin", "reason": "客户重新同意沟通"},
    )
    assert unmark_response.status_code == 200
    unmarked = unmark_response.json()
    assert unmarked["do_not_contact"] is False
    assert unmarked["do_not_contact_reason"] == "取消勿扰：客户重新同意沟通"
    assert unmarked["do_not_contact_marked_by"] == "主管B"


def test_customer_api_cancel_do_not_contact_requires_compliance_or_admin_role() -> None:
    client = TestClient(app)
    customer_id = asyncio.run(create_customer(f"{TEST_PREFIX}LEAD-ROLE-001"))

    client.post(
        f"/customers/{customer_id}/do-not-contact",
        json={"actor": "客服A", "reason": "客户明确拒绝继续联系"},
    )

    unmark_response = client.post(
        f"/customers/{customer_id}/do-not-contact/cancel",
        json={"actor": "客服A", "actor_role": "customer_service", "reason": "尝试取消勿扰"},
    )

    assert unmark_response.status_code == 403
    assert "取消勿扰仅允许合规或管理员" in unmark_response.json()["detail"]


def test_customer_api_excludes_do_not_contact_from_outreach_and_ai_script_candidates() -> None:
    client = TestClient(app)
    included_id = asyncio.run(create_customer(f"{TEST_PREFIX}LEAD-002", CustomerGrade.B))
    excluded_id = asyncio.run(create_customer(f"{TEST_PREFIX}LEAD-003", CustomerGrade.C))

    client.post(
        f"/customers/{excluded_id}/do-not-contact",
        json={"actor": "客服A", "reason": "客户明确拒绝继续联系"},
    )

    outreach_response = client.get("/customers/outreach-candidates")
    ai_response = client.get("/customers/ai-script-candidates")

    assert outreach_response.status_code == 200
    assert ai_response.status_code == 200
    outreach_ids = {item["id"] for item in outreach_response.json()["items"]}
    ai_ids = {item["id"] for item in ai_response.json()["items"]}
    assert included_id in outreach_ids
    assert included_id in ai_ids
    assert excluded_id not in outreach_ids
    assert excluded_id not in ai_ids


def test_customer_api_records_rejected_outreach_and_marks_do_not_contact() -> None:
    client = TestClient(app)
    customer_id = asyncio.run(create_customer(f"{TEST_PREFIX}LEAD-004"))

    response = client.post(
        f"/customers/{customer_id}/outreach-records",
        json={
            "channel": "email",
            "status": "rejected",
            "sent_by": "客服A",
            "response_summary": "客户回复不要再联系",
            "next_action": "标记勿扰",
            "do_not_contact_reason": "客户明确拒绝继续联系",
            "external_id": f"{TEST_PREFIX}OUTREACH-001",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "rejected"
    assert payload["triggers_do_not_contact"] is True

    customer_response = client.get(f"/customers/{customer_id}")
    assert customer_response.status_code == 200
    customer = customer_response.json()
    assert customer["do_not_contact"] is True
    assert customer["status"] == "do_not_contact"
