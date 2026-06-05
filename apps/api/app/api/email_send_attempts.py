from uuid import UUID

from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.session import AsyncSessionLocal
from app.models import EmailSendAttempt
from app.models.enums import EmailReplyDraftStatus, EmailSendAttemptStatus, OutreachStatus
from app.schemas.email_send_attempts import EmailSendAttemptActionRequest, EmailSendAttemptResponse


router = APIRouter(prefix="/email-send-attempts", tags=["email-send-attempts"])


@router.post("/{attempt_id}/retry", response_model=EmailSendAttemptResponse)
async def retry_email_send_attempt(
    attempt_id: str,
    request: EmailSendAttemptActionRequest,
) -> EmailSendAttemptResponse:
    attempt_uuid = parse_attempt_uuid(attempt_id)
    async with AsyncSessionLocal() as async_session:
        def run(sync_session):
            attempt = load_attempt(sync_session, attempt_uuid, attempt_id)
            if attempt.status not in {
                EmailSendAttemptStatus.FAILED,
                EmailSendAttemptStatus.BOUNCED,
                EmailSendAttemptStatus.RETRY_PENDING,
            }:
                raise HTTPException(status_code=400, detail="当前发送尝试状态不支持重试。")

            attempt.status = EmailSendAttemptStatus.RETRY_PENDING
            attempt.attempt_count = int(attempt.attempt_count or 0) + 1
            attempt.error_code = None
            attempt.error_message = None
            attempt.bounce_reason = None

            if attempt.outreach_record is not None:
                attempt.outreach_record.status = OutreachStatus.READY_FOR_MANUAL_SEND
                attempt.outreach_record.response_summary = f"邮件发送进入重试：{request.actor}"
                attempt.outreach_record.next_action = "等待邮件重试"

            if attempt.reply_draft is not None and attempt.reply_draft.status == EmailReplyDraftStatus.FAILED:
                attempt.reply_draft.status = EmailReplyDraftStatus.PENDING_REVIEW

            sync_session.commit()
            return serialize_attempt(attempt)

        return await async_session.run_sync(run)


@router.post("/{attempt_id}/bounce", response_model=EmailSendAttemptResponse)
async def mark_email_send_attempt_bounced(
    attempt_id: str,
    request: EmailSendAttemptActionRequest,
) -> EmailSendAttemptResponse:
    attempt_uuid = parse_attempt_uuid(attempt_id)
    async with AsyncSessionLocal() as async_session:
        def run(sync_session):
            attempt = load_attempt(sync_session, attempt_uuid, attempt_id)
            reason = request.bounce_reason or "Unknown bounce reason"
            attempt.status = EmailSendAttemptStatus.BOUNCED
            attempt.bounce_reason = reason
            attempt.error_code = "bounce"
            attempt.error_message = reason

            if attempt.outreach_record is not None:
                attempt.outreach_record.status = OutreachStatus.BAD_CONTACT
                attempt.outreach_record.response_summary = f"邮件退信：{reason}；记录人：{request.actor}"
                attempt.outreach_record.next_action = "核实邮箱或补充联系方式"

            if attempt.reply_draft is not None:
                attempt.reply_draft.status = EmailReplyDraftStatus.FAILED

            sync_session.commit()
            return serialize_attempt(attempt)

        return await async_session.run_sync(run)


def parse_attempt_uuid(attempt_id: str) -> UUID:
    try:
        return UUID(attempt_id)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Email send attempt {attempt_id} not found.") from None


def load_attempt(sync_session, attempt_uuid: UUID, attempt_id: str) -> EmailSendAttempt:
    statement = (
        select(EmailSendAttempt)
        .options(
            selectinload(EmailSendAttempt.reply_draft),
            selectinload(EmailSendAttempt.outreach_record),
        )
        .where(EmailSendAttempt.id == attempt_uuid)
    )
    attempt = sync_session.scalar(statement)
    if attempt is None:
        raise HTTPException(status_code=404, detail=f"Email send attempt {attempt_id} not found.")
    return attempt


def serialize_attempt(attempt: EmailSendAttempt) -> EmailSendAttemptResponse:
    return EmailSendAttemptResponse(
        id=str(attempt.id),
        reply_draft_id=str(attempt.reply_draft_id) if attempt.reply_draft_id else None,
        outreach_record_id=str(attempt.outreach_record_id) if attempt.outreach_record_id else None,
        provider=attempt.provider,
        provider_message_id=attempt.provider_message_id,
        from_email=attempt.from_email,
        to_emails=attempt.to_emails,
        cc_emails=attempt.cc_emails,
        subject_snapshot=attempt.subject_snapshot,
        body_text_snapshot=attempt.body_text_snapshot,
        status=attempt.status.value,
        attempt_count=attempt.attempt_count,
        error_code=attempt.error_code,
        error_message=attempt.error_message,
        bounce_reason=attempt.bounce_reason,
        sent_at=attempt.sent_at.isoformat() if attempt.sent_at else None,
    )
