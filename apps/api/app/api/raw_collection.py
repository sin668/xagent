from collections.abc import AsyncIterator
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.schemas.raw_collection import (
    CandidateUrlListResponse,
    CandidateUrlResponse,
    CandidateUrlUpsert,
    CollectionTaskCreate,
    CollectionTaskListResponse,
    CollectionTaskResponse,
    PageSnapshotCreate,
    PageSnapshotListResponse,
    PageSnapshotResponse,
)
from app.services.raw_collection import RawCollectionService

router = APIRouter(prefix="/raw-collection", tags=["raw-collection"])


async def get_async_session() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session


def serialize_task(task) -> CollectionTaskResponse:
    return CollectionTaskResponse(
        id=task.id,
        plan_id=task.plan_id,
        task_type=task.task_type,
        channel_name=task.channel_name,
        risk_level=task.risk_level.value,
        source_usage_type=task.source_usage_type.value,
        max_sample_size=task.max_sample_size,
        allowed_actions=task.allowed_actions,
        forbidden_actions=task.forbidden_actions,
        status=task.status.value,
        started_at=task.started_at.isoformat() if task.started_at else None,
        finished_at=task.finished_at.isoformat() if task.finished_at else None,
        error_message=task.error_message,
        created_at=task.created_at.isoformat(),
    )


def serialize_candidate(candidate, *, created: bool | None = None) -> CandidateUrlResponse:
    return CandidateUrlResponse(
        id=candidate.id,
        task_id=candidate.task_id,
        url=candidate.url,
        url_hash=candidate.url_hash,
        source_platform=candidate.source_platform.value,
        source_risk_level=candidate.source_risk_level.value,
        source_usage_type=candidate.source_usage_type.value,
        requires_secondary_verification=candidate.requires_secondary_verification,
        queue_eligible=candidate.queue_eligible,
        discovery_reason=candidate.discovery_reason,
        status=candidate.status.value,
        created=created,
        created_at=candidate.created_at.isoformat(),
        updated_at=candidate.updated_at.isoformat(),
    )


def serialize_snapshot(snapshot, *, latest_for_candidate_id: UUID | None = None) -> PageSnapshotResponse:
    return PageSnapshotResponse(
        id=snapshot.id,
        candidate_url_id=snapshot.candidate_url_id,
        page_title=snapshot.page_title,
        text_excerpt=snapshot.text_excerpt,
        evidence_note=snapshot.evidence_note,
        read_status=snapshot.read_status.value,
        captured_at=snapshot.captured_at.isoformat(),
        robots_or_policy_note=snapshot.robots_or_policy_note,
        created_at=snapshot.created_at.isoformat(),
        latest_for_candidate_id=latest_for_candidate_id,
    )


@router.post("/tasks", response_model=CollectionTaskResponse)
async def create_collection_task(
    request: CollectionTaskCreate,
    async_session: AsyncSession = Depends(get_async_session),
) -> CollectionTaskResponse:
    def run(sync_session):
        service = RawCollectionService(sync_session)
        try:
            task = service.create_collection_task(
                plan_id=request.plan_id,
                task_type=request.task_type,
                channel_name=request.channel_name,
                risk_level=request.risk_level,
                source_usage_type=request.source_usage_type,
                max_sample_size=request.max_sample_size,
                allowed_actions=request.allowed_actions,
                forbidden_actions=request.forbidden_actions,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        sync_session.commit()
        return serialize_task(task)

    return await async_session.run_sync(run)


@router.post("/page-snapshots", response_model=PageSnapshotResponse)
async def create_page_snapshot(
    request: PageSnapshotCreate,
    async_session: AsyncSession = Depends(get_async_session),
) -> PageSnapshotResponse:
    def run(sync_session):
        service = RawCollectionService(sync_session)
        try:
            result = service.create_page_snapshot(
                candidate_url_id=request.candidate_url_id,
                page_title=request.page_title,
                text_excerpt=request.text_excerpt,
                evidence_note=request.evidence_note,
                read_status=request.read_status,
                robots_or_policy_note=request.robots_or_policy_note,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        sync_session.commit()
        return serialize_snapshot(result.page_snapshot, latest_for_candidate_id=result.latest_for_candidate.id)

    return await async_session.run_sync(run)


@router.get("/page-snapshots", response_model=PageSnapshotListResponse)
async def list_page_snapshots(
    candidate_url_id: UUID | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    async_session: AsyncSession = Depends(get_async_session),
) -> PageSnapshotListResponse:
    def run(sync_session):
        service = RawCollectionService(sync_session)
        return PageSnapshotListResponse(
            items=[
                serialize_snapshot(snapshot)
                for snapshot in service.list_page_snapshots(candidate_url_id=candidate_url_id, limit=limit)
            ]
        )

    return await async_session.run_sync(run)


@router.get("/tasks", response_model=CollectionTaskListResponse)
async def list_collection_tasks(
    limit: int = Query(default=100, ge=1, le=500),
    async_session: AsyncSession = Depends(get_async_session),
) -> CollectionTaskListResponse:
    def run(sync_session):
        service = RawCollectionService(sync_session)
        return CollectionTaskListResponse(items=[serialize_task(task) for task in service.list_collection_tasks(limit=limit)])

    return await async_session.run_sync(run)


@router.post("/candidate-urls/upsert", response_model=CandidateUrlResponse)
async def upsert_candidate_url(
    request: CandidateUrlUpsert,
    async_session: AsyncSession = Depends(get_async_session),
) -> CandidateUrlResponse:
    def run(sync_session):
        service = RawCollectionService(sync_session)
        try:
            result = service.upsert_candidate_url(
                task_id=request.task_id,
                url=request.url,
                source_platform=request.source_platform,
                source_risk_level=request.source_risk_level,
                source_usage_type=request.source_usage_type,
                discovery_reason=request.discovery_reason,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        sync_session.commit()
        return serialize_candidate(result.candidate_url, created=result.created)

    return await async_session.run_sync(run)


@router.get("/candidate-urls", response_model=CandidateUrlListResponse)
async def list_candidate_urls(
    task_id: UUID | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    async_session: AsyncSession = Depends(get_async_session),
) -> CandidateUrlListResponse:
    def run(sync_session):
        service = RawCollectionService(sync_session)
        return CandidateUrlListResponse(
            items=[serialize_candidate(candidate) for candidate in service.list_candidate_urls(task_id=task_id, limit=limit)]
        )

    return await async_session.run_sync(run)
