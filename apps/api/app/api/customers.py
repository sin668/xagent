from collections.abc import AsyncIterator
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.schemas.customer import (
    CustomerListResponse,
    CustomerSummary,
    DoNotContactRequest,
    OutreachRecordCreate,
    OutreachRecordListResponse,
    OutreachRecordResponse,
)
from app.services.customer_dnc import CustomerDncService

router = APIRouter(prefix="/customers", tags=["customers"])


async def get_async_session() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session


def serialize_customer(customer) -> CustomerSummary:
    sources = [
        {
            "id": str(source.id),
            "platform": source.platform.value,
            "source_url": source.source_url,
            "evidence_note": source.evidence_note,
            "risk_level": source.channel_risk_level.value,
        }
        for source in (customer.sources or [])
    ]
    contacts = [
        {
            "id": str(contact.id),
            "type": contact.method_type.value,
            "value": contact.value,
            "label": contact.label,
            "source_url": contact.source_url,
            "evidence_note": contact.evidence_note,
            "is_primary": contact.is_primary,
        }
        for contact in (customer.contact_methods or [])
    ]
    primary_source = sources[0] if sources else {}
    return CustomerSummary(
        id=str(customer.id),
        external_id=customer.external_id,
        name=customer.name,
        grade=customer.grade.value,
        status=customer.status.value,
        do_not_contact=customer.do_not_contact,
        country=customer.country,
        city=customer.city,
        customer_type=customer.customer_type.value,
        primary_channel=primary_source.get("platform"),
        risk_level=primary_source.get("risk_level"),
        evidence_note=primary_source.get("evidence_note"),
        ai_recommended_grade=customer.ai_recommended_grade.value if customer.ai_recommended_grade else None,
        ai_recommendation_reason=customer.ai_recommendation_reason,
        missing_fields=customer.missing_fields,
        sources=sources,
        contacts=contacts,
        do_not_contact_reason=customer.do_not_contact_reason,
        do_not_contact_marked_by=customer.do_not_contact_marked_by,
        do_not_contact_marked_at=customer.do_not_contact_marked_at.isoformat() if customer.do_not_contact_marked_at else None,
    )


def serialize_outreach(record) -> OutreachRecordResponse:
    return OutreachRecordResponse(
        id=record.id,
        external_id=record.external_id,
        customer_id=record.customer_id,
        channel=record.channel.value,
        status=record.status.value,
        sent_by=record.sent_by,
        owner=record.owner,
        script_version=record.script_version,
        response_summary=record.response_summary,
        next_action=record.next_action,
        triggers_do_not_contact=record.triggers_do_not_contact,
        do_not_contact_reason=record.do_not_contact_reason,
    )


@router.get("/outreach-candidates", response_model=CustomerListResponse)
async def list_outreach_candidates(async_session: AsyncSession = Depends(get_async_session)) -> CustomerListResponse:
    def run(sync_session):
        service = CustomerDncService(sync_session)
        return CustomerListResponse(items=[serialize_customer(customer) for customer in service.list_outreach_candidates()])

    return await async_session.run_sync(run)


@router.get("", response_model=CustomerListResponse)
async def list_customers(
    limit: int = Query(default=100, ge=1, le=500),
    async_session: AsyncSession = Depends(get_async_session),
) -> CustomerListResponse:
    def run(sync_session):
        service = CustomerDncService(sync_session)
        return CustomerListResponse(items=[serialize_customer(customer) for customer in service.list_customers(limit=limit)])

    return await async_session.run_sync(run)


@router.get("/ai-script-candidates", response_model=CustomerListResponse)
async def list_ai_script_candidates(async_session: AsyncSession = Depends(get_async_session)) -> CustomerListResponse:
    def run(sync_session):
        service = CustomerDncService(sync_session)
        return CustomerListResponse(items=[serialize_customer(customer) for customer in service.list_ai_script_candidates()])

    return await async_session.run_sync(run)


@router.get("/{customer_id:uuid}", response_model=CustomerSummary)
async def get_customer(customer_id: UUID, async_session: AsyncSession = Depends(get_async_session)) -> CustomerSummary:
    def run(sync_session):
        service = CustomerDncService(sync_session)
        try:
            return serialize_customer(service.get_customer(customer_id))
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    return await async_session.run_sync(run)


@router.post("/{customer_id:uuid}/do-not-contact", response_model=CustomerSummary)
async def mark_do_not_contact(
    customer_id: UUID,
    request: DoNotContactRequest,
    async_session: AsyncSession = Depends(get_async_session),
) -> CustomerSummary:
    def run(sync_session):
        service = CustomerDncService(sync_session)
        try:
            customer = service.mark_do_not_contact(customer_id=customer_id, marked_by=request.actor, reason=request.reason)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        sync_session.commit()
        return serialize_customer(customer)

    return await async_session.run_sync(run)


@router.post("/{customer_id:uuid}/do-not-contact/cancel", response_model=CustomerSummary)
async def unmark_do_not_contact(
    customer_id: UUID,
    request: DoNotContactRequest,
    async_session: AsyncSession = Depends(get_async_session),
) -> CustomerSummary:
    def run(sync_session):
        service = CustomerDncService(sync_session)
        try:
            customer = service.unmark_do_not_contact(customer_id=customer_id, unmarked_by=request.actor, reason=request.reason)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        sync_session.commit()
        return serialize_customer(customer)

    return await async_session.run_sync(run)


@router.post("/{customer_id:uuid}/outreach-records", response_model=OutreachRecordResponse)
async def record_outreach(
    customer_id: UUID,
    request: OutreachRecordCreate,
    async_session: AsyncSession = Depends(get_async_session),
) -> OutreachRecordResponse:
    def run(sync_session):
        service = CustomerDncService(sync_session)
        try:
            record = service.record_outreach_result(
                customer_id=customer_id,
                channel=request.channel,
                status=request.status,
                sent_by=request.sent_by,
                owner=request.owner,
                response_summary=request.response_summary,
                next_action=request.next_action,
                do_not_contact_reason=request.do_not_contact_reason,
                external_id=request.external_id,
                manual_confirmed=request.manual_confirmed,
                script_version=request.script_version,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        sync_session.commit()
        return serialize_outreach(record)

    return await async_session.run_sync(run)


@router.get("/{customer_id:uuid}/outreach-records", response_model=OutreachRecordListResponse)
async def list_outreach_records(
    customer_id: UUID,
    async_session: AsyncSession = Depends(get_async_session),
) -> OutreachRecordListResponse:
    def run(sync_session):
        service = CustomerDncService(sync_session)
        try:
            records = service.list_outreach_records(customer_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return OutreachRecordListResponse(items=[serialize_outreach(record) for record in records])

    return await async_session.run_sync(run)
