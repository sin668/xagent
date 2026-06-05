from fastapi import APIRouter, HTTPException, Query

from app.schemas.email_replies import (
    EmailReplyActionRequest,
    EmailReplyDetailResponse,
    EmailReplyListResponse,
)


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


@router.post("/{reply_id}/confirm-send", response_model=EmailReplyDetailResponse)
def confirm_email_reply_send(reply_id: str, request: EmailReplyActionRequest) -> EmailReplyDetailResponse:
    _ = request
    raise HTTPException(status_code=404, detail=f"Email reply {reply_id} not found.")


@router.post("/{reply_id}/reject", response_model=EmailReplyDetailResponse)
def reject_email_reply(reply_id: str, request: EmailReplyActionRequest) -> EmailReplyDetailResponse:
    _ = request
    raise HTTPException(status_code=404, detail=f"Email reply {reply_id} not found.")
