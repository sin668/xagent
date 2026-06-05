from collections.abc import AsyncIterator
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.schemas.knowledge import (
    KnowledgeCollectionCreate,
    KnowledgeCollectionListResponse,
    KnowledgeCollectionResponse,
    KnowledgeEmbeddingCreate,
    KnowledgeEmbeddingResponse,
    KnowledgeItemCreate,
    KnowledgeItemListResponse,
    KnowledgeItemResponse,
    KnowledgeItemUpdate,
    KnowledgeReviewActionRequest,
    KnowledgeReviewLogListResponse,
    KnowledgeReviewLogResponse,
    KnowledgeRetrievalFilterRequest,
    KnowledgeRetrievalFilterResponse,
    KnowledgeRetrievalFilterResultResponse,
    KnowledgeQualitySummaryResponse,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
    KnowledgeSearchResultResponse,
    KnowledgeUsageRecordCreate,
    KnowledgeUsageRecordResponse,
    PhaseOneKnowledgeImportRequest,
    PhaseOneKnowledgeImportResponse,
)
from app.services.agent_thread_runner import AgentThreadRunner
from app.services.embedding_provider import create_embedding_provider
from app.services.knowledge import KnowledgeService
from app.services.knowledge_embedding_worker import KnowledgeEmbeddingWorker
from app.services.knowledge_import import KnowledgeImportService
from app.services.knowledge_search import KnowledgeSearchService

router = APIRouter(prefix="/knowledge", tags=["knowledge"])
REPO_ROOT = Path(__file__).resolve().parents[4]


async def get_async_session() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session


def serialize_collection(collection) -> KnowledgeCollectionResponse:
    return KnowledgeCollectionResponse(
        id=collection.id,
        name=collection.name,
        description=collection.description,
        status=collection.status.value,
        review_status=collection.review_status.value,
        version=collection.version,
        source_ref=collection.source_ref,
        created_at=collection.created_at.isoformat(),
        updated_at=collection.updated_at.isoformat(),
    )


def serialize_item(item) -> KnowledgeItemResponse:
    metadata = item.metadata_json or {}
    return KnowledgeItemResponse(
        id=item.id,
        collection_id=item.collection_id,
        title=item.title,
        body=item.body,
        language=item.language,
        country=item.country,
        applicable_channels=item.applicable_channels,
        status=item.status.value,
        review_status=item.review_status.value,
        source_ref=item.source_ref,
        version=item.version,
        metadata_json=item.metadata_json,
        content_type=metadata.get("content_type"),
        business_scene=metadata.get("business_scene"),
        risk_level=metadata.get("risk_level"),
        auto_reply_allowed=metadata.get("auto_reply_allowed"),
        market=metadata.get("market"),
        tone=metadata.get("tone"),
        rag_eligible=KnowledgeService.is_rag_eligible(status=item.status, review_status=item.review_status),
        created_at=item.created_at.isoformat(),
        updated_at=item.updated_at.isoformat(),
    )


def serialize_embedding(record) -> KnowledgeEmbeddingResponse:
    return KnowledgeEmbeddingResponse(
        id=record.id,
        item_id=record.item_id,
        embedding_model=record.embedding_model,
        embedding_dimensions=record.embedding_dimensions,
        embedding_status=record.embedding_status.value,
        error_message=record.error_message,
        created_at=record.created_at.isoformat(),
    )


def serialize_review_log(log) -> KnowledgeReviewLogResponse:
    return KnowledgeReviewLogResponse(
        id=log.id,
        item_id=log.task_id,
        action=log.action,
        reviewer=log.reviewer,
        input_ref=log.input_ref,
        output_ref=log.output_ref,
        result=log.result,
        error_message=log.error_message,
        created_at=log.created_at.isoformat(),
    )


def serialize_retrieval_filter_result(result) -> KnowledgeRetrievalFilterResultResponse:
    metadata = result.item.metadata_json or {}
    return KnowledgeRetrievalFilterResultResponse(
        knowledge_item_id=result.item.id,
        version=result.item.version,
        similarity_score=result.similarity_score,
        title=result.item.title,
        content_type=metadata.get("content_type"),
        business_scene=metadata.get("business_scene"),
        filter_conditions=result.filter_conditions,
    )


