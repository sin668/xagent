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
    OutreachStatus,
)
from app.settings import settings


client = TestClient(app)
TEST_PREFIX = "TEST-P5-E8-S3-"


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


async def seed_reply_draft(*, blocked: bool = False) -> str:
    result: dict[str, str] = {}
    async with AsyncSessionLocal() as async_session:
        def run(sync_session):
            customer = Customer(
                external_id=f"{TEST_PREFIX}{uuid4()}",
                name="Manual Send Dealer",
                country="Russia",
                city="Moscow",
                customer_type=CustomerType.LOCAL_DEALER_SECONDARY_DEALER,
                grade=CustomerGrade.WATCH if blocked else CustomerGrade.B,
                status=CustomerStatus.WATCH if blocked else CustomerStatus.READY_FOR_SALES,
                do_not_contact=False,
            )
            sync_session.add(customer)
            sync_session.flush()
            thread = EmailThread(
                customer_id=customer.id,
                subject="Manual send inquiry",
                status=EmailThreadStatus.OPEN,
                channel_account="sales@example.com",
            )
            sync_session.add(thread)
            sync_session.flush()
            message = EmailMessage(
                thread_id=thread.id,
                customer_id=customer.id,
                direction=EmailMessageDirection.INBOUND,
                from_email="manual-buyer@example.ru",
                to_emails=["sales@example.com"],
                cc_emails=[],
                subject="Manual send inquiry",
                body_text="Need cars",
                language="en",
                status=EmailMessageStatus.PENDING_REPLY,
                source_type=EmailMessageSourceType.MAILBOX_SYNC,
            )
            sync_session.add(message)
            sync_session.flush()
            decision_json = {
                "route": "blocked",
                "hard_blocked": True,
                "auto_send_allowed": False,
                "manual_review_required": True,
                "block_reasons": [{"code": "customer_de_grade", "message": "D/E 级客户不得发送。"}],
            } if blocked else {
                "route": "auto_send_candidate",
                "auto_send_allowed": True,
                "manual_review_required": False,
                "reasons": ["whitelisted_customer", "fixed_faq", "low_risk_scene"],
            }
            draft = EmailReplyDraft(
                thread_id=thread.id,
                message_id=message.id,
                customer_id=customer.id,
                detected_language="en",
                reply_language="en",
                language_confidence=0.94,
                ai_suggested_subject="AI subject",
                ai_suggested_body="AI suggested body",
                final_subject=None,
                final_body=None,
                knowledge_hits_json=[] if blocked else [{"knowledge_item_id": str(uuid4()), "title": "FAQ"}],
                auto_send_allowed=not blocked,
                auto_send_decision_json=decision_json,
                manual_review_required=blocked,
                manual_review_reason="命中硬拦截规则，禁止自动发送。" if blocked else None,
                status=EmailReplyDraftStatus.BLOCKED if blocked else EmailReplyDraftStatus.PENDING_REVIEW,
            )
            sync_session.add(draft)
            sync_session.commit()
            result["draft_id"] = str(draft.id)

        await async_session.run_sync(run)
    return result["draft_id"]


async def fetch_send_state(draft_id: str) -> dict:
    state: dict = {}
    async with AsyncSessionLocal() as async_session:
        def run(sync_session):
            draft = sync_session.scalar(select(EmailReplyDraft).where(EmailReplyDraft.id == draft_id))
            attempts = sync_session.scalars(select(EmailSendAttempt).where(EmailSendAttempt.reply_draft_id == draft_id)).all()
            outreach = sync_session.scalar(select(OutreachRecord).where(OutreachRecord.id == draft.sent_record_id))
            state["draft_status"] = draft.status.value
            state["final_subject"] = draft.final_subject
            state["final_body"] = draft.final_body
            state["reviewed_by"] = draft.reviewed_by
            state["reviewed_at"] = draft.reviewed_at.isoformat() if draft.reviewed_at else None
            state["sent_record_id"] = str(draft.sent_record_id) if draft.sent_record_id else None
            state["attempt_count"] = len(attempts)
            state["attempt_status"] = attempts[0].status.value if attempts else None
            state["attempt_provider"] = attempts[0].provider if attempts else None
            state["attempt_to_emails"] = attempts[0].to_emails if attempts else []
            state["outreach_status"] = outreach.status.value if outreach else None
            state["outreach_sent_by"] = outreach.sent_by if outreach else None

        await async_session.run_sync(run)
    return state


def setup_function() -> None:
    asyncio.run(cleanup_records())


def teardown_function() -> None:
    asyncio.run(cleanup_records())


def test_manual_confirm_send_api_sends_and_records_attempt_outreach_and_draft() -> None:
    original_provider = settings.email_sender_provider
    original_from = settings.email_sender_from_email
    settings.email_sender_provider = "fake"
    settings.email_sender_from_email = "sales@example.com"
    try:
        draft_id = asyncio.run(seed_reply_draft())
        response = client.post(
            f"/email-replies/{draft_id}/confirm-send",
            json={
                "actor": "销售B",
                "review_note": "人工确认首封回复",
                "manual_confirmed": True,
                "final_subject": "Human subject",
                "final_body": "Human reviewed body",
            },
        )
    finally:
        settings.email_sender_provider = original_provider
        settings.email_sender_from_email = original_from

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == draft_id
    assert payload["reply_draft"]["subject"] == "Human subject"
    assert payload["reply_draft"]["body"] == "Human reviewed body"
    assert payload["auto_send_check"]["decision"] == "auto_send_allowed"

    state = asyncio.run(fetch_send_state(draft_id))
    assert state["draft_status"] == "sent"
    assert state["final_subject"] == "Human subject"
    assert state["final_body"] == "Human reviewed body"
    assert state["reviewed_by"] == "销售B"
    assert state["reviewed_at"] is not None
    assert state["sent_record_id"] is not None
    assert state["attempt_count"] == 1
    assert state["attempt_status"] == EmailSendAttemptStatus.SENT.value
    assert state["attempt_provider"] == "fake"
    assert state["attempt_to_emails"] == ["manual-buyer@example.ru"]
    assert state["outreach_status"] == OutreachStatus.SENT.value
    assert state["outreach_sent_by"] == "销售B"


def test_manual_confirm_send_api_blocks_hard_blocked_preview_before_sending() -> None:
    original_from = settings.email_sender_from_email
    settings.email_sender_from_email = "sales@example.com"
    try:
        draft_id = asyncio.run(seed_reply_draft(blocked=True))
        response = client.post(
            f"/email-replies/{draft_id}/confirm-send",
            json={
                "actor": "销售B",
                "manual_confirmed": True,
                "final_subject": "Human subject",
                "final_body": "Human reviewed body",
            },
        )
    finally:
        settings.email_sender_from_email = original_from

    assert response.status_code == 400
    assert "禁止发送" in response.json()["detail"]
    state = asyncio.run(fetch_send_state(draft_id))
    assert state["draft_status"] == "blocked"
    assert state["attempt_count"] == 0
