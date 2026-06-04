from collections.abc import AsyncIterator
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.schemas.risk_events import RiskEventCreate, RiskEventListResponse, RiskEventResolve, RiskEventResponse
from app.services.audit_risk import AuditRiskLogService

router = APIRouter(prefix="/risk-events", tags=["risk-events"])


async def get_async_session() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session


def serialize_event(event) -> RiskEventResponse:
    return RiskEventResponse(
        id=event.id,
        channel_plan_id=event.channel_plan_id,
        task_id=event.task_id,
        agent_name=event.agent_name,
        action=event.action,
        channel=event.channel,
        risk_level=event.risk_level.value,
        event_type=event.event_type,
        severity=event.severity.value,
        resolution_status=event.resolution_status.value,
        block_reason=event.block_reason,
        pause_suggested=event.pause_suggested,
        resolution_note=event.resolution_note,
        resolved_by=event.resolved_by,
        input_ref=event.input_ref,
        output_ref=event.output_ref,
        result=event.result,
        error_message=event.error_message,
        created_at=event.created_at.isoformat(),
        resolved_at=event.resolved_at.isoformat() if event.resolved_at else None,
    )


@router.post("", response_model=RiskEventResponse)
async def create_risk_event(
    request: RiskEventCreate,
    async_session: AsyncSession = Depends(get_async_session),
) -> RiskEventResponse:
    def run(sync_session):
        service = AuditRiskLogService(sync_session)
        event = service.record_risk_event(**request.model_dump())
        sync_session.commit()
        return serialize_event(event)

    return await async_session.run_sync(run)


@router.get("", response_model=RiskEventListResponse)
async def list_risk_events(
    severity: str | None = Query(default=None, pattern="^(low|medium|high|critical)$"),
    resolution_status: str | None = Query(default=None, pattern="^(open|investigating|resolved|dismissed)$"),
    channel_plan_id: UUID | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    async_session: AsyncSession = Depends(get_async_session),
) -> RiskEventListResponse:
    def run(sync_session):
        service = AuditRiskLogService(sync_session)
        return RiskEventListResponse(
            items=[
                serialize_event(event)
                for event in service.list_risk_events(
                    severity=severity,
                    resolution_status=resolution_status,
                    channel_plan_id=channel_plan_id,
                    limit=limit,
                )
            ]
        )

    return await async_session.run_sync(run)


@router.post("/{event_id:uuid}/resolve", response_model=RiskEventResponse)
async def resolve_risk_event(
    event_id: UUID,
    request: RiskEventResolve,
    async_session: AsyncSession = Depends(get_async_session),
) -> RiskEventResponse:
    def run(sync_session):
        service = AuditRiskLogService(sync_session)
        try:
            event = service.resolve_risk_event(
                event_id=event_id,
                resolution_note=request.resolution_note,
                resolved_by=request.resolved_by,
            )
        except ValueError as exc:
            message = str(exc)
            status_code = 404 if "不存在" in message else 422
            raise HTTPException(status_code=status_code, detail=message) from exc
        sync_session.commit()
        return serialize_event(event)

    return await async_session.run_sync(run)
