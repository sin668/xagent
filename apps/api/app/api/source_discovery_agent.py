from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.schemas.source_discovery_agent import SourceDiscoveryRunRequest, SourceDiscoveryRunResponse
from app.services.agent_thread_runner import AgentThreadRunner
from app.services.source_discovery_agent import SourceDiscoveryAgentRequest, SourceDiscoveryAgentService


router = APIRouter(prefix="/agent-tasks/source-discovery", tags=["agent-tasks"])


async def get_async_session() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session


def get_source_discovery_service(
    async_session: AsyncSession = Depends(get_async_session),
) -> SourceDiscoveryAgentService:
    return SourceDiscoveryAgentService(async_session=async_session)


@router.post("/run", response_model=SourceDiscoveryRunResponse)
async def run_source_discovery(
    request: SourceDiscoveryRunRequest,
    service: SourceDiscoveryAgentService = Depends(get_source_discovery_service),
) -> SourceDiscoveryRunResponse:
    city = ", ".join(request.cities) if request.cities else None
    agent_request = SourceDiscoveryAgentRequest(
        country=request.country,
        city=city,
        channel_strategy=request.channel_strategy,
        keywords=request.keywords,
        max_candidates=request.limit,
        trigger_source="manual_api",
    )
    try:
        task_run = await service.create_pending_task(agent_request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    task_run_id = task_run.id

    def run_agent() -> None:
        async def run_async() -> None:
            async with AsyncSessionLocal() as async_session:
                await SourceDiscoveryAgentService(async_session=async_session).run_existing_task(task_run_id)

        import asyncio

        asyncio.run(run_async())

    AgentThreadRunner.start(name=f"source-discovery-agent-{task_run_id}", target=run_agent)
    return SourceDiscoveryRunResponse(
        agent_task_run_id=task_run_id,
        status=task_run.status,
        created_count=0,
        blocked_count=0,
        duplicate_count=0,
    )
