from collections.abc import AsyncIterator
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.schemas.customer_vehicle_intent import (
    CustomerVehicleIntentCreate,
    CustomerVehicleIntentResponse,
    CustomerVehicleIntentUpdate,
)
from app.services.customer_vehicle_intents import CustomerVehicleIntentService


router = APIRouter(tags=["customer-vehicle-intents"])


async def get_async_session() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session


@router.get("/customers/{customer_id:uuid}/vehicle-intents", response_model=list[CustomerVehicleIntentResponse])
async def list_customer_vehicle_intents(
    customer_id: UUID,
    async_session: AsyncSession = Depends(get_async_session),
) -> list[CustomerVehicleIntentResponse]:
    def run(sync_session):
        service = CustomerVehicleIntentService(sync_session)
        try:
            return service.list_for_customer(customer_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    return await async_session.run_sync(run)


@router.post("/customers/{customer_id:uuid}/vehicle-intents", response_model=CustomerVehicleIntentResponse)
async def create_customer_vehicle_intent(
    customer_id: UUID,
    request: CustomerVehicleIntentCreate,
    async_session: AsyncSession = Depends(get_async_session),
) -> CustomerVehicleIntentResponse:
    def run(sync_session):
        service = CustomerVehicleIntentService(sync_session)
        try:
            intent = service.create_for_customer(customer_id, request=request)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        sync_session.commit()
        return intent

    return await async_session.run_sync(run)


@router.patch("/customer-vehicle-intents/{intent_id:uuid}", response_model=CustomerVehicleIntentResponse)
async def update_customer_vehicle_intent(
    intent_id: UUID,
    request: CustomerVehicleIntentUpdate,
    async_session: AsyncSession = Depends(get_async_session),
) -> CustomerVehicleIntentResponse:
    def run(sync_session):
        service = CustomerVehicleIntentService(sync_session)
        try:
            intent = service.update_intent(intent_id, request=request)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        sync_session.commit()
        return intent

    return await async_session.run_sync(run)
