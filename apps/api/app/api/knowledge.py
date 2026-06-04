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
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
    KnowledgeSearchResultResponse,
    PhaseOneKnowledgeImportRequest,
    PhaseOneKnowledgeImportResponse,
)
from app.services.knowledge import KnowledgeService
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
    limit: int = Query(default=100, ge=1, le=500),
    async_session: AsyncSession = Depends(get_async_session),
) -> KnowledgeItemListResponse:
    def run(sync_session):
        return KnowledgeItemListResponse(
            items=[
                serialize_item(item)
                for item in KnowledgeService(sync_session).list_items(
                    production_rag_only=production_rag_only,
                    limit=limit,
                )
            ]
        )

    return await async_session.run_sync(run)


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
