from uuid import UUID
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.session import AsyncSessionLocal
from app.models import EmailMessage, EmailReplyDraft, EmailSendAttempt, OutreachRecord
from app.models.enums import (
    ContactMethodType,
    EmailMessageDirection,
    EmailMessageSourceType,
    EmailMessageStatus,
    EmailReplyDraftStatus,
    EmailSendAttemptStatus,
    OutreachStatus,
)
from app.schemas.email_replies import (
    EmailReplyActionRequest,
    EmailAutoSendCheckResponse,
    EmailReplyDraftResponse,
    EmailReplyDetailResponse,
    EmailReplyListResponse,
    EmailKnowledgeHitResponse,
    EmailReplySummary,
    EmailSendPreviewResponse,
)
from app.services.email_reply_audit import EmailReplyAuditService
from app.services.email_sender import EmailMessagePayload, EmailSender, EmailSenderError
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
async def confirm_email_reply_send(reply_id: str, request: EmailReplyActionRequest) -> EmailReplyDetailResponse:
    if not request.manual_confirmed:
        raise HTTPException(status_code=400, detail="邮件发送需要人工确认。")
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
                    selectinload(EmailReplyDraft.thread),
                )
                .where(EmailReplyDraft.id == draft_uuid)
            )
            draft = sync_session.scalar(statement)
            if draft is None:
                raise HTTPException(status_code=404, detail=f"Email reply {reply_id} not found.")

            final_subject = request.final_subject or draft.final_subject or draft.ai_suggested_subject
            final_body = request.final_body or draft.final_body or draft.ai_suggested_body
            if not final_subject or not final_body:
                raise HTTPException(status_code=400, detail="邮件发送需要主题和正文。")

            EmailReplyAuditService.apply_human_edit(
                draft,
                final_subject=final_subject,
                final_body=final_body,
                reviewed_by=request.actor,
            )
            preview = EmailSendPreviewService.build_preview(
                draft,
                sender_from_email=settings.email_sender_from_email,
            )
            if preview["decision"] == "blocked":
                raise HTTPException(status_code=400, detail="发送前检查命中硬拦截，禁止发送。")
            if not preview["to_emails"]:
                raise HTTPException(status_code=400, detail="邮件发送需要至少一个收件人。")

            payload = EmailMessagePayload(
                from_email=preview["from_email"],
                to_emails=preview["to_emails"],
                cc_emails=preview["cc_emails"],
                subject=preview["subject"],
                body_text=preview["body_text"],
                metadata={"reply_draft_id": str(draft.id), "actor": request.actor},
            )
            outreach = OutreachRecord(
                customer_id=draft.customer_id,
                channel=ContactMethodType.EMAIL,
                status=OutreachStatus.SENT,
                sent_by=request.actor,
                owner=request.actor,
                sent_at=datetime.now(UTC),
                response_summary=request.review_note or "人工确认邮件已发送",
                next_action="等待客户回复",
                script_version=draft.prompt_version,
            )
            sync_session.add(outreach)
            sync_session.flush()
            attempt = EmailSendAttempt(
                reply_draft_id=draft.id,
                outreach_record_id=outreach.id,
                provider=settings.email_sender_provider,
                from_email=payload.from_email,
                to_emails=payload.to_emails,
                cc_emails=payload.cc_emails,
                bcc_emails=[],
                subject_snapshot=payload.subject,
                body_text_snapshot=payload.body_text,
                body_html_snapshot=payload.body_html,
                status=EmailSendAttemptStatus.SENDING,
                attempt_count=1,
            )
            sync_session.add(attempt)
            sync_session.flush()
            try:
                send_result = EmailSender.from_settings(settings).send(payload)
            except EmailSenderError as exc:
                attempt.status = EmailSendAttemptStatus.FAILED
                attempt.error_code = exc.__class__.__name__
                attempt.error_message = str(exc)
                draft.status = EmailReplyDraftStatus.FAILED
                sync_session.commit()
                raise HTTPException(status_code=500, detail=f"邮件发送失败：{exc}") from exc

            sent_at = datetime.now(UTC)
            attempt.provider = send_result.provider
            attempt.provider_message_id = send_result.provider_message_id
            attempt.status = EmailSendAttemptStatus.SENT
            attempt.sent_at = sent_at
            draft.status = EmailReplyDraftStatus.SENT
            draft.sent_record_id = outreach.id
            if draft.message is not None:
                outbound = EmailMessage(
                    thread_id=draft.thread_id,
                    customer_id=draft.customer_id,
                    direction=EmailMessageDirection.OUTBOUND,
                    from_email=payload.from_email,
                    to_emails=payload.to_emails,
                    cc_emails=payload.cc_emails,
                    subject=payload.subject,
                    body_text=payload.body_text,
                    body_html=payload.body_html,
                    language=draft.reply_language,
                    status=EmailMessageStatus.SENT,
                    source_type=EmailMessageSourceType.API_IMPORT,
                    external_message_id=send_result.provider_message_id,
                )
                sync_session.add(outbound)
            draft.auto_send_decision_json = {
                **(draft.auto_send_decision_json or {}),
                "manual_send_trace": EmailReplyAuditService.build_send_trace(
                    draft,
                    attempt=attempt,
                    actor=request.actor,
                    action="manual_send_confirmed",
                    occurred_at=sent_at,
                ),
            }
            sync_session.commit()
            return _serialize_email_reply_detail(draft, preview)

        detail = await async_session.run_sync(run)
    return detail


