from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.session import AsyncSessionLocal
from app.models import EmailReplyDraft
from app.schemas.email_replies import (
    EmailReplyActionRequest,
    EmailReplyDetailResponse,
    EmailReplyListResponse,
    EmailSendPreviewResponse,
)
from app.services.email_send_preview import EmailSendPreviewService
from app.settings import settings


router = APIRouter(prefix="/email-replies", tags=["email-replies"])


@router.get("", response_model=EmailReplyListResponse)
def list_email_replies(
    limit: int = Query(default=100, ge=1, le=500),
    decision: str | None = Query(default=None, pattern="^(auto_send_allowed|manual_review|blocked)$"),
) -> EmailReplyListResponse:
    _ = (limit, decision)
    return EmailReplyListResponse(items=[], total=0)


@router.get("/{reply_id}", response_model=EmailReplyDetailResponse)
def get_email_reply(reply_id: str) -> EmailReplyDetailResponse:
    raise HTTPException(status_code=404, detail=f"Email reply {reply_id} not found.")


@router.post("/{reply_id}/send-preview", response_model=EmailSendPreviewResponse)
async def preview_email_reply_send(reply_id: str) -> EmailSendPreviewResponse:
    try:
        draft_uuid = UUID(reply_id)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Email reply {reply_id} not found.") from None

    async with AsyncSessionLocal() as async_session:
        def run(sync_session):
            statement = (
                select(EmailReplyDraft)
                .options(
                    selectinload(EmailReplyDraft.customer),
                    selectinload(EmailReplyDraft.message),
                )
                .where(EmailReplyDraft.id == draft_uuid)
            )
            draft = sync_session.scalar(statement)
            if draft is None:
                raise HTTPException(status_code=404, detail=f"Email reply {reply_id} not found.")
            return EmailSendPreviewService.build_preview(
                draft,
                sender_from_email=settings.email_sender_from_email,
            )

        preview = await async_session.run_sync(run)
    return EmailSendPreviewResponse(**preview)


@router.post("/{reply_id}/confirm-send", response_model=EmailReplyDetailResponse)
def confirm_email_reply_send(reply_id: str, request: EmailReplyActionRequest) -> EmailReplyDetailResponse:
    _ = request
    raise HTTPException(status_code=404, detail=f"Email reply {reply_id} not found.")


@router.post("/{reply_id}/reject", response_model=EmailReplyDetailResponse)
def reject_email_reply(reply_id: str, request: EmailReplyActionRequest) -> EmailReplyDetailResponse:
    _ = request
    raise HTTPException(status_code=404, detail=f"Email reply {reply_id} not found.")
