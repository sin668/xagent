from collections.abc import AsyncIterator
from datetime import date
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.schemas.dashboard import (
    AdminOverviewResponse,
    ChannelLeadDashboardResponse,
    ChannelQualityDashboardResponse,
    EmailDeliveryQualityResponse,
    EmailReplyQualityResponse,
    Phase5E2EIntegrationReportResponse,
    Phase5GoNoGoReportResponse,
    Phase5QualityFoundationResponse,
    PhaseOneFunnelDashboardResponse,
    RiskEventDashboardResponse,
)
from app.schemas.dashboard import OutreachSlaDashboardResponse
from app.schemas.dashboard import RoiCostCreateRequest, RoiCostResponse, RoiMetricsResponse
from app.services.dashboard import DashboardService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
REPO_ROOT = Path(__file__).resolve().parents[4]


async def get_async_session() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session


@router.get("/channel-leads", response_model=ChannelLeadDashboardResponse)
async def get_channel_lead_dashboard(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    async_session: AsyncSession = Depends(get_async_session),
) -> ChannelLeadDashboardResponse:
    def run(sync_session):
        service = DashboardService(sync_session)
        return ChannelLeadDashboardResponse(**service.channel_lead_metrics(date_from=date_from, date_to=date_to))

    return await async_session.run_sync(run)


@router.get("/admin-overview", response_model=AdminOverviewResponse)
async def get_admin_overview(
    async_session: AsyncSession = Depends(get_async_session),
) -> AdminOverviewResponse:
    def run(sync_session):
        service = DashboardService(sync_session)
        return AdminOverviewResponse(**service.admin_overview())

    return await async_session.run_sync(run)


@router.get("/email-delivery-quality", response_model=EmailDeliveryQualityResponse)
async def get_email_delivery_quality(
    async_session: AsyncSession = Depends(get_async_session),
) -> EmailDeliveryQualityResponse:
    def run(sync_session):
        service = DashboardService(sync_session)
        return EmailDeliveryQualityResponse(**service.email_delivery_quality_metrics())

    return await async_session.run_sync(run)


@router.get("/email-reply-quality", response_model=EmailReplyQualityResponse)
async def get_email_reply_quality(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    language: str | None = Query(default=None),
    business_scene: str | None = Query(default=None),
    async_session: AsyncSession = Depends(get_async_session),
) -> EmailReplyQualityResponse:
    def run(sync_session):
        service = DashboardService(sync_session)
        return EmailReplyQualityResponse(
            **service.email_reply_quality_metrics(
                date_from=date_from,
                date_to=date_to,
                language=language,
                business_scene=business_scene,
            )
        )

    return await async_session.run_sync(run)


@router.get("/phase5-quality-foundation", response_model=Phase5QualityFoundationResponse)
async def get_phase5_quality_foundation(
    knowledge_collection_prefix: str | None = Query(default=None),
    async_session: AsyncSession = Depends(get_async_session),
) -> Phase5QualityFoundationResponse:
    def run(sync_session):
        service = DashboardService(sync_session)
        return Phase5QualityFoundationResponse(
            **service.phase5_quality_foundation_metrics(
                repo_root=REPO_ROOT,
                knowledge_collection_prefix=knowledge_collection_prefix,
            )
        )

    return await async_session.run_sync(run)


@router.get("/phase5-go-no-go-report", response_model=Phase5GoNoGoReportResponse)
async def get_phase5_go_no_go_report(
    knowledge_collection_prefix: str | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    language: str | None = Query(default=None),
    business_scene: str | None = Query(default=None),
    async_session: AsyncSession = Depends(get_async_session),
) -> Phase5GoNoGoReportResponse:
    def run(sync_session):
        service = DashboardService(sync_session)
        return Phase5GoNoGoReportResponse(
            **service.phase5_go_no_go_report(
                repo_root=REPO_ROOT,
                knowledge_collection_prefix=knowledge_collection_prefix,
                date_from=date_from,
                date_to=date_to,
                language=language,
                business_scene=business_scene,
            )
        )

    return await async_session.run_sync(run)


@router.get("/phase5-e2e-integration-report", response_model=Phase5E2EIntegrationReportResponse)
async def get_phase5_e2e_integration_report(
    knowledge_collection_prefix: str | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    language: str | None = Query(default=None),
    business_scene: str | None = Query(default=None),
    async_session: AsyncSession = Depends(get_async_session),
) -> Phase5E2EIntegrationReportResponse:
    def run(sync_session):
        service = DashboardService(sync_session)
        return Phase5E2EIntegrationReportResponse(
            **service.phase5_e2e_integration_report(
                repo_root=REPO_ROOT,
                knowledge_collection_prefix=knowledge_collection_prefix,
                date_from=date_from,
                date_to=date_to,
                language=language,
                business_scene=business_scene,
            )
        )

    return await async_session.run_sync(run)