@router.post("/{reply_id}/auto-send", response_model=EmailReplyDetailResponse)
async def auto_send_email_reply(reply_id: str) -> EmailReplyDetailResponse:
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
                    selectinload(EmailReplyDraft.thread),
                )
                .where(EmailReplyDraft.id == draft_uuid)
            )
            draft = sync_session.scalar(statement)
            if draft is None:
                raise HTTPException(status_code=404, detail=f"Email reply {reply_id} not found.")

            _assert_auto_send_eligible(draft)
            final_subject = draft.final_subject or draft.ai_suggested_subject
            final_body = draft.final_body or draft.ai_suggested_body
            if not final_subject or not final_body:
                raise HTTPException(status_code=400, detail="自动发送需要主题和正文。")

            EmailReplyAuditService.apply_human_edit(
                draft,
                final_subject=final_subject,
                final_body=final_body,
                reviewed_by="AUTO_SEND",
            )
            preview = EmailSendPreviewService.build_preview(
                draft,
                sender_from_email=settings.email_sender_from_email,
            )
            if preview["decision"] == "blocked":
                raise HTTPException(status_code=400, detail="发送前检查命中硬拦截，禁止自动发送。")
            if preview["decision"] != "auto_send_allowed":
                raise HTTPException(status_code=400, detail="发送前检查要求人工复核，禁止自动发送。")
            if not preview["to_emails"]:
                raise HTTPException(status_code=400, detail="自动发送需要至少一个收件人。")

            payload = EmailMessagePayload(
                from_email=preview["from_email"],
                to_emails=preview["to_emails"],
                cc_emails=preview["cc_emails"],
                subject=preview["subject"],
                body_text=preview["body_text"],
                metadata={"reply_draft_id": str(draft.id), "actor": "AUTO_SEND"},
            )
            outreach = OutreachRecord(
                customer_id=draft.customer_id,
                channel=ContactMethodType.EMAIL,
                status=OutreachStatus.SENT,
                sent_by="AUTO_SEND",
                owner=getattr(draft.customer, "owner", None),
                sent_at=datetime.now(UTC),
                response_summary="白名单低风险场景自动发送",
                next_action="等待客户回复",
                script_version=draft.prompt_version,
            )
            sync_session.add(outreach)
            sync_session.flush()
            attempt = EmailSendAttempt(
                reply_draft_id=draft.id,
                outreach_record_id=outreach.id,
                provider=settings.email_sender_provider,
                from_email=payload.from_email,
                to_emails=payload.to_emails,
                cc_emails=payload.cc_emails,
                bcc_emails=[],
                subject_snapshot=payload.subject,
                body_text_snapshot=payload.body_text,
                body_html_snapshot=payload.body_html,
                status=EmailSendAttemptStatus.SENDING,
                attempt_count=1,
            )
            sync_session.add(attempt)
            sync_session.flush()
            try:
                send_result = EmailSender.from_settings(settings).send(payload)
            except EmailSenderError as exc:
                attempt.status = EmailSendAttemptStatus.FAILED
                attempt.error_code = exc.__class__.__name__
                attempt.error_message = str(exc)
                draft.status = EmailReplyDraftStatus.FAILED
                draft.auto_send_decision_json = {
                    **(draft.auto_send_decision_json or {}),
                    "auto_send_trace": {
                        "actor": "AUTO_SEND",
                        "result": "failed",
                        "error_code": exc.__class__.__name__,
                        "error_message": str(exc),
                        "eligibility_reasons": list((draft.auto_send_decision_json or {}).get("reasons") or []),
                        "knowledge_evidence": list(draft.knowledge_hits_json or []),
                    },
                }
                sync_session.commit()
                raise HTTPException(status_code=500, detail=f"自动发送失败：{exc}") from exc

            sent_at = datetime.now(UTC)
            attempt.provider = send_result.provider
            attempt.provider_message_id = send_result.provider_message_id
            attempt.status = EmailSendAttemptStatus.SENT
            attempt.sent_at = sent_at
            draft.status = EmailReplyDraftStatus.SENT
            draft.sent_record_id = outreach.id
            outbound = EmailMessage(
                thread_id=draft.thread_id,
                customer_id=draft.customer_id,
                direction=EmailMessageDirection.OUTBOUND,
                from_email=payload.from_email,
                to_emails=payload.to_emails,
                cc_emails=payload.cc_emails,
                subject=payload.subject,
                body_text=payload.body_text,
                body_html=payload.body_html,
                language=draft.reply_language,
                status=EmailMessageStatus.SENT,
                source_type=EmailMessageSourceType.API_IMPORT,
                external_message_id=send_result.provider_message_id,
            )
            sync_session.add(outbound)
            draft.auto_send_decision_json = {
                **(draft.auto_send_decision_json or {}),
                "auto_send_trace": {
                    **EmailReplyAuditService.build_send_trace(
                        draft,
                        attempt=attempt,
                        actor="AUTO_SEND",
                        action="whitelist_low_risk_auto_send",
                        occurred_at=sent_at,
                    ),
                    "eligibility_reasons": list((draft.auto_send_decision_json or {}).get("reasons") or []),
                    "knowledge_evidence": list(draft.knowledge_hits_json or []),
                },
            }
            sync_session.commit()
            return _serialize_email_reply_detail(draft, preview)

        detail = await async_session.run_sync(run)
    return detail


