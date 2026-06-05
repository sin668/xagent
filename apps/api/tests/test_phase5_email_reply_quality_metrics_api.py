import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
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
TEST_PREFIX = "TEST-P5-E9-S2-"


async def cleanup_records() -> None:
    async with AsyncSessionLocal() as async_session:
        def run(sync_session):
            customer_ids = sync_session.scalars(
                select(Customer.id).where(Customer.external_id.like(f"{TEST_PREFIX}%"))
            ).all()
            if customer_ids:
                draft_ids = sync_session.scalars(
                    select(EmailReplyDraft.id).where(EmailReplyDraft.customer_id.in_(customer_ids))
                ).all()
                if draft_ids:
                    sync_session.execute(delete(EmailSendAttempt).where(EmailSendAttempt.reply_draft_id.in_(draft_ids)))
                sync_session.execute(delete(OutreachRecord).where(OutreachRecord.customer_id.in_(customer_ids)))
                sync_session.execute(delete(EmailReplyDraft).where(EmailReplyDraft.customer_id.in_(customer_ids)))
                sync_session.execute(delete(EmailMessage).where(EmailMessage.customer_id.in_(customer_ids)))
                sync_session.execute(delete(EmailThread).where(EmailThread.customer_id.in_(customer_ids)))
            sync_session.execute(delete(Customer).where(Customer.external_id.like(f"{TEST_PREFIX}%")))
            sync_session.commit()

        await async_session.run_sync(run)


def setup_function() -> None:
    asyncio.run(cleanup_records())


def teardown_function() -> None:
    asyncio.run(cleanup_records())


