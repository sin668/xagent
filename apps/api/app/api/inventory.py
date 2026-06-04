from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.schemas.inventory import (
    InventoryItemCreate,
    InventoryItemListResponse,
    InventoryItemResponse,
    InventoryQuoteSafetyResponse,
)
from app.schemas.inventory_match import (
    InventoryMatchDecisionRequest,
    InventoryMatchDecisionResponse,
    InventoryMatchItemResponse,
    InventoryMatchListResponse,
    InventoryMatchRequest,
)
from app.services.inventory import InventoryService
from app.services.inventory_match import QUOTE_DISCLAIMER, InventoryMatchService

router = APIRouter(prefix="/inventory", tags=["inventory"])


async def get_async_session() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session


def serialize_item(item, service: InventoryService) -> InventoryItemResponse:
    return InventoryItemResponse(
        id=item.id,
        external_id=item.external_id,
        brand=item.brand,
        model=item.model,
        year=item.year,
        mileage_km=item.mileage_km,
        vehicle_type=item.vehicle_type,
        condition_summary=item.condition_summary,
        configuration=item.configuration,
        quoted_price=item.quoted_price,
        currency=item.currency,
        quote_status=item.quote_status,
        export_ready=item.export_ready,
        media_urls=item.media_urls or [],
        valid_until=item.valid_until,
        source_ref=item.source_ref,
        is_expired=service.is_expired(item),
        can_ai_quote=service.can_ai_quote(item),
        priority_recommendable=service.can_ai_quote(item),
        risk_flags=service.risk_flags(item),
    )


@router.post("/items", response_model=InventoryItemResponse)
async def create_inventory_item(
    request: InventoryItemCreate,
    async_session: AsyncSession = Depends(get_async_session),
) -> InventoryItemResponse:
    def run(sync_session):
        service = InventoryService(sync_session)
        item = service.create_item(**request.model_dump())
        sync_session.commit()
        return serialize_item(item, service)

    return await async_session.run_sync(run)


def serialize_match(match, service: InventoryMatchService) -> InventoryMatchItemResponse:
    item = match.inventory_item
    return InventoryMatchItemResponse(
        match_id=match.id,
        inventory_item_id=item.id,
        inventory_external_id=item.external_id,
        brand=item.brand,
        model=item.model,
        year=item.year,
        vehicle_type=item.vehicle_type,
        condition_summary=item.condition_summary,
        quoted_price=float(item.quoted_price) if item.quoted_price is not None else None,
        currency=item.currency,
        export_ready=item.export_ready,
        valid_until=item.valid_until.isoformat() if item.valid_until else None,
        priority_recommendable=service.inventory_service.can_ai_quote(item),
        recommendation_reason=match.recommendation_reason,
        risk_tips=match.risk_tips or [],
        requires_compliance_review=any("合规复核" in tip for tip in (match.risk_tips or [])),
    )


@router.post("/matches/{customer_id}/recommendations", response_model=InventoryMatchListResponse)
async def recommend_inventory_matches(
    customer_id,
    request: InventoryMatchRequest,
    async_session: AsyncSession = Depends(get_async_session),
) -> InventoryMatchListResponse:
    def run(sync_session):
        service = InventoryMatchService(sync_session)
        try:
            matches = service.recommend(customer_id=customer_id, **request.model_dump())
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        sync_session.commit()
        return InventoryMatchListResponse(
            customer_id=customer_id,
            quote_disclaimer=QUOTE_DISCLAIMER,
            items=[serialize_match(match, service) for match in matches],
        )

    return await async_session.run_sync(run)


@router.post("/matches/{match_id}/decision", response_model=InventoryMatchDecisionResponse)
async def decide_inventory_match(
    match_id,
    request: InventoryMatchDecisionRequest,
    async_session: AsyncSession = Depends(get_async_session),
) -> InventoryMatchDecisionResponse:
    def run(sync_session):
        service = InventoryMatchService(sync_session)
        try:
            match = service.decide(match_id=match_id, decision=request.decision, owner=request.owner, note=request.note)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        sync_session.commit()
        return InventoryMatchDecisionResponse(
            match_id=match.id,
            decision=match.decision,
            owner=match.decision_owner or request.owner,
            note=match.decision_note,
            formal_quote_allowed=False,
            next_gate=service.next_gate(match),
        )

    return await async_session.run_sync(run)


@router.get("/items", response_model=InventoryItemListResponse)
async def list_inventory_items(async_session: AsyncSession = Depends(get_async_session)) -> InventoryItemListResponse:
    def run(sync_session):
        service = InventoryService(sync_session)
        return InventoryItemListResponse(items=[serialize_item(item, service) for item in service.list_items()])

    return await async_session.run_sync(run)


@router.get("/items/{external_id}/ai-quote-safety", response_model=InventoryQuoteSafetyResponse)
async def get_ai_quote_safety(
    external_id: str,
    async_session: AsyncSession = Depends(get_async_session),
) -> InventoryQuoteSafetyResponse:
    def run(sync_session):
        service = InventoryService(sync_session)
        try:
            item = service.get_item_by_external_id(external_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return InventoryQuoteSafetyResponse(
            external_id=item.external_id,
            can_ai_quote=service.can_ai_quote(item),
            blocking_reasons=service.quote_blocking_reasons(item),
        )

    return await async_session.run_sync(run)
