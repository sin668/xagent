from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from app.schemas.outreach_draft import (
    ManualSendRecordRequest,
    ManualSendRecordResponse,
    OutreachDraftResponse,
)
from app.services.outreach_draft import OutreachDraftService

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
