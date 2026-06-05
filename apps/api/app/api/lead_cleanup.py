from collections.abc import AsyncIterator
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models.enums import LeadCleanupSuggestionReviewStatus, LeadCleanupSuggestionType
from app.schemas.lead_cleanup import (
    LeadCleanupSuggestionExecuteRequest,
    LeadCleanupSuggestionListResponse,
    LeadCleanupSuggestionResponse,
    LeadCleanupSuggestionReviewRequest,
)
from app.services.lead_cleanup import LeadCleanupSuggestionQueryFilters, LeadCleanupSuggestionService


router = APIRouter(prefix="/lead-cleanup", tags=["lead-cleanup"])


async def get_async_session() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session


@router.get("/suggestions", response_model=LeadCleanupSuggestionListResponse)
async def list_cleanup_suggestions(
    suggestion_type: LeadCleanupSuggestionType | None = Query(default=None),
    review_status: LeadCleanupSuggestionReviewStatus | None = Query(default=LeadCleanupSuggestionReviewStatus.PENDING),
    min_confidence: float | None = Query(default=None, ge=0, le=1, alias="confidence"),
    max_confidence: float | None = Query(default=None, ge=0, le=1),
    lead_id: UUID | None = Query(default=None, alias="lead"),
    limit: int = Query(default=100, ge=1, le=500),
    async_session: AsyncSession = Depends(get_async_session),
) -> LeadCleanupSuggestionListResponse:
    def run(sync_session):
        service = LeadCleanupSuggestionService(sync_session)
        rows = service.list_suggestions(
            LeadCleanupSuggestionQueryFilters(
                suggestion_type=suggestion_type,
                review_status=review_status,
                min_confidence=min_confidence,
                max_confidence=max_confidence,
                lead_id=lead_id,
                limit=limit,
            )
        )
        items = [LeadCleanupSuggestionResponse.model_validate(row) for row in rows]
        return LeadCleanupSuggestionListResponse(items=items, total=len(items))

    return await async_session.run_sync(run)


@router.patch("/suggestions/{suggestion_id:uuid}/approve", response_model=LeadCleanupSuggestionResponse)
async def approve_cleanup_suggestion(
    suggestion_id: UUID,
    request: LeadCleanupSuggestionReviewRequest,
    async_session: AsyncSession = Depends(get_async_session),
) -> LeadCleanupSuggestionResponse:
    def run(sync_session):
        service = LeadCleanupSuggestionService(sync_session)
        try:
            suggestion = service.approve_suggestion(
                suggestion_id,
                actor=request.actor,
                actor_role=request.actor_role,
                review_note=request.review_note,
            )
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        sync_session.commit()
        return LeadCleanupSuggestionResponse.model_validate(suggestion)

    return await async_session.run_sync(run)


@router.patch("/suggestions/{suggestion_id:uuid}/reject", response_model=LeadCleanupSuggestionResponse)
async def reject_cleanup_suggestion(
    suggestion_id: UUID,
    request: LeadCleanupSuggestionReviewRequest,
    async_session: AsyncSession = Depends(get_async_session),
) -> LeadCleanupSuggestionResponse:
    def run(sync_session):
        service = LeadCleanupSuggestionService(sync_session)
        try:
            suggestion = service.reject_suggestion(
                suggestion_id,
                actor=request.actor,
                actor_role=request.actor_role,
                review_note=request.review_note,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        sync_session.commit()
        return LeadCleanupSuggestionResponse.model_validate(suggestion)

    return await async_session.run_sync(run)


@router.post("/suggestions/{suggestion_id:uuid}/execute", response_model=LeadCleanupSuggestionResponse)
async def execute_cleanup_suggestion(
    suggestion_id: UUID,
    request: LeadCleanupSuggestionExecuteRequest,
    async_session: AsyncSession = Depends(get_async_session),
) -> LeadCleanupSuggestionResponse:
    def run(sync_session):
        service = LeadCleanupSuggestionService(sync_session)
        try:
            suggestion = service.execute_suggestion(
                suggestion_id,
                actor=request.actor,
                actor_role=request.actor_role,
                execution_note=request.execution_note,
            )
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        sync_session.commit()
        return LeadCleanupSuggestionResponse.model_validate(suggestion)

    return await async_session.run_sync(run)


@router.get("/suggestions/{suggestion_id:uuid}", response_model=LeadCleanupSuggestionResponse)
async def get_cleanup_suggestion(
    suggestion_id: UUID,
    async_session: AsyncSession = Depends(get_async_session),
) -> LeadCleanupSuggestionResponse:
    def run(sync_session):
        service = LeadCleanupSuggestionService(sync_session)
        try:
            return LeadCleanupSuggestionResponse.model_validate(service.get_suggestion(suggestion_id))
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    return await async_session.run_sync(run)
