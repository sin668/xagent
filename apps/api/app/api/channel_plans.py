from collections.abc import AsyncIterator
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.schemas.channel_plans import (
    ChannelPlanCreate,
    ChannelPlanListResponse,
    ChannelPlanResponse,
    ChannelPlanUpdate,
)
from app.services.channel_plans import ChannelPlanService

router = APIRouter(prefix="/channel-plans", tags=["channel-plans"])


async def get_async_session() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session


def serialize_plan(plan) -> ChannelPlanResponse:
    return ChannelPlanResponse(
        id=plan.id,
        country=plan.country,
        city=plan.city,
        channel_name=plan.channel_name,
        channel_type=plan.channel_type,
        risk_level=plan.risk_level.value,
        source_usage_type=plan.source_usage_type.value,
        keywords=plan.keywords,
        daily_url_limit=plan.daily_url_limit,
        daily_lead_limit=plan.daily_lead_limit,
        status=plan.status.value,
        owner=plan.owner,
        created_at=plan.created_at.isoformat(),
        updated_at=plan.updated_at.isoformat(),
    )


@router.post("", response_model=ChannelPlanResponse)
async def create_channel_plan(
    request: ChannelPlanCreate,
    async_session: AsyncSession = Depends(get_async_session),
) -> ChannelPlanResponse:
    def run(sync_session):
        service = ChannelPlanService(sync_session)
        try:
            plan = service.create_channel_plan(**request.model_dump())
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        sync_session.commit()
        return serialize_plan(plan)

    return await async_session.run_sync(run)


@router.get("", response_model=ChannelPlanListResponse)
async def list_channel_plans(
    country: str | None = None,
    city: str | None = None,
    status: str | None = Query(default=None, pattern="^(draft|enabled|paused|archived)$"),
    limit: int = Query(default=100, ge=1, le=500),
    async_session: AsyncSession = Depends(get_async_session),
) -> ChannelPlanListResponse:
    def run(sync_session):
        service = ChannelPlanService(sync_session)
        return ChannelPlanListResponse(
            items=[
                serialize_plan(plan)
                for plan in service.list_channel_plans(country=country, city=city, status=status, limit=limit)
            ]
        )

    return await async_session.run_sync(run)


@router.get("/{plan_id:uuid}", response_model=ChannelPlanResponse)
async def get_channel_plan(
    plan_id: UUID,
    async_session: AsyncSession = Depends(get_async_session),
) -> ChannelPlanResponse:
    def run(sync_session):
        service = ChannelPlanService(sync_session)
        plan = service.get_channel_plan(plan_id)
        if plan is None:
            raise HTTPException(status_code=404, detail="channel plan 不存在。")
        return serialize_plan(plan)

    return await async_session.run_sync(run)


@router.patch("/{plan_id:uuid}", response_model=ChannelPlanResponse)
async def update_channel_plan(
    plan_id: UUID,
    request: ChannelPlanUpdate,
    async_session: AsyncSession = Depends(get_async_session),
) -> ChannelPlanResponse:
    def run(sync_session):
        service = ChannelPlanService(sync_session)
        try:
            plan = service.update_channel_plan(plan_id, **request.model_dump(exclude_unset=True))
        except ValueError as exc:
            message = str(exc)
            status_code = 404 if "不存在" in message else 422
            raise HTTPException(status_code=status_code, detail=message) from exc
        sync_session.commit()
        return serialize_plan(plan)

    return await async_session.run_sync(run)


@router.delete("/{plan_id:uuid}", response_model=ChannelPlanResponse)
async def archive_channel_plan(
    plan_id: UUID,
    async_session: AsyncSession = Depends(get_async_session),
) -> ChannelPlanResponse:
    def run(sync_session):
        service = ChannelPlanService(sync_session)
        try:
            plan = service.archive_channel_plan(plan_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        sync_session.commit()
        return serialize_plan(plan)

    return await async_session.run_sync(run)
