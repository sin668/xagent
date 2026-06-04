from collections.abc import AsyncIterator
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.schemas.compliance import (
    CompliancePendingItem,
    CompliancePendingListResponse,
    ComplianceReviewRequest,
    ComplianceReviewResponse,
    ComplianceReviewStatusResponse,
    MarkQuotedRequest,
    MarkQuotedResponse,
)
from app.services.compliance import AI_RISK_TIP, ComplianceService

router = APIRouter(prefix="/compliance", tags=["compliance"])


async def get_async_session() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session


def serialize_review(review) -> ComplianceReviewResponse:
    return ComplianceReviewResponse(
        id=review.id,
        customer_id=review.customer_id,
        status=review.status.value,
        reviewer=review.reviewer,
        reviewed_at=review.reviewed_at.isoformat() if review.reviewed_at else None,
        reason=review.reason,
        risk_note=review.risk_note,
    )


@router.get("/reviews/pending", response_model=CompliancePendingListResponse)
async def list_pending_reviews(async_session: AsyncSession = Depends(get_async_session)) -> CompliancePendingListResponse:
    def run(sync_session):
        service = ComplianceService(sync_session)
        items = [
            CompliancePendingItem(
                customer_id=str(customer.id),
                customer_name=customer.name,
                grade=customer.grade.value,
                status=review.status.value,
                city=customer.city,
                risk_note=review.risk_note,
            )
            for customer, review in service.list_pending_reviews()
        ]
        sync_session.commit()
        return CompliancePendingListResponse(items=items)

    return await async_session.run_sync(run)


@router.get("/customers/{customer_id:uuid}/status", response_model=ComplianceReviewStatusResponse)
async def get_compliance_status(
    customer_id: UUID,
    async_session: AsyncSession = Depends(get_async_session),
) -> ComplianceReviewStatusResponse:
    def run(sync_session):
        service = ComplianceService(sync_session)
        try:
            customer, review = service.status_for_customer(customer_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        sync_session.commit()
        return ComplianceReviewStatusResponse(
            customer_id=str(customer.id),
            status=review.status.value,
            reviewer=review.reviewer,
            reviewed_at=review.reviewed_at.isoformat() if review.reviewed_at else None,
            reason=review.reason,
            risk_note=review.risk_note,
            quote_contract_blocked=service.quote_contract_blocked(customer, review),
            ai_risk_tip=AI_RISK_TIP,
        )

    return await async_session.run_sync(run)


@router.post("/customers/{customer_id:uuid}/review", response_model=ComplianceReviewResponse)
async def submit_compliance_review(
    customer_id: UUID,
    request: ComplianceReviewRequest,
    async_session: AsyncSession = Depends(get_async_session),
) -> ComplianceReviewResponse:
    def run(sync_session):
        service = ComplianceService(sync_session)
        try:
            review = service.submit_review(
                customer_id=customer_id,
                actor=request.actor,
                actor_role=request.actor_role,
                status=request.status,
                reason=request.reason,
                risk_note=request.risk_note,
            )
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        sync_session.commit()
        return serialize_review(review)

    return await async_session.run_sync(run)


@router.post("/customers/{customer_id:uuid}/mark-quoted", response_model=MarkQuotedResponse)
async def mark_customer_quoted(
    customer_id: UUID,
    request: MarkQuotedRequest,
    async_session: AsyncSession = Depends(get_async_session),
) -> MarkQuotedResponse:
    def run(sync_session):
        service = ComplianceService(sync_session)
        try:
            customer = service.mark_quoted(customer_id=customer_id, actor=request.actor)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        sync_session.commit()
        return MarkQuotedResponse(customer_id=str(customer.id), quoted_status=customer.status.value)

    return await async_session.run_sync(run)