@router.get("/phase-one-funnel", response_model=PhaseOneFunnelDashboardResponse)
async def get_phase_one_funnel_dashboard(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    channel: str | None = Query(
        default=None,
        pattern="^(official_website|public_directory|search_engine|google_maps|yandex_maps|youtube|drom|other|vkontakte|facebook)$",
    ),
    risk_level: str | None = Query(default=None, pattern="^(Low|Medium|High|Forbidden)$"),
    daily_candidate_target: int = Query(default=100, ge=1),
    async_session: AsyncSession = Depends(get_async_session),
) -> PhaseOneFunnelDashboardResponse:
    def run(sync_session):
        service = DashboardService(sync_session)
        return PhaseOneFunnelDashboardResponse(
            **service.phase_one_funnel_metrics(
                date_from=date_from,
                date_to=date_to,
                channel=channel,
                risk_level=risk_level,
                daily_candidate_target=daily_candidate_target,
            )
        )

    return await async_session.run_sync(run)


@router.get("/channel-quality", response_model=ChannelQualityDashboardResponse)
async def get_channel_quality_dashboard(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    channel: str | None = Query(
        default=None,
        pattern="^(official_website|public_directory|search_engine|google_maps|yandex_maps|youtube|drom|other|vkontakte|facebook)$",
    ),
    risk_level: str | None = Query(default=None, pattern="^(Low|Medium|High|Forbidden)$"),
    async_session: AsyncSession = Depends(get_async_session),
) -> ChannelQualityDashboardResponse:
    def run(sync_session):
        service = DashboardService(sync_session)
        return ChannelQualityDashboardResponse(
            **service.channel_quality_metrics(
                date_from=date_from,
                date_to=date_to,
                channel=channel,
                risk_level=risk_level,
            )
        )

    return await async_session.run_sync(run)


@router.get("/risk-events", response_model=RiskEventDashboardResponse)
async def get_risk_event_dashboard(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    channel: str | None = Query(
        default=None,
        pattern="^(official_website|public_directory|search_engine|google_maps|yandex_maps|youtube|drom|other|vkontakte|facebook)$",
    ),
    risk_level: str | None = Query(default=None, pattern="^(Low|Medium|High|Forbidden)$"),
    severity: str | None = Query(default=None, pattern="^(low|medium|high|critical)$"),
    resolution_status: str | None = Query(default=None, pattern="^(open|investigating|resolved|dismissed)$"),
    async_session: AsyncSession = Depends(get_async_session),
) -> RiskEventDashboardResponse:
    def run(sync_session):
        service = DashboardService(sync_session)
        return RiskEventDashboardResponse(
            **service.risk_event_dashboard(
                date_from=date_from,
                date_to=date_to,
                channel=channel,
                risk_level=risk_level,
                severity=severity,
                resolution_status=resolution_status,
            )
        )

    return await async_session.run_sync(run)


def serialize_roi_cost(entry) -> RoiCostResponse:
    return RoiCostResponse(
        id=str(entry.id),
        external_id=entry.external_id,
        cost_type=entry.cost_type,
        amount=float(entry.amount),
        currency=entry.currency,
        labor_hours=float(entry.labor_hours) if entry.labor_hours is not None else None,
        hourly_rate=float(entry.hourly_rate) if entry.hourly_rate is not None else None,
        channel_name=entry.channel_name,
        notes=entry.notes,
    )


@router.post("/roi-costs", response_model=RoiCostResponse)
async def create_roi_cost(
    request: RoiCostCreateRequest,
    async_session: AsyncSession = Depends(get_async_session),
) -> RoiCostResponse:
    def run(sync_session):
        service = DashboardService(sync_session)
        try:
            entry = service.create_roi_cost(
                external_id=request.external_id,
                cost_type=request.cost_type,
                amount=request.amount,
                currency=request.currency,
                labor_hours=request.labor_hours,
                hourly_rate=request.hourly_rate,
                channel_name=request.channel_name,
                notes=request.notes,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        sync_session.commit()
        return serialize_roi_cost(entry)

    return await async_session.run_sync(run)


@router.get("/roi-metrics", response_model=RoiMetricsResponse)
async def get_roi_metrics(
    channel: str | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    async_session: AsyncSession = Depends(get_async_session),
) -> RoiMetricsResponse:
    def run(sync_session):
        service = DashboardService(sync_session)
        return RoiMetricsResponse(**service.roi_metrics(channel=channel, date_from=date_from, date_to=date_to))

    return await async_session.run_sync(run)


@router.get("/outreach-sla", response_model=OutreachSlaDashboardResponse)
async def get_outreach_sla_dashboard(
    owner: str | None = Query(default=None),
    grade: str | None = Query(default=None, pattern="^(B|C)$"),
    channel: str | None = Query(
        default=None,
        pattern="^(email|phone|whatsapp|telegram|vkontakte|odnoklassniki|tiktok|max|website|website_form|other)$",
    ),
    async_session: AsyncSession = Depends(get_async_session),
) -> OutreachSlaDashboardResponse:
    def run(sync_session):
        service = DashboardService(sync_session)
        return OutreachSlaDashboardResponse(
            **service.outreach_sla_metrics(owner=owner, grade=grade, channel=channel)
        )

    return await async_session.run_sync(run)