async def seed_email_reply_quality_records() -> None:
    now = datetime.now(UTC)
    async with AsyncSessionLocal() as async_session:
        def run(sync_session):
            customer = Customer(
                external_id=f"{TEST_PREFIX}{uuid4()}",
                name="Reply Quality Dealer",
                country="Russia",
                city="Moscow",
                customer_type=CustomerType.LOCAL_DEALER_SECONDARY_DEALER,
                grade=CustomerGrade.B,
                status=CustomerStatus.READY_FOR_SALES,
            )
            sync_session.add(customer)
            sync_session.flush()

            def make_thread(index: int) -> tuple[EmailThread, EmailMessage]:
                thread = EmailThread(
                    customer_id=customer.id,
                    subject=f"Quality thread {index}",
                    status=EmailThreadStatus.OPEN,
                    channel_account="sales@example.com",
                    created_at=now + timedelta(minutes=index),
                )
                sync_session.add(thread)
                sync_session.flush()
                inbound = EmailMessage(
                    thread_id=thread.id,
                    customer_id=customer.id,
                    direction=EmailMessageDirection.INBOUND,
                    from_email=f"buyer-{index}@example.ru",
                    to_emails=["sales@example.com"],
                    cc_emails=[],
                    subject=f"Question {index}",
                    body_text="Need vehicles",
                    language="ru",
                    status=EmailMessageStatus.PENDING_REPLY,
                    source_type=EmailMessageSourceType.MAILBOX_SYNC,
                    created_at=now + timedelta(minutes=index),
                )
                sync_session.add(inbound)
                sync_session.flush()
                return thread, inbound

            def make_draft(
                *,
                index: int,
                status: EmailReplyDraftStatus,
                ai_body: str,
                final_body: str | None,
                manual_review_required: bool,
                auto_send_allowed: bool,
                attempt_status: EmailSendAttemptStatus | None,
                reply_language: str = "ru",
                business_scene: str = "first_outreach",
                customer_replied: bool = False,
            ) -> None:
                thread, inbound = make_thread(index)
                draft_created_at = now + timedelta(minutes=index)
                draft = EmailReplyDraft(
                    thread_id=thread.id,
                    message_id=inbound.id,
                    customer_id=customer.id,
                    prompt_version="email-reply-quality-v1",
                    model="test-model",
                    detected_language=reply_language,
                    reply_language=reply_language,
                    language_confidence=0.96,
                    ai_suggested_subject=f"AI subject {index}",
                    ai_suggested_body=ai_body,
                    final_subject=f"Final subject {index}" if final_body is not None else None,
                    final_body=final_body,
                    knowledge_hits_json=[{"title": "FAQ", "version": "v1"}],
                    auto_send_allowed=auto_send_allowed,
                    auto_send_decision_json={"route": "auto_send" if auto_send_allowed else "manual_review", "business_scene": business_scene},
                    manual_review_required=manual_review_required,
                    status=status,
                    reviewed_by="operator" if manual_review_required and final_body is not None else None,
                    reviewed_at=draft_created_at + timedelta(minutes=1) if manual_review_required and final_body is not None else None,
                    created_at=draft_created_at,
                    updated_at=draft_created_at,
                )
                sync_session.add(draft)
                sync_session.flush()
                if attempt_status is not None:
                    outreach = OutreachRecord(
                        customer_id=customer.id,
                        channel=ContactMethodType.EMAIL,
                        status=OutreachStatus.SENT if attempt_status == EmailSendAttemptStatus.SENT else OutreachStatus.BAD_CONTACT,
                        sent_by="AUTO_SEND" if auto_send_allowed else "operator",
                        sent_at=draft_created_at + timedelta(minutes=2),
                        response_summary="sent",
                        next_action="等待客户回复",
                    )
                    sync_session.add(outreach)
                    sync_session.flush()
                    sync_session.add(
                        EmailSendAttempt(
                            reply_draft_id=draft.id,
                            outreach_record_id=outreach.id,
                            provider="fake",
                            from_email="sales@example.com",
                            to_emails=["buyer@example.ru"],
                            cc_emails=[],
                            bcc_emails=[],
                            subject_snapshot=draft.final_subject or draft.ai_suggested_subject or "",
                            body_text_snapshot=draft.final_body or draft.ai_suggested_body,
                            status=attempt_status,
                            attempt_count=1,
                            sent_at=draft_created_at + timedelta(minutes=2) if attempt_status == EmailSendAttemptStatus.SENT else None,
                            bounce_reason="mailbox unavailable" if attempt_status == EmailSendAttemptStatus.BOUNCED else None,
                            error_code="smtp_error" if attempt_status == EmailSendAttemptStatus.FAILED else None,
                            error_message="smtp failed" if attempt_status == EmailSendAttemptStatus.FAILED else None,
                        )
                    )
                if customer_replied:
                    sync_session.add(
                        EmailMessage(
                            thread_id=thread.id,
                            customer_id=customer.id,
                            direction=EmailMessageDirection.INBOUND,
                            from_email="buyer-reply@example.ru",
                            to_emails=["sales@example.com"],
                            cc_emails=[],
                            subject=f"Re: Question {index}",
                            body_text="Thanks, send details.",
                            language=reply_language,
                            status=EmailMessageStatus.RECEIVED,
                            source_type=EmailMessageSourceType.MAILBOX_SYNC,
                            created_at=draft_created_at + timedelta(hours=2),
                        )
                    )

            make_draft(
                index=1,
                status=EmailReplyDraftStatus.SENT,
                ai_body="Same accepted body",
                final_body="Same accepted body",
                manual_review_required=True,
                auto_send_allowed=False,
                attempt_status=EmailSendAttemptStatus.SENT,
                customer_replied=True,
            )
            make_draft(
                index=2,
                status=EmailReplyDraftStatus.SENT,
                ai_body="Short AI body",
                final_body="Longer safer human edited body",
                manual_review_required=True,
                auto_send_allowed=False,
                attempt_status=EmailSendAttemptStatus.SENT,
            )
            make_draft(
                index=3,
                status=EmailReplyDraftStatus.SENT,
                ai_body="Auto body",
                final_body="Auto body",
                manual_review_required=False,
                auto_send_allowed=True,
                attempt_status=EmailSendAttemptStatus.SENT,
            )
            make_draft(
                index=4,
                status=EmailReplyDraftStatus.FAILED,
                ai_body="Failed send body",
                final_body="Failed send body",
                manual_review_required=False,
                auto_send_allowed=True,
                attempt_status=EmailSendAttemptStatus.FAILED,
            )
            make_draft(
                index=5,
                status=EmailReplyDraftStatus.FAILED,
                ai_body="Bounced body",
                final_body="Bounced body",
                manual_review_required=False,
                auto_send_allowed=True,
                attempt_status=EmailSendAttemptStatus.BOUNCED,
            )
            make_draft(
                index=6,
                status=EmailReplyDraftStatus.FAILED,
                ai_body="Generation failed body",
                final_body=None,
                manual_review_required=True,
                auto_send_allowed=False,
                attempt_status=None,
            )
            make_draft(
                index=7,
                status=EmailReplyDraftStatus.SENT,
                ai_body="English excluded body",
                final_body="English excluded body",
                manual_review_required=True,
                auto_send_allowed=False,
                attempt_status=EmailSendAttemptStatus.SENT,
                reply_language="en",
                business_scene="first_outreach",
            )
            make_draft(
                index=8,
                status=EmailReplyDraftStatus.SENT,
                ai_body="Different scene body",
                final_body="Different scene body",
                manual_review_required=True,
                auto_send_allowed=False,
                attempt_status=EmailSendAttemptStatus.SENT,
                reply_language="ru",
                business_scene="after_sales",
            )
            sync_session.commit()

        await async_session.run_sync(run)


def test_phase5_email_reply_quality_metrics_support_rates_edit_distance_and_filters() -> None:
    asyncio.run(seed_email_reply_quality_records())

    response = client.get("/dashboard/email-reply-quality?language=ru&business_scene=first_outreach")

    assert response.status_code == 200
    body = response.json()
    assert body["filters"]["language"] == "ru"
    assert body["filters"]["business_scene"] == "first_outreach"
    assert body["draft_count"] == 6
    assert body["ai_generation_success_count"] == 5
    assert body["ai_generation_failed_count"] == 1
    assert body["ai_generation_success_rate"] == pytest.approx(5 / 6)
    assert body["manual_review_count"] == 3
    assert body["manual_adopted_count"] == 1
    assert body["manual_adoption_rate"] == pytest.approx(1 / 3)
    assert body["average_edit_distance_ratio"] > 0
    assert body["auto_send_candidate_count"] == 3
    assert body["auto_send_success_count"] == 1
    assert body["auto_send_success_rate"] == pytest.approx(1 / 3)
    assert body["send_attempt_count"] == 5
    assert body["sent_count"] == 3
    assert body["failed_count"] == 1
    assert body["bounced_count"] == 1
    assert body["send_failure_rate"] == pytest.approx(1 / 5)
    assert body["bounce_rate"] == pytest.approx(1 / 5)
    assert body["customer_reply_count"] == 1
    assert body["customer_reply_rate"] == pytest.approx(1 / 3)
