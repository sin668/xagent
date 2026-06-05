import asyncio
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.db.session import AsyncSessionLocal
from app.main import app
from app.models import Customer, EmailMessage, EmailReplyDraft, EmailThread
from app.models.enums import (
    CustomerGrade,
    CustomerStatus,
    CustomerType,
    EmailMessageDirection,
    EmailMessageSourceType,
    EmailMessageStatus,
    EmailReplyDraftStatus,
    EmailThreadStatus,
)
from app.settings import settings


client = TestClient(app)
TEST_PREFIX = "TEST-P5-E8-S2-"


async def cleanup_records() -> None:
    async with AsyncSessionLocal() as async_session:
        def run(sync_session):
            customer_ids = sync_session.scalars(select(Customer.id).where(Customer.external_id.like(f"{TEST_PREFIX}%"))).all()
            if customer_ids:
                sync_session.execute(delete(EmailReplyDraft).where(EmailReplyDraft.customer_id.in_(customer_ids)))
                sync_session.execute(delete(EmailMessage).where(EmailMessage.customer_id.in_(customer_ids)))
                sync_session.execute(delete(EmailThread).where(EmailThread.customer_id.in_(customer_ids)))
            sync_session.execute(delete(Customer).where(Customer.external_id.like(f"{TEST_PREFIX}%")))
            sync_session.commit()

        await async_session.run_sync(run)


async def seed_send_preview_draft() -> str:
    result: dict[str, str] = {}
    async with AsyncSessionLocal() as async_session:
        def run(sync_session):
            customer = Customer(
                external_id=f"{TEST_PREFIX}{uuid4()}",
                name="Moscow Email Preview Dealer",
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
                subject="Toyota Prado inquiry",
                status=EmailThreadStatus.OPEN,
                channel_account="sales@example.com",
            )
            sync_session.add(thread)
            sync_session.flush()
            message = EmailMessage(
                thread_id=thread.id,
                customer_id=customer.id,
                direction=EmailMessageDirection.INBOUND,
                from_email="buyer-preview@example.ru",
                to_emails=["sales@example.com"],
                cc_emails=[],
                subject="Toyota Prado inquiry",
                body_text="Need Toyota Prado options",
                language="en",
                status=EmailMessageStatus.PENDING_REPLY,
                source_type=EmailMessageSourceType.MAILBOX_SYNC,
            )
            sync_session.add(message)
            sync_session.flush()
            draft = EmailReplyDraft(
                thread_id=thread.id,
                message_id=message.id,
                customer_id=customer.id,
                detected_language="en",
                reply_language="en",
                language_confidence=0.93,
                ai_suggested_subject="Re: Toyota Prado inquiry",
                ai_suggested_body="Hello, we can prepare suitable Toyota Prado options.",
                final_subject="Re: Toyota Prado inquiry",
                final_body="Hello, we can prepare suitable Toyota Prado options and next steps.",
                knowledge_hits_json=[
                    {
                        "knowledge_item_id": str(uuid4()),
                        "title": "First reply FAQ",
                        "similarity_score": 0.9,
                        "auto_reply_allowed": True,
                    }
                ],
                auto_send_allowed=True,
                auto_send_decision_json={
                    "route": "auto_send_candidate",
                    "auto_send_allowed": True,
                    "manual_review_required": False,
                    "reasons": ["whitelisted_customer", "fixed_faq", "first_touch", "low_risk_scene"],
                },
                manual_review_required=False,
                status=EmailReplyDraftStatus.DRAFTED,
            )
            sync_session.add(draft)
            sync_session.commit()
            result["draft_id"] = str(draft.id)

        await async_session.run_sync(run)
    return result["draft_id"]


def setup_function() -> None:
    asyncio.run(cleanup_records())


def teardown_function() -> None:
    asyncio.run(cleanup_records())


def test_email_replies_list_contract_returns_real_empty_queue_before_models_land() -> None:
    response = client.get("/email-replies?limit=50&decision=manual_review")

    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0}


def test_email_reply_detail_and_actions_return_404_without_uuid_validation() -> None:
    for method, path in [
        ("GET", "/email-replies/reply-seed-slug"),
        ("POST", "/email-replies/reply-seed-slug/send-preview"),
        ("POST", "/email-replies/reply-seed-slug/confirm-send"),
        ("POST", "/email-replies/reply-seed-slug/reject"),
    ]:
        payload = {"actor": "ops-anna", "review_note": "mobile check", "manual_confirmed": True}
        response = client.request(method, path, json=payload if method == "POST" else None)

        assert response.status_code == 404
        assert response.status_code != 422


def test_email_replies_api_is_registered_in_openapi() -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/email-replies" in paths
    assert "/email-replies/{reply_id}" in paths
    assert "/email-replies/{reply_id}/send-preview" in paths
    assert "/email-replies/{reply_id}/confirm-send" in paths
    assert "/email-replies/{reply_id}/reject" in paths


def test_email_send_preview_api_returns_real_preview_without_sending() -> None:
    original_from = settings.email_sender_from_email
    settings.email_sender_from_email = "sales@example.com"
    try:
        draft_id = asyncio.run(seed_send_preview_draft())

        response = client.post(f"/email-replies/{draft_id}/send-preview")
    finally:
        settings.email_sender_from_email = original_from

    assert response.status_code == 200
    payload = response.json()
    assert payload["reply_id"] == draft_id
    assert payload["decision"] == "auto_send_allowed"
    assert payload["allow_auto_send"] is True
    assert payload["send_triggered"] is False
    assert payload["from_email"] == "sales@example.com"
    assert payload["to_emails"] == ["buyer-preview@example.ru"]
    assert payload["subject"] == "Re: Toyota Prado inquiry"
    assert payload["knowledge_hit_count"] == 1
    assert payload["hard_blocks"] == []
