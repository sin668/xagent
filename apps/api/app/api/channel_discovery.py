from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.raw_collection import serialize_candidate, serialize_task
from app.db.session import AsyncSessionLocal
from app.schemas.channel_discovery import ChannelDiscoveryRunRequest, ChannelDiscoveryRunResponse
from app.services.channel_discovery_agent import ChannelDiscoveryAgentService

router = APIRouter(prefix="/channel-discovery", tags=["channel-discovery"])


async def get_async_session() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session


@router.post("/run", response_model=ChannelDiscoveryRunResponse)
async def run_channel_discovery(
    request: ChannelDiscoveryRunRequest,
    async_session: AsyncSession = Depends(get_async_session),
) -> ChannelDiscoveryRunResponse:
    def run(sync_session):
        service = ChannelDiscoveryAgentService(sync_session)
        try:
            result = service.run_discovery(
                plan_id=request.plan_id,
                max_candidates=request.max_candidates,
            )
        except ValueError as exc:
            message = str(exc)
            status_code = 404 if "不存在" in message else 422
            raise HTTPException(status_code=status_code, detail=message) from exc
        sync_session.commit()
        created_count = sum(1 for candidate in result.candidates if candidate.created)
        return ChannelDiscoveryRunResponse(
            task=serialize_task(result.task),
            candidates=[
                serialize_candidate(candidate.candidate_url, created=candidate.created)
                for candidate in result.candidates
            ],
            created_count=created_count,
            updated_count=len(result.candidates) - created_count,
        )

    return await async_session.run_sync(run)