@router.post("/{reply_id}/reject", response_model=EmailReplyDetailResponse)
def reject_email_reply(reply_id: str, request: EmailReplyActionRequest) -> EmailReplyDetailResponse:
    _ = request
    raise HTTPException(status_code=404, detail=f"Email reply {reply_id} not found.")


def _assert_auto_send_eligible(draft: EmailReplyDraft) -> None:
    decision_json = draft.auto_send_decision_json or {}
    required_reasons = {
        "whitelisted_customer",
        "fixed_faq",
        "first_touch",
        "low_risk_scene",
        "knowledge_auto_reply_allowed",
        "knowledge_embedding_ready",
        "reply_language_confident",
    }
    reasons = set(decision_json.get("reasons") or [])
    if bool(decision_json.get("hard_blocked")):
        raise HTTPException(status_code=400, detail="发送前检查命中硬拦截，禁止自动发送。")
    if not bool(draft.auto_send_allowed) or bool(draft.manual_review_required):
        raise HTTPException(status_code=400, detail="自动发送准入未通过，需要人工复核。")
    if decision_json.get("route") != "auto_send_candidate" or decision_json.get("auto_send_allowed") is not True:
        raise HTTPException(status_code=400, detail="自动发送准入未通过，需要人工复核。")
    missing_reasons = required_reasons - reasons
    if missing_reasons:
        raise HTTPException(status_code=400, detail="自动发送准入证据不足，需要人工复核。")
    knowledge_hits = list(draft.knowledge_hits_json or [])
    if not knowledge_hits:
        raise HTTPException(status_code=400, detail="缺少知识证据，需要人工复核。")
    for hit in knowledge_hits:
        if not isinstance(hit, dict):
            raise HTTPException(status_code=400, detail="知识证据格式不确定，需要人工复核。")
        if hit.get("auto_reply_allowed") is not True:
            raise HTTPException(status_code=400, detail="知识不允许自动回复，需要人工复核。")
        if str(hit.get("embedding_status") or "").strip().lower() not in {"ready", "embedding_ready"}:
            raise HTTPException(status_code=400, detail="知识 embedding 未就绪，需要人工复核。")
        if str(hit.get("risk_level") or "").strip().lower() != "low":
            raise HTTPException(status_code=400, detail="知识风险不属于低风险，需要人工复核。")