def serialize_usage_record(record) -> KnowledgeUsageRecordResponse:
    return KnowledgeUsageRecordResponse(
        id=record.id,
        knowledge_item_id=record.knowledge_item_id,
        knowledge_version=record.knowledge_version,
        email_reply_draft_id=record.email_reply_draft_id,
        retrieval_query=record.retrieval_query,
        similarity_score=record.similarity_score,
        rank=record.rank,
        filters_json=record.filters_json,
        outcome=record.outcome.value,
        adopted=record.adopted,
        edit_distance_ratio=record.edit_distance_ratio,
        caused_bounce=record.caused_bounce,
        customer_replied=record.customer_replied,
        suggest_deprecate=record.suggest_deprecate,
        suggest_deprecate_reason=record.suggest_deprecate_reason,
        created_at=record.created_at.isoformat(),
    )


@router.post("/collections", response_model=KnowledgeCollectionResponse)
async def create_collection(
    request: KnowledgeCollectionCreate,
    async_session: AsyncSession = Depends(get_async_session),
) -> KnowledgeCollectionResponse:
    def run(sync_session):
        collection = KnowledgeService(sync_session).create_collection(**request.model_dump())
        sync_session.commit()
        return serialize_collection(collection)

    return await async_session.run_sync(run)


@router.get("/collections", response_model=KnowledgeCollectionListResponse)
async def list_collections(
    limit: int = Query(default=100, ge=1, le=500),
    async_session: AsyncSession = Depends(get_async_session),
) -> KnowledgeCollectionListResponse:
    def run(sync_session):
        return KnowledgeCollectionListResponse(
            items=[serialize_collection(item) for item in KnowledgeService(sync_session).list_collections(limit=limit)]
        )

    return await async_session.run_sync(run)


@router.post("/items", response_model=KnowledgeItemResponse)
async def create_item(
    request: KnowledgeItemCreate,
    async_session: AsyncSession = Depends(get_async_session),
) -> KnowledgeItemResponse:
    def run(sync_session):
        service = KnowledgeService(sync_session)
        try:
            item = service.create_item(**request.model_dump())
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        sync_session.commit()
        return serialize_item(item)

    return await async_session.run_sync(run)


@router.get("/items", response_model=KnowledgeItemListResponse)
async def list_items(
    production_rag_only: bool = False,
    status: str | None = Query(default=None, pattern="^(draft|active|deprecated|disabled)$"),
    review_status: str | None = Query(default=None, pattern="^(pending|approved|rejected)$"),
    language: str | None = Query(default=None),
    content_type: str | None = Query(
        default=None,
        pattern="^(qa_entry|email_reply_template|compliance_phrase|vehicle_product_note|process_sop)$",
    ),
    business_scene: str | None = Query(default=None),
    risk_level: str | None = Query(default=None),
    auto_reply_allowed: bool | None = Query(default=None),
    market: str | None = Query(default=None),
    tone: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    async_session: AsyncSession = Depends(get_async_session),
) -> KnowledgeItemListResponse:
    def run(sync_session):
        return KnowledgeItemListResponse(
            items=[
                serialize_item(item)
                for item in KnowledgeService(sync_session).list_items(
                    production_rag_only=production_rag_only,
                    status=status,
                    review_status=review_status,
                    language=language,
                    content_type=content_type,
                    business_scene=business_scene,
                    risk_level=risk_level,
                    auto_reply_allowed=auto_reply_allowed,
                    market=market,
                    tone=tone,
                    limit=limit,
                )
            ]
        )

    return await async_session.run_sync(run)


@router.get("/items/{item_id:uuid}", response_model=KnowledgeItemResponse)
async def get_item(
    item_id: UUID,
    async_session: AsyncSession = Depends(get_async_session),
) -> KnowledgeItemResponse:
    def run(sync_session):
        item = KnowledgeService(sync_session).get_item(item_id)
        if item is None:
            raise HTTPException(status_code=404, detail="knowledge item 不存在。")
        return serialize_item(item)

    return await async_session.run_sync(run)


@router.patch("/items/{item_id:uuid}", response_model=KnowledgeItemResponse)
async def update_item(
    item_id: UUID,
    request: KnowledgeItemUpdate,
    async_session: AsyncSession = Depends(get_async_session),
) -> KnowledgeItemResponse:
    def run(sync_session):
        service = KnowledgeService(sync_session)
        try:
            item = service.update_item(item_id, payload=request.model_dump(exclude_unset=True))
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        sync_session.commit()
        return serialize_item(item)

    return await async_session.run_sync(run)


