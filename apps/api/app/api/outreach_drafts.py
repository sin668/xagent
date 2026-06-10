from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from app.schemas.outreach_draft import (
    ManualSendRecordRequest,
    ManualSendRecordResponse,
    OutreachEmailSendRequest,
    OutreachEmailSendResponse,
    OutreachDraftResponse,
)
from app.services.email_sender import EmailMessagePayload, EmailSender, EmailSenderError
from app.services.outreach_draft import OutreachDraftService
from app.settings import settings

router = APIRouter(prefix="/outreach-drafts", tags=["outreach-drafts"])


MOBILE_SEED_CUSTOMER_IDS = {
    "ru-auto-city": UUID("11111111-1111-4111-8111-111111111111"),
}


@router.get("/{customer_id:uuid}", response_model=OutreachDraftResponse)
def get_outreach_draft(
    customer_id: UUID,
    risk_level: str = Query(default="Low", pattern="^(Low|Medium|High|Forbidden)$"),
    do_not_contact: bool = False,
) -> OutreachDraftResponse:
    service = OutreachDraftService()
    return OutreachDraftResponse(**service.get_existing_draft(customer_id=customer_id, risk_level=risk_level, do_not_contact=do_not_contact))


@router.get("/{customer_slug}", response_model=OutreachDraftResponse)
def get_mobile_seed_outreach_draft(
    customer_slug: str,
    risk_level: str = Query(default="Low", pattern="^(Low|Medium|High|Forbidden)$"),
    do_not_contact: bool = False,
) -> OutreachDraftResponse:
    customer_id = MOBILE_SEED_CUSTOMER_IDS.get(customer_slug)
    if customer_id is None:
        raise HTTPException(status_code=404, detail="触达草稿不存在。")

    service = OutreachDraftService()
    return OutreachDraftResponse(**service.get_existing_draft(customer_id=customer_id, risk_level=risk_level, do_not_contact=do_not_contact))


@router.post("/{customer_id:uuid}/record-manual-send", response_model=ManualSendRecordResponse)
def record_manual_send(
    customer_id: UUID,
    request: ManualSendRecordRequest,
    risk_level: str = Query(default="Low", pattern="^(Low|Medium|High|Forbidden)$"),
    do_not_contact: bool = False,
) -> ManualSendRecordResponse:
    service = OutreachDraftService()
    try:
        record = service.record_manual_send(
            customer_id=customer_id,
            human_confirmed=request.human_confirmed,
            sender=request.sender,
            channel=request.channel,
            risk_level=risk_level,
            do_not_contact=do_not_contact,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return ManualSendRecordResponse(**record)


@router.post("/{customer_id:uuid}/send-email", response_model=OutreachEmailSendResponse)
def send_outreach_email(
    customer_id: UUID,
    request: OutreachEmailSendRequest,
) -> OutreachEmailSendResponse:
    if not request.human_confirmed:
        raise HTTPException(status_code=400, detail="邮件发送需要人工确认。")
    if not settings.email_sender_from_email:
        raise HTTPException(status_code=500, detail="邮件发送服务缺少发件邮箱配置。")

    try:
        result = EmailSender.from_settings(settings).send(
            EmailMessagePayload(
                from_email=settings.email_sender_from_email,
                to_emails=[request.to_email],
                subject=request.subject,
                body_text=request.body,
                metadata={
                    "customer_id": str(customer_id),
                    "actor": request.sender,
                    "business_scene": "first_outreach",
                    "manual_confirmed": request.human_confirmed,
                },
            ),
        )
    except EmailSenderError as exc:
        raise HTTPException(status_code=500, detail=f"邮件发送失败：{exc}") from exc

    return OutreachEmailSendResponse(
        customer_id=customer_id,
        status=result.status,
        provider=result.provider,
        provider_message_id=result.provider_message_id,
        to_email=request.to_email,
        subject=request.subject,
        auto_send=False,
    )
