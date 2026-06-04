from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.schemas.phase2_dashboard import Phase2DashboardResponse
from app.services.phase2_dashboard import Phase2DashboardService


router = APIRouter(prefix="/dashboard", tags=["dashboard"])


async def get_async_session() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session


@router.get("/phase2", response_model=Phase2DashboardResponse)
async def get_phase2_dashboard(
    channel_prefix: str | None = Query(default=None, max_length=120),
    async_session: AsyncSession = Depends(get_async_session),
) -> Phase2DashboardResponse:
    def run(sync_session):
        return Phase2DashboardResponse(**Phase2DashboardService(sync_session).metrics(channel_prefix=channel_prefix))

    return await async_session.run_sync(run)
