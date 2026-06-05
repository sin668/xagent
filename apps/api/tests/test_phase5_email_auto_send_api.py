import asyncio
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.db.session import AsyncSessionLocal
from app.main import app
from app.models import Customer, EmailMessage, EmailReplyDraft, EmailSendAttempt, EmailThread, OutreachRecord
from app.models.enums import (
    CustomerGrade,
    CustomerStatus,
    CustomerType,
    EmailMessageDirection,
    EmailMessageSourceType,
    EmailMessageStatus,
    EmailReplyDraftStatus,
    EmailSendAttemptStatus,
    EmailThreadStatus,
)
from app.services.email_reply_auto_send import AUTO_SEND_ELIGIBILITY_RULE_VERSION
from app.settings import settings


client = TestClient(app)
TEST_PREFIX = "TEST-P5-E8-S4-"


async def cleanup_records() -> None:
    async with AsyncSessionLocal() as async_session:
        def run(sync_session):
            customer_ids = sync_session.scalars(select(Customer.id).where(Customer.external_id.like(f"{TEST_PREFIX}%"))).all()
            if customer_ids:
                draft_ids = sync_session.scalars(select(EmailReplyDraft.id).where(EmailReplyDraft.customer_id.in_(customer_ids))).all()
                if draft_ids:
                    sync_session.execute(delete(EmailSendAttempt).where(EmailSendAttempt.reply_draft_id.in_(draft_ids)))
                sync_session.execute(delete(OutreachRecord).where(OutreachRecord.customer_id.in_(customer_ids)))
                sync_session.execute(delete(EmailReplyDraft).where(EmailReplyDraft.customer_id.in_(customer_ids)))
                sync_session.execute(delete(EmailMessage).where(EmailMessage.customer_id.in_(customer_ids)))
                sync_session.execute(delete(EmailThread).where(EmailThread.customer_id.in_(customer_ids)))
            sync_session.execute(delete(Customer).where(Customer.external_id.like(f"{TEST_PREFIX}%")))
            sync_session.commit()

        await async_session.run_sync(run)


async def seed_auto_send_draft(*, eligible: bool = True) -> str:
    result: dict[str, str] = {}
    async with AsyncSessionLocal() as async_session:
        def run(sync_session):
            customer = Customer(
                external_id=f"{TEST_PREFIX}{uuid4()}",
                name="Auto Send Dealer",
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
                subject="Auto send inquiry",
                status=EmailThreadStatus.OPEN,
                channel_account="sales@example.com",
            )
            sync_session.add(thread)
            sync_session.flush()
            message = EmailMessage(
                thread_id=thread.id,
                customer_id=customer.id,
                direction=EmailMessageDirection.INBOUND,
                from_email="auto-buyer@example.ru",
                to_emails=["sales@example.com"],
                cc_emails=[],
                subject="Auto send inquiry",
                body_text="Need FAQ answer",
                language="en",
                status=EmailMessageStatus.PENDING_REPLY,
                source_type=EmailMessageSourceType.MAILBOX_SYNC,
            )
            sync_session.add(message)
            sync_session.flush()
            reasons = [
                "whitelisted_customer",
                "fixed_faq",
                "first_touch",
                "low_risk_scene",
                "knowledge_auto_reply_allowed",
                "knowledge_embedding_ready",
                "reply_language_confident",
            ]
            decision_json = {
                "rule_version": AUTO_SEND_ELIGIBILITY_RULE_VERSION,
                "route": "auto_send_candidate" if eligible else "hold_for_manual_review",
                "auto_send_allowed": eligible,
                "manual_review_required": not eligible,
                "manual_review_reason": None if eligible else "未满足自动发送准入条件，进入人工确认。",
                "reasons": reasons if eligible else ["not_whitelisted_customer", "fixed_faq", "first_touch"],
            }
            draft = EmailReplyDraft(
                thread_id=thread.id,
                message_id=message.id,
                customer_id=customer.id,
                detected_language="en",
                reply_language="en",
                language_confidence=0.95,
                ai_suggested_subject="FAQ answer",
                ai_suggested_body="Hello, this is a low-risk FAQ answer.",
                final_subject=None,
                final_body=None,
                knowledge_hits_json=[
                    {
                        "knowledge_item_id": str(uuid4()),
                        "title": "Published fixed FAQ",
                        "content_type": "qa_entry",
                        "business_scene": "fixed_faq",
                        "risk_level": "low",
                        "auto_reply_allowed": True,
                        "embedding_status": "ready",
                        "evidence_note": "FAQ evidence",
                    }
                ],
                auto_send_allowed=eligible,
                auto_send_decision_json=decision_json,
                manual_review_required=not eligible,
                manual_review_reason=None if eligible else "未满足自动发送准入条件，进入人工确认。",
                status=EmailReplyDraftStatus.DRAFTED,
            )
            sync_session.add(draft)
            sync_session.commit()
            result["draft_id"] = str(draft.id)

        await async_session.run_sync(run)
    return result["draft_id"]


