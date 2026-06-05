from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.services.phase3_metrics import Phase3MetricsService


router = APIRouter(prefix="/phase3-dashboard", tags=["phase3-dashboard"])


async def get_async_session() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session


@router.get("/metrics")
async def get_phase3_metrics(async_session: AsyncSession = Depends(get_async_session)) -> dict[str, object]:
    def run(sync_session):
        return Phase3MetricsService(sync_session).metrics()

    return await async_session.run_sync(run)
