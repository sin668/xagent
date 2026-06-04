from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.schemas.failed_cases import FailedCaseCreate, FailedCaseListResponse, FailedCaseResponse
from app.services.failed_cases import FailedCaseService

router = APIRouter(prefix="/failed-cases", tags=["failed-cases"])


async def get_async_session() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session


def serialize_failed_case(record) -> FailedCaseResponse:
    return FailedCaseResponse(
        id=record.id,
        case_type=record.case_type.value,
        source_url=record.source_url,
        risk_level=record.risk_level.value if record.risk_level is not None else None,
        related_task_type=record.related_task_type,
        related_object_type=record.related_object_type,
        related_object_id=record.related_object_id,
        failure_reason=record.failure_reason,
        evidence_note=record.evidence_note,
        raw_input_ref=record.raw_input_ref,
        raw_output_json=record.raw_output_json,
        model_name=record.model_name,
        prompt_version=record.prompt_version,
        usable_for_rag=record.usable_for_rag,
        touch_queue_allowed=record.touch_queue_allowed,
        created_at=record.created_at.isoformat(),
    )


@router.post("", response_model=FailedCaseResponse)
async def create_failed_case(
    request: FailedCaseCreate,
    async_session: AsyncSession = Depends(get_async_session),
) -> FailedCaseResponse:
    def run(sync_session):
        service = FailedCaseService(sync_session)
        try:
            record = service.record_failed_case(**request.model_dump())
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        sync_session.commit()
        return serialize_failed_case(record)

    return await async_session.run_sync(run)


@router.get("", response_model=FailedCaseListResponse)
async def list_failed_cases(
    case_type: str | None = Query(
        default=None,
        pattern="^(fetch_failed|schema_invalid|missing_evidence|risk_blocked|duplicate|llm_suspected_fabrication)$",
    ),
    usable_for_rag: bool | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    async_session: AsyncSession = Depends(get_async_session),
) -> FailedCaseListResponse:
    def run(sync_session):
        service = FailedCaseService(sync_session)
        return FailedCaseListResponse(
            items=[
                serialize_failed_case(record)
                for record in service.list_failed_cases(
                    case_type=case_type,
                    usable_for_rag=usable_for_rag,
                    limit=limit,
                )
            ]
        )

    return await async_session.run_sync(run)

