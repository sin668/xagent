from datetime import datetime

import pytest
import pytest_asyncio
from sqlalchemy import delete, select

from app.db.session import AsyncSessionLocal
from app.models import Customer, OutreachRecord
from app.models.enums import ContactMethodType, CustomerGrade, CustomerStatus, CustomerType, OutreachStatus
from app.services.customer_dnc import CustomerDncService


TEST_PREFIX = "TEST-E6S2-"


async def cleanup_test_records() -> None:
    async with AsyncSessionLocal() as async_session:
        customer_ids = (
            await async_session.execute(select(Customer.id).where(Customer.external_id.like(f"{TEST_PREFIX}%")))
        ).scalars().all()
        if customer_ids:
            await async_session.execute(delete(OutreachRecord).where(OutreachRecord.customer_id.in_(customer_ids)))
        await async_session.execute(delete(Customer).where(Customer.external_id.like(f"{TEST_PREFIX}%")))
        await async_session.commit()


async def run_with_session(callback):
    async with AsyncSessionLocal() as async_session:
        result = await async_session.run_sync(callback)
        await async_session.commit()
        return result


@pytest_asyncio.fixture(autouse=True)
async def isolated_dnc_records():
    await cleanup_test_records()
    yield
    await cleanup_test_records()


def create_customer(session, external_id: str, *, grade=CustomerGrade.B, status=CustomerStatus.READY_FOR_CUSTOMER_SERVICE) -> Customer:
    customer = Customer(
        external_id=external_id,
        name=f"{external_id} Dealer",
        country="Russia",
        city="Moscow",
        customer_type=CustomerType.LOCAL_DEALER_SECONDARY_DEALER,
        grade=grade,
        status=status,
        do_not_contact=False,
    )
    session.add(customer)
    session.flush()
    return customer


@pytest.mark.asyncio
async def test_mark_do_not_contact_records_actor_time_reason_and_status() -> None:
    def act(session):
        customer = create_customer(session, f"{TEST_PREFIX}LEAD-001")
        service = CustomerDncService(session)
        updated = service.mark_do_not_contact(
            customer_id=customer.id,
            marked_by="客服A",
            reason="客户明确拒绝继续联系",
        )
        return updated

    updated = await run_with_session(act)

    assert updated.do_not_contact is True
    assert updated.do_not_contact_reason == "客户明确拒绝继续联系"
    assert updated.do_not_contact_marked_by == "客服A"
    assert updated.do_not_contact_marked_at is not None
    assert updated.status == CustomerStatus.DO_NOT_CONTACT


@pytest.mark.asyncio
async def test_unmark_do_not_contact_requires_reason_and_records_actor() -> None:
    def act(session):
        customer = create_customer(session, f"{TEST_PREFIX}LEAD-002", status=CustomerStatus.DO_NOT_CONTACT)
        customer.do_not_contact = True
        customer.do_not_contact_reason = "客户误标记"
        customer.do_not_contact_marked_by = "客服A"
        customer.do_not_contact_marked_at = datetime.utcnow()
        service = CustomerDncService(session)
        try:
            service.unmark_do_not_contact(customer_id=customer.id, unmarked_by="主管B", reason="")
        except ValueError as exc:
            empty_reason_error = str(exc)
        updated = service.unmark_do_not_contact(customer_id=customer.id, unmarked_by="主管B", reason="客户重新同意沟通")
        return empty_reason_error, updated

    empty_reason_error, updated = await run_with_session(act)

    assert "取消勿扰需要记录原因" in empty_reason_error
    assert updated.do_not_contact is False
    assert updated.do_not_contact_reason == "取消勿扰：客户重新同意沟通"
    assert updated.do_not_contact_marked_by == "主管B"
    assert updated.do_not_contact_marked_at is not None
    assert updated.status == CustomerStatus.PENDING_REVIEW


@pytest.mark.asyncio
async def test_do_not_contact_customers_are_excluded_from_outreach_queue_and_ai_script_tasks() -> None:
    def act(session):
        included = create_customer(session, f"{TEST_PREFIX}LEAD-003", grade=CustomerGrade.B)
        excluded = create_customer(session, f"{TEST_PREFIX}LEAD-004", grade=CustomerGrade.C)
        excluded.do_not_contact = True
        excluded.status = CustomerStatus.DO_NOT_CONTACT
        service = CustomerDncService(session)
        outreach_ids = [customer.external_id for customer in service.list_outreach_candidates()]
        ai_ids = [customer.external_id for customer in service.list_ai_script_candidates()]
        return included.external_id, excluded.external_id, outreach_ids, ai_ids

    included_id, excluded_id, outreach_ids, ai_ids = await run_with_session(act)

    assert included_id in outreach_ids
    assert included_id in ai_ids
    assert excluded_id not in outreach_ids
    assert excluded_id not in ai_ids


@pytest.mark.asyncio
async def test_rejected_outreach_record_links_customer_to_do_not_contact() -> None:
    def act(session):
        customer = create_customer(session, f"{TEST_PREFIX}LEAD-005")
        service = CustomerDncService(session)
        outreach = service.record_outreach_result(
            customer_id=customer.id,
            channel=ContactMethodType.EMAIL.value,
            status=OutreachStatus.REJECTED.value,
            sent_by="客服A",
            response_summary="客户回复不要再联系",
            next_action="标记勿扰",
            do_not_contact_reason="客户明确拒绝继续联系",
            external_id=f"{TEST_PREFIX}OUTREACH-001",
        )
        session.flush()
        refreshed = session.scalar(select(Customer).where(Customer.id == customer.id))
        return outreach, refreshed

    outreach, customer = await run_with_session(act)

    assert outreach.status == OutreachStatus.REJECTED
    assert outreach.triggers_do_not_contact is True
    assert customer.do_not_contact is True
    assert customer.do_not_contact_reason == "客户明确拒绝继续联系"
    assert customer.status == CustomerStatus.DO_NOT_CONTACT