@router.post("/items/{item_id:uuid}/submit-review", response_model=KnowledgeItemResponse)
async def submit_item_review(
    item_id: UUID,
    request: KnowledgeReviewActionRequest,
    async_session: AsyncSession = Depends(get_async_session),
) -> KnowledgeItemResponse:
    def run(sync_session):
        service = KnowledgeService(sync_session)
        try:
            item = service.submit_review(
                item_id,
                actor=request.actor,
                actor_role=request.actor_role,
                review_note=request.review_note,
            )
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        sync_session.commit()
        return serialize_item(item)

    return await async_session.run_sync(run)


@router.post("/items/{item_id:uuid}/publish", response_model=KnowledgeItemResponse)
async def publish_item(
    item_id: UUID,
    request: KnowledgeReviewActionRequest,
    async_session: AsyncSession = Depends(get_async_session),
) -> KnowledgeItemResponse:
    queued_embedding_id: UUID | None = None

    def run(sync_session):
        nonlocal queued_embedding_id
        service = KnowledgeService(sync_session)
        try:
            item = service.publish_item(
                item_id,
                actor=request.actor,
                actor_role=request.actor_role,
                review_note=request.review_note,
            )
            provider = create_embedding_provider()
            embedding_task = service.create_pending_embedding_task(
                item_id=item.id,
                embedding_model=provider.model,
                embedding_dimensions=provider.dimensions,
            )
            queued_embedding_id = embedding_task.id
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        sync_session.commit()
        return serialize_item(item)

    response = await async_session.run_sync(run)
    if queued_embedding_id is not None:
        provider = create_embedding_provider()
        worker = KnowledgeEmbeddingWorker(provider)
        AgentThreadRunner.start(
            name=f"knowledge-embedding-worker-{queued_embedding_id}",
            target=lambda: worker.run_once(queued_embedding_id),
        )
    return response


@router.post("/items/{item_id:uuid}/activate-retrieval", response_model=KnowledgeItemResponse)
async def activate_item_retrieval(
    item_id: UUID,
    request: KnowledgeReviewActionRequest,
    async_session: AsyncSession = Depends(get_async_session),
) -> KnowledgeItemResponse:
    def run(sync_session):
        service = KnowledgeService(sync_session)
        try:
            item = service.activate_retrieval(
                item_id,
                actor=request.actor,
                actor_role=request.actor_role,
                review_note=request.review_note,
            )
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        sync_session.commit()
        return serialize_item(item)

    return await async_session.run_sync(run)


@router.post("/items/{item_id:uuid}/archive", response_model=KnowledgeItemResponse)
async def archive_item(
    item_id: UUID,
    request: KnowledgeReviewActionRequest,
    async_session: AsyncSession = Depends(get_async_session),
) -> KnowledgeItemResponse:
    def run(sync_session):
        service = KnowledgeService(sync_session)
        try:
            item = service.archive_item(
                item_id,
                actor=request.actor,
                actor_role=request.actor_role,
                review_note=request.review_note,
            )
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        sync_session.commit()
        return serialize_item(item)

    return await async_session.run_sync(run)


@router.post("/items/{item_id:uuid}/block", response_model=KnowledgeItemResponse)
async def block_item(
    item_id: UUID,
    request: KnowledgeReviewActionRequest,
    async_session: AsyncSession = Depends(get_async_session),
) -> KnowledgeItemResponse:
    def run(sync_session):
        service = KnowledgeService(sync_session)
        try:
            item = service.block_item(
                item_id,
                actor=request.actor,
                actor_role=request.actor_role,
                review_note=request.review_note,
            )
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        sync_session.commit()
        return serialize_item(item)

    return await async_session.run_sync(run)


@router.get("/items/{item_id:uuid}/review-logs", response_model=KnowledgeReviewLogListResponse)
async def list_item_review_logs(
    item_id: UUID,
    async_session: AsyncSession = Depends(get_async_session),
) -> KnowledgeReviewLogListResponse:
    def run(sync_session):
        service = KnowledgeService(sync_session)
        item = service.get_item(item_id)
        if item is None:
            raise HTTPException(status_code=404, detail="knowledge item 不存在。")
        logs = [serialize_review_log(log) for log in service.list_review_logs(item_id)]
        return KnowledgeReviewLogListResponse(items=logs, total=len(logs))

    return await async_session.run_sync(run)


