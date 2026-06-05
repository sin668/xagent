import asyncio
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.db.session import AsyncSessionLocal
from app.main import app
from app.models import Customer, EmailMessage, EmailReplyDraft, EmailSendAttempt, EmailThread, OutreachRecord
from app.models.enums import (
    ContactMethodType,
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


client = TestClient(app)
TEST_PREFIX = "TEST-P5-E8-S5-"


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


async def seed_failed_attempt() -> dict[str, str]:
    result: dict[str, str] = {}
    async with AsyncSessionLocal() as async_session:
        def run(sync_session):
            customer = Customer(
                external_id=f"{TEST_PREFIX}{uuid4()}",
                name="Delivery Failure Dealer",
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
                subject="Delivery issue",
                status=EmailThreadStatus.OPEN,
                channel_account="sales@example.com",
            )
            sync_session.add(thread)
            sync_session.flush()
            inbound = EmailMessage(
                thread_id=thread.id,
                customer_id=customer.id,
                direction=EmailMessageDirection.INBOUND,
                from_email="delivery-buyer@example.ru",
                to_emails=["sales@example.com"],
                cc_emails=[],
                subject="Delivery issue",
                body_text="Need answer",
                language="en",
                status=EmailMessageStatus.PENDING_REPLY,
                source_type=EmailMessageSourceType.MAILBOX_SYNC,
            )
            sync_session.add(inbound)
            sync_session.flush()
            draft = EmailReplyDraft(
                thread_id=thread.id,
                message_id=inbound.id,
                customer_id=customer.id,
                detected_language="en",
                reply_language="en",
                language_confidence=0.95,
                ai_suggested_subject="Delivery issue",
                ai_suggested_body="Hello.",
                final_subject="Delivery issue",
                final_body="Hello.",
                knowledge_hits_json=[{"knowledge_item_id": str(uuid4()), "title": "FAQ"}],
                auto_send_allowed=False,
                auto_send_decision_json={"route": "manual_review"},
                manual_review_required=True,
                status=EmailReplyDraftStatus.FAILED,
            )
            sync_session.add(draft)
            sync_session.flush()
            outreach = OutreachRecord(
                customer_id=customer.id,
                channel=ContactMethodType.EMAIL,
                status=OutreachStatus.SENT,
                sent_by="AUTO_SEND",
                response_summary="发送失败：SMTP timeout",
                next_action="等待重试",
            )
            sync_session.add(outreach)
            sync_session.flush()
            attempt = EmailSendAttempt(
                reply_draft_id=draft.id,
                outreach_record_id=outreach.id,
                provider="fake",
                from_email="sales@example.com",
                to_emails=["delivery-buyer@example.ru"],
                cc_emails=[],
                bcc_emails=[],
                subject_snapshot="Delivery issue",
                body_text_snapshot="Hello.",
                status=EmailSendAttemptStatus.FAILED,
                attempt_count=1,
                error_code="timeout",
                error_message="SMTP timeout",
            )
            sync_session.add(attempt)
            sync_session.commit()
            result["customer_id"] = str(customer.id)
            result["draft_id"] = str(draft.id)
            result["attempt_id"] = str(attempt.id)
            result["outreach_id"] = str(outreach.id)

        await async_session.run_sync(run)
    return result


async def fetch_attempt_state(attempt_id: str) -> dict:
    state: dict = {}
    async with AsyncSessionLocal() as async_session:
        def run(sync_session):
            attempt = sync_session.scalar(select(EmailSendAttempt).where(EmailSendAttempt.id == attempt_id))
            outreach = sync_session.scalar(select(OutreachRecord).where(OutreachRecord.id == attempt.outreach_record_id))
            draft = sync_session.scalar(select(EmailReplyDraft).where(EmailReplyDraft.id == attempt.reply_draft_id))
            state["attempt_status"] = attempt.status.value
            state["attempt_count"] = attempt.attempt_count
            state["error_code"] = attempt.error_code
            state["error_message"] = attempt.error_message
            state["bounce_reason"] = attempt.bounce_reason
            state["outreach_status"] = outreach.status.value
            state["outreach_summary"] = outreach.response_summary
            state["outreach_next_action"] = outreach.next_action
            state["draft_status"] = draft.status.value

        await async_session.run_sync(run)
    return state


def setup_function() -> None:
    asyncio.run(cleanup_records())


def teardown_function() -> None:
    asyncio.run(cleanup_records())


def test_email_send_attempt_retry_records_attempt_count_and_outreach_history() -> None:
    seeded = asyncio.run(seed_failed_attempt())

    response = client.post(f"/email-send-attempts/{seeded['attempt_id']}/retry", json={"actor": "运营A"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "retry_pending"
    assert payload["attempt_count"] == 2
    assert payload["error_code"] is None
    assert payload["error_message"] is None

    state = asyncio.run(fetch_attempt_state(seeded["attempt_id"]))
    assert state["attempt_status"] == "retry_pending"
    assert state["attempt_count"] == 2
    assert state["outreach_status"] == "ready_for_manual_send"
    assert "重试" in state["outreach_summary"]
    assert state["outreach_next_action"] == "等待邮件重试"


def test_email_send_attempt_bounce_marks_bad_contact_and_quality_metrics() -> None:
    seeded = asyncio.run(seed_failed_attempt())

    response = client.post(
        f"/email-send-attempts/{seeded['attempt_id']}/bounce",
        json={"bounce_reason": "Mailbox unavailable", "actor": "mailbox-sync"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "bounced"
    assert payload["bounce_reason"] == "Mailbox unavailable"

    state = asyncio.run(fetch_attempt_state(seeded["attempt_id"]))
    assert state["attempt_status"] == "bounced"
    assert state["bounce_reason"] == "Mailbox unavailable"
    assert state["outreach_status"] == "bad_contact"
    assert "退信" in state["outreach_summary"]
    assert state["draft_status"] == "failed"

    metrics = client.get("/dashboard/email-delivery-quality")
    assert metrics.status_code == 200
    body = metrics.json()
    assert body["total_send_attempts"] == 1
    assert body["failed_count"] == 0
    assert body["bounced_count"] == 1
    assert body["bounce_rate"] == 1.0