def _serialize_email_reply_detail(draft: EmailReplyDraft, preview: dict) -> EmailReplyDetailResponse:
    customer = draft.customer
    message = draft.message
    knowledge_hits = [
        EmailKnowledgeHitResponse(
            id=str(hit.get("knowledge_item_id") or hit.get("id")) if isinstance(hit, dict) and (hit.get("knowledge_item_id") or hit.get("id")) else None,
            title=str(hit.get("title") or "Unknown") if isinstance(hit, dict) else "Unknown",
            note=hit.get("evidence_note") if isinstance(hit, dict) else None,
            similarity_score=hit.get("similarity_score") if isinstance(hit, dict) else None,
            auto_reply_allowed=bool(hit.get("auto_reply_allowed")) if isinstance(hit, dict) else False,
        )
        for hit in list(draft.knowledge_hits_json or [])
    ]
    summary = EmailReplySummary(
        id=str(draft.id),
        thread_id=str(draft.thread_id) if draft.thread_id else None,
        customer_name=getattr(customer, "name", "Unknown"),
        customer_grade=str(getattr(getattr(customer, "grade", None), "value", getattr(customer, "grade", "Unknown"))),
        subject=preview["subject"],
        preview=preview["body_text"][:160],
        language=draft.reply_language,
        auto_send_decision=preview["decision"],
        hard_block_reasons=preview["hard_blocks"],
        knowledge_hits=knowledge_hits,
        risk_level=None,
        received_at=message.created_at.isoformat() if getattr(message, "created_at", None) else None,
    )
    return EmailReplyDetailResponse(
        **summary.model_dump(),
        inbound_body=getattr(message, "body_text", None),
        reply_draft=EmailReplyDraftResponse(
            subject=draft.final_subject or draft.ai_suggested_subject,
            body=draft.final_body or draft.ai_suggested_body,
            prompt_version=draft.prompt_version or "email-reply-v1",
        ),
        auto_send_check=EmailAutoSendCheckResponse(
            decision=preview["decision"],
            allow_auto_send=preview["allow_auto_send"],
            reasons=preview["reasons"],
            hard_blocks=preview["hard_blocks"],
        ),
        ai_audit={
            "reviewed_by": draft.reviewed_by,
            "reviewed_at": draft.reviewed_at.isoformat() if draft.reviewed_at else None,
            "send_triggered": True,
            "sent_record_id": str(draft.sent_record_id) if draft.sent_record_id else None,
        },
    )
