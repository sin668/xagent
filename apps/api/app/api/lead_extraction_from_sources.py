from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.schemas.lead_extraction_from_sources import (
    LeadExtractionBlockedCandidateResponse,
    LeadExtractionFromSourcesRunRequest,
    LeadExtractionFromSourcesRunResponse,
)
from app.services.agent_thread_runner import AgentThreadRunner
from app.services.lead_extraction_from_sources import LeadExtractionFromSourcesService


router = APIRouter(prefix="/agent-tasks/lead-extraction/from-sources", tags=["agent-tasks"])


async def get_async_session() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session


@router.post("/run", response_model=LeadExtractionFromSourcesRunResponse)
async def run_lead_extraction_from_sources(
    request: LeadExtractionFromSourcesRunRequest,
    async_session: AsyncSession = Depends(get_async_session),
) -> LeadExtractionFromSourcesRunResponse:
    def run(sync_session):
        service = LeadExtractionFromSourcesService(sync_session)
        try:
            result = service.create_lead_extraction_task_from_sources(
                limit=request.limit,
                trigger_source=request.trigger_source,
                country=request.country,
                city=request.city,
            )
        except ValueError as exc:
            sync_session.commit()
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        sync_session.commit()
        task_run_id = result.task_run.id

        def run_agent() -> None:
            async def run_async() -> None:
                async with AsyncSessionLocal() as background_session:
                    def run_background(sync_session):
                        service = LeadExtractionFromSourcesService(sync_session)
                        service.run_queued_lead_extraction_task(task_run_id)
                        sync_session.commit()

                    await background_session.run_sync(run_background)

            import asyncio

            asyncio.run(run_async())

        AgentThreadRunner.start(name=f"lead-extraction-agent-{task_run_id}", target=run_agent)
        return LeadExtractionFromSourcesRunResponse(
            agent_task_run_id=result.task_run.id,
            status=result.task_run.status,
            selected_count=len(result.selected_candidates),
            blocked_count=len(result.blocked_candidates),
            candidate_ids=[candidate.id for candidate in result.selected_candidates],
            blocked_candidates=[
                LeadExtractionBlockedCandidateResponse(
                    candidate_id=item.candidate_id,
                    risk_level=item.risk_level,
                    review_status=item.review_status,
                    extraction_status=item.extraction_status,
                    block_reason=item.block_reason,
                )
                for item in result.blocked_candidates
            ],
        )

    return await async_session.run_sync(run)
