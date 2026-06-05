from collections.abc import AsyncIterator
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.schemas.customer_followup import CustomerFollowupCreate, CustomerFollowupResponse
from app.services.customer_followups import CustomerFollowupService


router = APIRouter(tags=["customer-followups"])


async def get_async_session() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session


@router.get("/customers/{customer_id:uuid}/followups", response_model=list[CustomerFollowupResponse])
async def list_customer_followups(
    customer_id: UUID,
    async_session: AsyncSession = Depends(get_async_session),
) -> list[CustomerFollowupResponse]:
    def run(sync_session):
        service = CustomerFollowupService(sync_session)
        try:
            return service.list_for_customer(customer_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    return await async_session.run_sync(run)


@router.post("/customers/{customer_id:uuid}/followups", response_model=CustomerFollowupResponse)
async def create_customer_followup(
    customer_id: UUID,
    request: CustomerFollowupCreate,
    async_session: AsyncSession = Depends(get_async_session),
) -> CustomerFollowupResponse:
    def run(sync_session):
        service = CustomerFollowupService(sync_session)
        try:
            followup = service.create_for_customer(customer_id, request=request)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        sync_session.commit()
        return followup

    return await async_session.run_sync(run)