@router.post("/items/{item_id}/embedding", response_model=KnowledgeEmbeddingResponse)
@router.post("/items/{item_id:uuid}/embedding", response_model=KnowledgeEmbeddingResponse)
async def create_embedding(
    item_id: UUID,
    request: KnowledgeEmbeddingCreate,
    async_session: AsyncSession = Depends(get_async_session),
) -> KnowledgeEmbeddingResponse:
    def run(sync_session):
        service = KnowledgeService(sync_session)
        try:
            record = service.create_embedding(item_id=item_id, **request.model_dump())
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        sync_session.commit()
        return serialize_embedding(record)

    return await async_session.run_sync(run)


@router.post("/embeddings/{embedding_id:uuid}/retry", response_model=KnowledgeEmbeddingResponse)
async def retry_embedding(
    embedding_id: UUID,
    async_session: AsyncSession = Depends(get_async_session),
) -> KnowledgeEmbeddingResponse:
    def run(sync_session):
        service = KnowledgeService(sync_session)
        try:
            record = service.retry_embedding(embedding_id)
        except PermissionError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        sync_session.commit()
        return serialize_embedding(record)

    return await async_session.run_sync(run)


@router.post("/import/phase-one", response_model=PhaseOneKnowledgeImportResponse)
async def import_phase_one_knowledge(
    request: PhaseOneKnowledgeImportRequest,
    async_session: AsyncSession = Depends(get_async_session),
) -> PhaseOneKnowledgeImportResponse:
    def run(sync_session):
        result = KnowledgeImportService(sync_session).import_phase_one(REPO_ROOT, dry_run=request.dry_run)
        if not request.dry_run:
            sync_session.commit()
        return PhaseOneKnowledgeImportResponse(
            imported_count=result.imported_count,
            skipped_count=result.skipped_count,
            collection_names=result.collection_names,
            item_titles=result.item_titles,
        )

    return await async_session.run_sync(run)


@router.post("/items/{item_id:uuid}/usage-records", response_model=KnowledgeUsageRecordResponse)
async def create_item_usage_record(
    item_id: UUID,
    request: KnowledgeUsageRecordCreate,
    async_session: AsyncSession = Depends(get_async_session),
) -> KnowledgeUsageRecordResponse:
    def run(sync_session):
        service = KnowledgeService(sync_session)
        try:
            record = service.create_usage_record(item_id, payload=request.model_dump())
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        sync_session.commit()
        return serialize_usage_record(record)

    return await async_session.run_sync(run)


@router.get("/items/{item_id:uuid}/quality-summary", response_model=KnowledgeQualitySummaryResponse)
async def get_item_quality_summary(
    item_id: UUID,
    async_session: AsyncSession = Depends(get_async_session),
) -> KnowledgeQualitySummaryResponse:
    def run(sync_session):
        service = KnowledgeService(sync_session)
        try:
            summary = service.quality_summary(item_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return KnowledgeQualitySummaryResponse(**summary)

    return await async_session.run_sync(run)


@router.post("/retrieval-filter", response_model=KnowledgeRetrievalFilterResponse)
async def retrieval_filter_knowledge(
    request: KnowledgeRetrievalFilterRequest,
    async_session: AsyncSession = Depends(get_async_session),
) -> KnowledgeRetrievalFilterResponse:
    def run(sync_session):
        service = KnowledgeSearchService(sync_session)
        results, rejection_reason = service.retrieve_for_email_reply(**request.model_dump())
        return KnowledgeRetrievalFilterResponse(
            items=[serialize_retrieval_filter_result(result) for result in results],
            total=len(results),
            rejection_reason=rejection_reason,
        )

    return await async_session.run_sync(run)


@router.post("/search", response_model=KnowledgeSearchResponse)
async def search_knowledge(
    request: KnowledgeSearchRequest,
    async_session: AsyncSession = Depends(get_async_session),
) -> KnowledgeSearchResponse:
    def run(sync_session):
        service = KnowledgeSearchService(sync_session)
        try:
            results, mode = service.search(**request.model_dump())
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return KnowledgeSearchResponse(
            items=[
                KnowledgeSearchResultResponse(
                    item=serialize_item(result.item),
                    score=result.score,
                    match_reason=result.match_reason,
                    search_mode=result.search_mode,
                )
                for result in results
            ],
            search_mode=mode["search_mode"],
            fallback_reason=mode.get("fallback_reason"),
        )

    return await async_session.run_sync(run)
