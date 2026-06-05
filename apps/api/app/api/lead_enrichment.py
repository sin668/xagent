from collections.abc import AsyncIterator
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.schemas.lead_enrichment_field_candidate import (
    LeadEnrichmentFieldCandidateAccept,
    LeadEnrichmentFieldCandidateReject,
    LeadEnrichmentFieldCandidateResponse,
    LeadEnrichmentFieldCandidateUpdate,
)
from app.schemas.lead_enrichment import (
    LeadEnrichmentResultItem,
    LeadEnrichmentResultsResponse,
    LeadEnrichmentRunCreate,
    LeadEnrichmentRunResponse,
    ManualEnrichmentCreate,
)
from app.services.lead_enrichment import LeadEnrichmentService, select_deep_enrichment_runtime
from app.settings import settings


router = APIRouter(prefix="/staging-leads", tags=["lead-enrichment"])
field_candidate_router = APIRouter(prefix="/lead-enrichment-field-candidates", tags=["lead-enrichment"])


async def get_async_session() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session


def serialize_enrichment_run(run, *, quota_daily_limit: int, quota_used_today: int) -> LeadEnrichmentRunResponse:
    return LeadEnrichmentRunResponse(
        id=run.id,
        staging_lead_id=run.staging_lead_id,
        enrichment_type=run.enrichment_type,
        triggered_by=run.triggered_by,
        status=run.status,
        input_snapshot_json=run.input_snapshot_json,
        output_json=run.output_json,
        evidence_links=run.evidence_links,
        confidence_score=run.confidence_score,
        missing_fields=run.missing_fields,
        recommended_action=run.recommended_action,
        agent_task_run_id=run.agent_task_run_id,
        quota_daily_limit=quota_daily_limit,
        quota_used_today=quota_used_today,
        created_at=run.created_at,
        updated_at=run.updated_at,
    )


@router.post("/{lead_id:uuid}/enrichment-runs", response_model=LeadEnrichmentRunResponse)
async def create_lead_enrichment_run(
    lead_id: UUID,
    request: LeadEnrichmentRunCreate,
    async_session: AsyncSession = Depends(get_async_session),
) -> LeadEnrichmentRunResponse:
    def run(sync_session):
        service = LeadEnrichmentService(sync_session)
        lead = service.get_staging_lead(lead_id)
        if lead is None:
            raise HTTPException(status_code=404, detail="staging lead not found")
        try:
            enrichment_run, quota = service.create_pending_run(
                lead,
                request=request,
                daily_limit=settings.lead_enrichment_daily_quota_per_lead,
            )
            runtime = select_deep_enrichment_runtime(settings)
            if runtime is not None:
                service.run_deep_enrichment_agent(
                    enrichment_run,
                    runtime=runtime,
                    agents_base_url=settings.agents_base_url,
                )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        sync_session.commit()
        sync_session.refresh(enrichment_run)
        return serialize_enrichment_run(
            enrichment_run,
            quota_daily_limit=quota.daily_limit,
            quota_used_today=quota.used_today,
        )

    return await async_session.run_sync(run)


def serialize_field_candidate_response(candidate) -> LeadEnrichmentFieldCandidateResponse:
    return LeadEnrichmentFieldCandidateResponse(**LeadEnrichmentService.serialize_field_candidate(candidate))


@field_candidate_router.patch("/{candidate_id:uuid}/accept", response_model=LeadEnrichmentFieldCandidateResponse)
async def accept_lead_enrichment_field_candidate(
    candidate_id: UUID,
    request: LeadEnrichmentFieldCandidateAccept,
    async_session: AsyncSession = Depends(get_async_session),
) -> LeadEnrichmentFieldCandidateResponse:
    def run(sync_session):
        service = LeadEnrichmentService(sync_session)
        candidate = service.get_field_candidate(candidate_id)
        if candidate is None:
            raise HTTPException(status_code=404, detail="lead enrichment field candidate not found")
        try:
            accepted = service.accept_field_candidate_with_audit(candidate, request=request)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        sync_session.commit()
        sync_session.refresh(accepted)
        return serialize_field_candidate_response(accepted)

    return await async_session.run_sync(run)


@field_candidate_router.patch("/{candidate_id:uuid}/reject", response_model=LeadEnrichmentFieldCandidateResponse)
async def reject_lead_enrichment_field_candidate(
    candidate_id: UUID,
    request: LeadEnrichmentFieldCandidateReject,
    async_session: AsyncSession = Depends(get_async_session),
) -> LeadEnrichmentFieldCandidateResponse:
    def run(sync_session):
        service = LeadEnrichmentService(sync_session)
        candidate = service.get_field_candidate(candidate_id)
        if candidate is None:
            raise HTTPException(status_code=404, detail="lead enrichment field candidate not found")
        rejected = service.reject_field_candidate_with_audit(candidate, request=request)
        sync_session.commit()
        sync_session.refresh(rejected)
        return serialize_field_candidate_response(rejected)

    return await async_session.run_sync(run)


@field_candidate_router.patch("/{candidate_id:uuid}", response_model=LeadEnrichmentFieldCandidateResponse)
async def update_lead_enrichment_field_candidate(
    candidate_id: UUID,
    request: LeadEnrichmentFieldCandidateUpdate,
    async_session: AsyncSession = Depends(get_async_session),
) -> LeadEnrichmentFieldCandidateResponse:
    def run(sync_session):
        service = LeadEnrichmentService(sync_session)
        candidate = service.get_field_candidate(candidate_id)
        if candidate is None:
            raise HTTPException(status_code=404, detail="lead enrichment field candidate not found")
        updated = service.update_field_candidate(candidate, request=request)
        sync_session.commit()
        sync_session.refresh(updated)
        return serialize_field_candidate_response(updated)

    return await async_session.run_sync(run)


@router.get("/{lead_id:uuid}/enrichment-results", response_model=LeadEnrichmentResultsResponse)
async def list_lead_enrichment_results(
    lead_id: UUID,
    async_session: AsyncSession = Depends(get_async_session),
) -> LeadEnrichmentResultsResponse:
    def run(sync_session):
        service = LeadEnrichmentService(sync_session)
        lead = service.get_staging_lead(lead_id)
        if lead is None:
            raise HTTPException(status_code=404, detail="staging lead not found")
        results = service.list_results_for_lead(lead_id)
        candidates = service.list_field_candidates_for_results([result.id for result in results])
        grouped_candidates = service.group_field_candidates_by_result_id(candidates)
        return LeadEnrichmentResultsResponse(
            staging_lead_id=lead_id,
            items=[
                service.serialize_result_with_candidates(
                    result,
                    grouped_candidates.get(result.id, []),
                )
                for result in results
            ],
        )

    return await async_session.run_sync(run)


@router.post("/{lead_id:uuid}/manual-enrichment", response_model=LeadEnrichmentResultItem)
async def create_manual_enrichment(
    lead_id: UUID,
    request: ManualEnrichmentCreate,
    async_session: AsyncSession = Depends(get_async_session),
) -> LeadEnrichmentResultItem:
    def run(sync_session):
        service = LeadEnrichmentService(sync_session)
        lead = service.get_staging_lead(lead_id)
        if lead is None:
            raise HTTPException(status_code=404, detail="staging lead not found")
        try:
            result, candidates = service.create_manual_enrichment(lead, request=request)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        sync_session.commit()
        sync_session.refresh(result)
        for candidate in candidates:
            sync_session.refresh(candidate)
        return service.serialize_result_with_candidates(result, candidates)

    return await async_session.run_sync(run)