async def fetch_auto_send_state(draft_id: str) -> dict:
    state: dict = {}
    async with AsyncSessionLocal() as async_session:
        def run(sync_session):
            draft = sync_session.scalar(select(EmailReplyDraft).where(EmailReplyDraft.id == draft_id))
            attempts = sync_session.scalars(select(EmailSendAttempt).where(EmailSendAttempt.reply_draft_id == draft_id)).all()
            state["draft_status"] = draft.status.value
            state["final_subject"] = draft.final_subject
            state["final_body"] = draft.final_body
            state["attempt_count"] = len(attempts)
            state["attempt_status"] = attempts[0].status.value if attempts else None
            state["attempt_provider"] = attempts[0].provider if attempts else None
            state["decision_json"] = draft.auto_send_decision_json

        await async_session.run_sync(run)
    return state


def setup_function() -> None:
    asyncio.run(cleanup_records())


def teardown_function() -> None:
    asyncio.run(cleanup_records())


def test_whitelist_low_risk_auto_send_api_sends_and_records_rule_evidence() -> None:
    original_provider = settings.email_sender_provider
    original_from = settings.email_sender_from_email
    settings.email_sender_provider = "fake"
    settings.email_sender_from_email = "sales@example.com"
    try:
        draft_id = asyncio.run(seed_auto_send_draft())
        response = client.post(f"/email-replies/{draft_id}/auto-send")
    finally:
        settings.email_sender_provider = original_provider
        settings.email_sender_from_email = original_from

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == draft_id
    assert payload["auto_send_check"]["decision"] == "auto_send_allowed"
    assert payload["ai_audit"]["send_triggered"] is True

    state = asyncio.run(fetch_auto_send_state(draft_id))
    assert state["draft_status"] == "sent"
    assert state["final_subject"] == "FAQ answer"
    assert state["final_body"] == "Hello, this is a low-risk FAQ answer."
    assert state["attempt_count"] == 1
    assert state["attempt_status"] == EmailSendAttemptStatus.SENT.value
    assert state["attempt_provider"] == "fake"
    assert state["decision_json"]["rule_version"] == AUTO_SEND_ELIGIBILITY_RULE_VERSION
    assert "whitelisted_customer" in state["decision_json"]["auto_send_trace"]["eligibility_reasons"]
    assert state["decision_json"]["auto_send_trace"]["knowledge_evidence"][0]["title"] == "Published fixed FAQ"


def test_auto_send_api_routes_uncertain_or_manual_review_draft_without_sending() -> None:
    original_from = settings.email_sender_from_email
    settings.email_sender_from_email = "sales@example.com"
    try:
        draft_id = asyncio.run(seed_auto_send_draft(eligible=False))
        response = client.post(f"/email-replies/{draft_id}/auto-send")
    finally:
        settings.email_sender_from_email = original_from

    assert response.status_code == 400
    assert "人工复核" in response.json()["detail"]
    state = asyncio.run(fetch_auto_send_state(draft_id))
    assert state["draft_status"] == "drafted"
    assert state["attempt_count"] == 0
