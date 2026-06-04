from collections.abc import AsyncIterator
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models.enums import (
    ChannelRiskLevel,
    LeadSourceCandidateExtractionStatus,
    LeadSourceCandidateReviewStatus,
    SourcePlatform,
)
from app.schemas.lead_source_candidate import (
    LeadSourceCandidateDetailResponse,
    LeadSourceCandidateListResponse,
    LeadSourceCandidateResponse,
    LeadSourceCandidateReviewActionRequest,
    LeadSourceCandidateReviewActionResponse,
)
from app.services.lead_source_candidates import LeadSourceCandidateService


router = APIRouter(prefix="/lead-source-candidates", tags=["lead-source-candidates"])


async def get_async_session() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session


def serialize_candidate(candidate) -> LeadSourceCandidateResponse:
    return LeadSourceCandidateResponse.model_validate(candidate)


def serialize_candidate_list_item(candidate) -> LeadSourceCandidateResponse:
    return LeadSourceCandidateResponse(
        id=candidate.id,
        source_url=candidate.source_url,
        normalized_domain=candidate.normalized_domain,
        platform=candidate.platform,
        channel_name=candidate.channel_name,
        country=candidate.country,
        city=candidate.city,
        risk_level=candidate.risk_level,
        review_status=candidate.review_status,
        approved_for_extraction=candidate.approved_for_extraction,
        reviewer_id=candidate.reviewer_id,
        review_note=candidate.review_note,
        reviewed_at=candidate.reviewed_at,
        discovery_method=candidate.discovery_method,
        discovery_query=candidate.discovery_query,
        discovery_reason=candidate.discovery_reason,
        evidence_note=candidate.evidence_note,
        evidence_links=candidate.evidence_links,
        llm_provider=candidate.llm_provider,
        llm_model=candidate.llm_model,
        llm_output_json=None,
        confidence_score=candidate.confidence_score,
        extraction_status=candidate.extraction_status,
        last_extracted_at=candidate.last_extracted_at,
        next_retry_at=candidate.next_retry_at,
        retry_count=candidate.retry_count,
        dedupe_key=candidate.dedupe_key,
        duplicate_of_id=candidate.duplicate_of_id,
        is_duplicate=candidate.is_duplicate,
        created_by_task_run_id=candidate.created_by_task_run_id,
        created_at=candidate.created_at,
        updated_at=candidate.updated_at,
    )


def build_llm_output_summary(llm_output_json: dict | None) -> dict:
    if not isinstance(llm_output_json, dict):
        return {}
    candidates = llm_output_json.get("candidates")
    blocked_candidates = llm_output_json.get("blocked_candidates")
    return {
        "task_type": llm_output_json.get("task_type"),
        "country": llm_output_json.get("country"),
        "city": llm_output_json.get("city"),
        "channel_strategy": llm_output_json.get("channel_strategy"),
        "candidate_count": len(candidates) if isinstance(candidates, list) else 0,
        "blocked_count": len(blocked_candidates) if isinstance(blocked_candidates, list) else 0,
    }


def serialize_candidate_detail(candidate) -> LeadSourceCandidateDetailResponse:
    payload = serialize_candidate(candidate).model_dump()
    payload["llm_output_summary"] = build_llm_output_summary(candidate.llm_output_json)
    return LeadSourceCandidateDetailResponse(**payload)


@router.get("", response_model=LeadSourceCandidateListResponse)
async def list_lead_source_candidates(
    risk_level: ChannelRiskLevel | None = None,
    review_status: LeadSourceCandidateReviewStatus | None = None,
    country: str | None = None,
    city: str | None = None,
    platform: SourcePlatform | None = None,
    channel_name: str | None = None,
    extraction_status: LeadSourceCandidateExtractionStatus | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    async_session: AsyncSession = Depends(get_async_session),
) -> LeadSourceCandidateListResponse:
    def run(sync_session):
        items, total = LeadSourceCandidateService(sync_session).list_candidates(
            risk_level=risk_level,
            review_status=review_status,
            country=country,
            city=city,
            platform=platform,
            channel_name=channel_name,
            extraction_status=extraction_status,
            limit=limit,
            offset=offset,
        )
        return LeadSourceCandidateListResponse(
            items=[serialize_candidate_list_item(candidate) for candidate in items],
            total=total,
            limit=limit,
            offset=offset,
        )

    return await async_session.run_sync(run)


@router.get("/{candidate_id:uuid}", response_model=LeadSourceCandidateDetailResponse)
async def get_lead_source_candidate(
    candidate_id: UUID,
    async_session: AsyncSession = Depends(get_async_session),
) -> LeadSourceCandidateDetailResponse:
    def run(sync_session):
        candidate = LeadSourceCandidateService(sync_session).get_candidate(candidate_id)
        if candidate is None:
            raise HTTPException(status_code=404, detail="来源候选不存在。")
        return serialize_candidate_detail(candidate)

    return await async_session.run_sync(run)


@router.post("/{candidate_id:uuid}/review-actions", response_model=LeadSourceCandidateReviewActionResponse)
async def apply_lead_source_candidate_review_action(
    candidate_id: UUID,
    request: LeadSourceCandidateReviewActionRequest,
    async_session: AsyncSession = Depends(get_async_session),
) -> LeadSourceCandidateReviewActionResponse:
    def run(sync_session):
        service = LeadSourceCandidateService(sync_session)
        try:
            result = service.apply_review_action(
                candidate_id,
                action=request.action,
                reviewer_id=request.reviewer_id,
                review_note=request.review_note,
            )
        except ValueError as exc:
            sync_session.commit()
            message = str(exc)
            status_code = 404 if "不存在" in message else 422
            raise HTTPException(status_code=status_code, detail=message) from exc
        sync_session.commit()
        payload = serialize_candidate_detail(result.candidate).model_dump()
        payload["audit_task_run_id"] = result.audit_task_run.id
        return LeadSourceCandidateReviewActionResponse(**payload)

    return await async_session.run_sync(run)
