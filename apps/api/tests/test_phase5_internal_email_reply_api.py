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


def test_internal_email_reply_auto_send_check_requires_agent_api_key() -> None:
    response = client.post(
        "/internal/email-reply/auto-send-check",
        json={
            "schema_version": "email-reply-v1",
            "request_id": str(uuid4()),
            "thread_id": str(uuid4()),
            "message_id": str(uuid4()),
            "draft_id": str(uuid4()),
            "output": {
                "schema_version": "email-reply-v1",
                "reply_language": "ru",
                "detected_language": "ru",
                "suggested_subject": "Toyota sourcing",
                "suggested_body": "Здравствуйте.",
                "knowledge_hits": [],
                "risk_flags": [],
                "auto_send_allowed": True,
                "manual_review_required": False,
                "next_action": "auto_send_candidate",
                "audit": {"writes_core_tables": False},
            },
            "context": {},
            "knowledge_hits": [],
            "options": {},
            "dry_run": True,
        },
    )

    assert response.status_code == 401


def test_internal_email_reply_auto_send_check_returns_apps_api_rule_decision() -> None:
    response = client.post(
        "/internal/email-reply/auto-send-check",
        headers={"X-Agents-Api-Key": INTERNAL_API_KEY},
        json={
            "schema_version": "email-reply-v1",
            "request_id": str(uuid4()),
            "thread_id": str(uuid4()),
            "message_id": str(uuid4()),
            "draft_id": str(uuid4()),
            "output": {
                "schema_version": "email-reply-v1",
                "reply_language": "ru",
                "detected_language": "ru",
                "suggested_subject": "Toyota sourcing",
                "suggested_body": "Здравствуйте.",
                "knowledge_hits": [
                    {
                        "knowledge_item_id": str(uuid4()),
                        "title": "Fixed FAQ",
                        "version": "v1",
                        "similarity_score": 0.95,
                        "evidence_note": "Approved FAQ wording.",
                    }
                ],
                "risk_flags": [],
                "auto_send_allowed": True,
                "manual_review_required": False,
                "next_action": "auto_send_candidate",
                "audit": {"writes_core_tables": False},
            },
            "context": {
                "customer": {
                    "is_whitelisted": True,
                    "grade": "A",
                    "status": "ready_for_sales",
                    "do_not_contact": False,
                },
                "inbound_message": {
                    "risk_flags": [],
                    "sensitive_topics": [],
                    "language": "ru",
                },
            },
            "knowledge_hits": [
                {
                    "knowledge_item_id": str(uuid4()),
                    "title": "Fixed FAQ",
                    "version": "v1",
                    "similarity_score": 0.95,
                    "evidence_note": "Approved FAQ wording.",
                    "content_type": "qa_entry",
                    "business_scene": "fixed_faq",
                    "risk_level": "low",
                    "auto_reply_allowed": True,
                    "embedding_status": "ready",
                }
            ],
            "options": {
                "business_scene": "fixed_faq",
                "scene_risk_level": "low",
                "is_first_touch": True,
                "reply_language_confident": True,
                "channel_risk_level": "low",
            },
            "dry_run": True,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["route"] == "auto_send"
    assert payload["auto_send_allowed"] is True
    assert payload["manual_review_required"] is False
    assert payload["dry_run"] is True
    assert payload["send_triggered"] is False
    assert "whitelisted_customer" in payload["reasons"]
