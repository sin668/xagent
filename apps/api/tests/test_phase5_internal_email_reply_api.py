import asyncio
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import delete, select

from app.db.session import AsyncSessionLocal
from app.main import app
from app.models import Customer, EmailMessage, EmailThread, OutreachRecord
from app.models.enums import (
    ContactMethodType,
    CustomerGrade,
    CustomerStatus,
    CustomerType,
    EmailMessageDirection,
    EmailMessageSourceType,
    EmailMessageStatus,
    EmailThreadStatus,
    OutreachStatus,
)
from app.settings import settings


TEST_PREFIX = "TEST-P5-E7-S2-"
INTERNAL_API_KEY = "test-internal-agent-key"
client = TestClient(app)


async def cleanup_records() -> None:
    async with AsyncSessionLocal() as async_session:
        def run(sync_session):
            customer_ids = sync_session.scalars(
                select(Customer.id).where(Customer.external_id.like(f"{TEST_PREFIX}%"))
            ).all()
            if customer_ids:
                sync_session.execute(delete(OutreachRecord).where(OutreachRecord.customer_id.in_(customer_ids)))
                sync_session.execute(delete(EmailMessage).where(EmailMessage.customer_id.in_(customer_ids)))
                sync_session.execute(delete(EmailThread).where(EmailThread.customer_id.in_(customer_ids)))
            sync_session.execute(delete(Customer).where(Customer.external_id.like(f"{TEST_PREFIX}%")))
            sync_session.commit()

        await async_session.run_sync(run)


async def seed_email_context() -> dict[str, str]:
    result: dict[str, str] = {}
    async with AsyncSessionLocal() as async_session:
        def run(sync_session):
            customer = Customer(
                external_id=f"{TEST_PREFIX}{uuid4()}",
                name="Moscow Internal Context Dealer",
                country="Russia",
                city="Moscow",
                customer_type=CustomerType.LOCAL_DEALER_SECONDARY_DEALER,
                grade=CustomerGrade.B,
                status=CustomerStatus.READY_FOR_SALES,
                do_not_contact=False,
            )
            sync_session.add(customer)
            sync_session.flush()
            thread = EmailThread(
                customer_id=customer.id,
                subject="Need Toyota cars",
                status=EmailThreadStatus.OPEN,
                channel_account="sales@example.com",
            )
            sync_session.add(thread)
            sync_session.flush()
            message = EmailMessage(
                thread_id=thread.id,
                customer_id=customer.id,
                direction=EmailMessageDirection.INBOUND,
                from_email="dealer@example.ru",
                to_emails=["sales@example.com"],
                subject="Need Toyota cars",
                body_text="Need Toyota Land Cruiser options",
                language="en",
                status=EmailMessageStatus.PENDING_REPLY,
                source_type=EmailMessageSourceType.MAILBOX_SYNC,
            )
            outreach = OutreachRecord(
                customer_id=customer.id,
                channel=ContactMethodType.EMAIL,
                status=OutreachStatus.SENT,
                sent_by="销售A",
                response_summary="首次触达已发送",
                next_action="等待回复",
            )
            sync_session.add_all([message, outreach])
            sync_session.commit()
            result["customer_id"] = str(customer.id)
            result["thread_id"] = str(thread.id)
            result["message_id"] = str(message.id)

        await async_session.run_sync(run)
    return result


@pytest.fixture(autouse=True)
def isolated_internal_email_reply_records():
    original_key = settings.agents_api_key
    settings.agents_api_key = SecretStr(INTERNAL_API_KEY)
    asyncio.run(cleanup_records())
    yield
    asyncio.run(cleanup_records())
    settings.agents_api_key = original_key


def test_internal_email_reply_context_requires_agent_api_key() -> None:
    seeded = asyncio.run(seed_email_context())

    response = client.post(
        "/internal/email-reply/context",
        json={
            "schema_version": "email-reply-v1",
            "request_id": str(uuid4()),
            "thread_id": seeded["thread_id"],
            "message_id": seeded["message_id"],
            "customer_id": seeded["customer_id"],
            "context": {},
            "prompt": {},
            "options": {},
        },
    )

    assert response.status_code == 401
    assert "Invalid or missing agents API key" in response.json()["detail"]


def test_internal_email_reply_context_loads_business_context_for_agent() -> None:
    seeded = asyncio.run(seed_email_context())

    response = client.post(
        "/internal/email-reply/context",
        headers={"X-Agents-Api-Key": INTERNAL_API_KEY},
        json={
            "schema_version": "email-reply-v1",
            "request_id": str(uuid4()),
            "thread_id": seeded["thread_id"],
            "message_id": seeded["message_id"],
            "customer_id": seeded["customer_id"],
            "context": {},
            "prompt": {"version": "email-reply-v3"},
            "options": {"language": "en"},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["customer"]["name"] == "Moscow Internal Context Dealer"
    assert payload["inbound_message"]["body_text"] == "Need Toyota Land Cruiser options"
    assert payload["recent_outreach_history"][0]["response_summary"] == "首次触达已发送"
    assert payload["audit_summary"]["sensitive_data_policy"].startswith("只包含邮件回复所需")


def test_internal_email_reply_knowledge_requires_agent_api_key() -> None:
    response = client.post(
        "/internal/email-reply/knowledge",
        json={
            "query": "logistics",
            "language": "ru",
            "channel": "email",
            "content_types": ["qa_entry"],
            "auto_send_candidate": True,
            "limit": 5,
        },
    )

    assert response.status_code == 401
