from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.schemas.sync import SyncAuditDashboardResponse, SyncRequest, SyncResponse
from app.services.feishu_client import FeishuApiClient
from app.services.sync_audit_dashboard import SyncAuditDashboardService
from app.services.sync_service import FeishuSyncService
from app.settings import settings

router = APIRouter(prefix="/sync", tags=["sync"])


async def get_async_session() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session


def get_feishu_client() -> FeishuApiClient:
    return FeishuApiClient(
        app_id=settings.feishu_app_id,
        app_secret=settings.feishu_app_secret,
        bitable_app_token=settings.feishu_bitable_app_token,
    )


def get_sync_service() -> FeishuSyncService:
    client = FeishuApiClient(
        app_id=settings.feishu_app_id,
        app_secret=settings.feishu_app_secret,
        bitable_app_token=settings.feishu_bitable_app_token,
    )
    return FeishuSyncService(client=client)


@router.post("/feishu", response_model=SyncResponse)
async def trigger_feishu_sync(
    request: SyncRequest,
    async_session: AsyncSession = Depends(get_async_session),
    client: FeishuApiClient = Depends(get_feishu_client),
) -> SyncResponse:
    def run_sync(sync_session):
        service = FeishuSyncService(client=client, session=None if request.dry_run else sync_session)
        result = service.sync(object_names=request.object_names, dry_run=request.dry_run)
        if not request.dry_run:
            sync_session.commit()
        return result

    result = await async_session.run_sync(run_sync)
    return SyncResponse(
        status=result.status,
        dry_run=result.dry_run,
        results=[
            {
                "object_name": item.object_name,
                "success_count": item.success_count,
                "failure_count": item.failure_count,
                "skipped_count": item.skipped_count,
                "errors": item.errors,
            }
            for item in result.results
        ],
    )


@router.get("/audit-dashboard", response_model=SyncAuditDashboardResponse)
async def get_sync_ai_audit_dashboard(
    task_type: str | None = Query(
        default=None,
        pattern="^(lead_extraction|lead_grading|outreach_draft|inventory_matching|risk_block)$",
    ),
    status: str | None = Query(default=None, pattern="^(blocked|succeeded)$"),
    source_name: str | None = Query(default=None),
    model_name: str | None = Query(default=None),
    async_session: AsyncSession = Depends(get_async_session),
) -> SyncAuditDashboardResponse:
    def run(sync_session):
        service = SyncAuditDashboardService(sync_session)
        return SyncAuditDashboardResponse(
            **service.dashboard(
                task_type=task_type,
                status=status,
                source_name=source_name,
                model_name=model_name,
            )
        )

    return await async_session.run_sync(run)
