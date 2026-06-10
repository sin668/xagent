from collections.abc import AsyncIterator
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.schemas.staging_leads import (
    AIAuditSummaryResponse,
    DuplicateResolveRequest,
    DuplicateResolveResponse,
    DuplicateSignalsResponse,
    CandidateUrlEvidenceResponse,
    CoreGateResponse,
    PageSnapshotEvidenceResponse,
    StagingLeadCreate,
    StagingLeadAbandonRequest,
    StagingLeadDetailResponse,
    StagingLeadExitActionResponse,
    StagingLeadGradeUpdateRequest,
    StagingLeadListResponse,
    StagingLeadMarkInvalidRequest,
    StagingLeadMarkWatchRequest,
    StagingPromoteRequest,
    StagingPromoteResponse,
    StagingLeadResponse,
    StagingLeadUpdate,
)
from app.schemas.customer_promotion import PromoteStagingLeadToCustomerRequest, PromoteStagingLeadToCustomerResponse
from app.services.customer_promotion import CustomerPromotionService
from app.services.staging_lead_actions import StagingLeadActionService
from app.services.staging_leads import StagingLeadService

router = APIRouter(prefix="/staging-leads", tags=["staging-leads"])


async def get_async_session() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session


def serialize_duplicate_signals(signals: dict | None) -> DuplicateSignalsResponse:
    return DuplicateSignalsResponse(**(signals or StagingLeadService.empty_duplicate_signal_summary()))


def serialize_staging_lead(lead, duplicate_signals: dict | None = None) -> StagingLeadResponse:
    candidate = lead.candidate_url
    source_risk_level = candidate.source_risk_level.value if candidate is not None else None
    has_contact = StagingLeadService.has_contact(lead.contacts_json)
    evidence_status = StagingLeadService.evidence_status(lead.source_evidence)
    return StagingLeadResponse(
        id=lead.id,
        candidate_url_id=lead.candidate_url_id,
        source_url=candidate.url if candidate is not None else None,
        source_risk_level=source_risk_level,
        requires_secondary_verification=(
            candidate.requires_secondary_verification if candidate is not None else lead.review_status.value == "needs_secondary_verification"
        ),
        has_contact=has_contact,
        evidence_status=evidence_status,
        risk_markers=StagingLeadService.risk_markers(
            source_risk_level=source_risk_level or "Low",
            recommended_grade=lead.recommended_grade,
            review_status=lead.review_status,
            has_contact=has_contact,
            has_evidence=evidence_status == "present",
        ),
        duplicate_signals=serialize_duplicate_signals(duplicate_signals),
        customer_name=lead.customer_name,
        country=lead.country,
        city=lead.city,
        customer_type=lead.customer_type.value,
        contacts_json=lead.contacts_json,
        activity_level=lead.activity_level,
        scale_signal=lead.scale_signal,
        import_used_car_relevance=lead.import_used_car_relevance,
        source_evidence=lead.source_evidence,
        recommended_grade=lead.recommended_grade.value,
        recommended_reason=lead.recommended_reason,
        missing_fields=lead.missing_fields,
        review_status=lead.review_status.value,
        queue_status=lead.queue_status.value,
        dedupe_key=lead.dedupe_key,
        requires_compliance_review=lead.requires_compliance_review,
        created_at=lead.created_at.isoformat(),
        updated_at=lead.updated_at.isoformat(),
    )


def serialize_candidate_url(candidate) -> CandidateUrlEvidenceResponse | None:
    if candidate is None:
        return None
    return CandidateUrlEvidenceResponse(
        id=candidate.id,
        url=candidate.url,
        source_platform=candidate.source_platform.value,
        source_risk_level=candidate.source_risk_level.value,
        source_usage_type=candidate.source_usage_type.value,
        requires_secondary_verification=candidate.requires_secondary_verification,
        queue_eligible=candidate.queue_eligible,
        discovery_reason=candidate.discovery_reason,
        status=candidate.status.value,
    )


def serialize_page_snapshot(snapshot) -> PageSnapshotEvidenceResponse | None:
    if snapshot is None:
        return None
    return PageSnapshotEvidenceResponse(
        id=snapshot.id,
        page_title=snapshot.page_title,
        evidence_note=snapshot.evidence_note,
        read_status=snapshot.read_status.value,
        captured_at=snapshot.captured_at.isoformat(),
        robots_or_policy_note=snapshot.robots_or_policy_note,
    )


def serialize_ai_audit_summary(audit) -> AIAuditSummaryResponse:
    if audit is None:
        return AIAuditSummaryResponse(
            model_name="Unknown",
            prompt_version="Unknown",
            missing_fields=[],
            risk_blocked=False,
        )
    output = audit.output_payload or audit.output_json or {}
    return AIAuditSummaryResponse(
        id=audit.id,
        task_type=audit.task_type.value,
        model_name=audit.model_name,
        prompt_version=audit.prompt_version,
        recommended_grade=output.get("recommended_grade"),
        recommended_reason=output.get("recommended_reason"),
        missing_fields=output.get("missing_fields") or [],
        risk_blocked=audit.risk_blocked,
        risk_block_reason=audit.risk_block_reason,
        executed_at=audit.executed_at.isoformat(),
    )


def serialize_staging_lead_detail(
    lead,
    latest_snapshot=None,
    latest_ai_audit=None,
    duplicate_signals=None,
    *,
    do_not_contact_customer_id=None,
) -> StagingLeadDetailResponse:
    candidate = lead.candidate_url
    source_url = candidate.url if candidate is not None else None
    has_evidence = any(
        [
            (lead.source_evidence or "").strip(),
            (latest_snapshot.evidence_note if latest_snapshot is not None else "").strip(),
        ]
    )
    gate = StagingLeadService.core_gate_status(
        source_url=source_url,
        has_evidence=has_evidence,
        source_risk_level=candidate.source_risk_level if candidate is not None else None,
        recommended_grade=lead.recommended_grade,
        review_status=lead.review_status,
        queue_status=lead.queue_status,
    )
    return StagingLeadDetailResponse(
        staging_lead=serialize_staging_lead(lead, duplicate_signals),
        candidate_url=serialize_candidate_url(candidate),
        latest_page_snapshot=serialize_page_snapshot(latest_snapshot),
        ai_audit_summary=serialize_ai_audit_summary(latest_ai_audit),
        core_gate=CoreGateResponse(**gate),
        has_do_not_contact_match=do_not_contact_customer_id is not None,
        do_not_contact_customer_id=do_not_contact_customer_id,
    )


def serialize_exit_action_result(result: dict) -> StagingLeadExitActionResponse:
    lead = result["lead"]
    review_log = result["review_log"]
    return StagingLeadExitActionResponse(
        staging_lead_id=lead.id,
        action=result["action"],
        recommended_grade=lead.recommended_grade,
        review_status=lead.review_status,
        queue_status=lead.queue_status,
        reason=result["reason"],
        review_log_id=review_log.id,
    )


@router.post("", response_model=StagingLeadResponse)
async def create_staging_lead(
    request: StagingLeadCreate,
    async_session: AsyncSession = Depends(get_async_session),
) -> StagingLeadResponse:
    def run(sync_session):
        service = StagingLeadService(sync_session)
        try:
            lead = service.create_staging_lead(
                candidate_url_id=request.candidate_url_id,
                customer_name=request.customer_name,
                country=request.country,
                city=request.city,
                customer_type=request.customer_type,
                contacts_json=request.contacts_json,
                activity_level=request.activity_level,
                scale_signal=request.scale_signal,
                import_used_car_relevance=request.import_used_car_relevance,
                source_evidence=request.source_evidence,
                recommended_grade=request.recommended_grade,
                recommended_reason=request.recommended_reason,
                missing_fields=request.missing_fields,
                source_risk_level=request.source_risk_level,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        sync_session.commit()
        return serialize_staging_lead(lead)

    return await async_session.run_sync(run)


@router.get("", response_model=StagingLeadListResponse)
async def list_staging_leads(
    review_status: str | None = Query(default=None, pattern="^(pending_review|needs_secondary_verification|approved|rejected|duplicate)$"),
    recommended_grade: list[str] | None = Query(default=None),
    queue_status: str | None = Query(default=None, pattern="^(pending_review|eligible|not_eligible|blocked)$"),
    source_risk_level: str | None = Query(default=None, pattern="^(Low|Medium|High|Forbidden)$"),
    has_contact: bool | None = None,
    requires_secondary_verification: bool | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    async_session: AsyncSession = Depends(get_async_session),
) -> StagingLeadListResponse:
    def run(sync_session):
        service = StagingLeadService(sync_session)
        return StagingLeadListResponse(
            items=[
                serialize_staging_lead(lead)
                for lead in service.list_staging_leads(
                    review_status=review_status,
                    recommended_grade=recommended_grade,
                    queue_status=queue_status,
                    source_risk_level=source_risk_level,
                    has_contact=has_contact,
                    requires_secondary_verification=requires_secondary_verification,
                    limit=limit,
                )
            ]
        )

    return await async_session.run_sync(run)


@router.get("/{lead_id:uuid}", response_model=StagingLeadDetailResponse)
async def get_staging_lead(
    lead_id: UUID,
    async_session: AsyncSession = Depends(get_async_session),
) -> StagingLeadDetailResponse:
    def run(sync_session):
        service = StagingLeadService(sync_session)
        lead = service.get_staging_lead(lead_id)
        if lead is None:
            raise HTTPException(status_code=404, detail="staging lead not found")
        return serialize_staging_lead_detail(
            lead,
            service.latest_page_snapshot_for_lead(lead),
            service.latest_ai_audit_for_lead(lead),
            service.duplicate_signals_for_lead(lead),
            do_not_contact_customer_id=CustomerPromotionService(sync_session).find_do_not_contact_customer_id(lead),
        )

    return await async_session.run_sync(run)


@router.get("/{lead_id:uuid}/duplicates", response_model=DuplicateSignalsResponse)
async def get_staging_lead_duplicates(
    lead_id: UUID,
    async_session: AsyncSession = Depends(get_async_session),
) -> DuplicateSignalsResponse:
    def run(sync_session):
        service = StagingLeadService(sync_session)
        lead = service.get_staging_lead(lead_id)
        if lead is None:
            raise HTTPException(status_code=404, detail="staging lead not found")
        return serialize_duplicate_signals(service.duplicate_signals_for_lead(lead))

    return await async_session.run_sync(run)


@router.post("/{lead_id:uuid}/duplicates/resolve", response_model=DuplicateResolveResponse)
async def resolve_staging_lead_duplicate(
    lead_id: UUID,
    request: DuplicateResolveRequest,
    async_session: AsyncSession = Depends(get_async_session),
) -> DuplicateResolveResponse:
    def run(sync_session):
        service = StagingLeadService(sync_session)
        try:
            result = service.resolve_duplicate(
                lead_id=lead_id,
                actor=request.actor,
                action=request.action,
                target_customer_id=request.target_customer_id,
                note=request.note,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        sync_session.commit()
        lead = result["lead"]
        review_log = result["review_log"]
        return DuplicateResolveResponse(
            staging_lead_id=lead.id,
            action=result["action"],
            review_status=lead.review_status.value,
            queue_status=lead.queue_status.value,
            target_customer_id=result["target_customer_id"],
            review_log_id=review_log.id,
        )

    return await async_session.run_sync(run)


@router.post("/{lead_id:uuid}/promote", response_model=StagingPromoteResponse)
async def promote_staging_lead(
    lead_id: UUID,
    request: StagingPromoteRequest,
    async_session: AsyncSession = Depends(get_async_session),
) -> StagingPromoteResponse:
    def run(sync_session):
        service = StagingLeadService(sync_session)
        try:
            result = service.promote_staging_lead_to_core(
                lead_id=lead_id,
                actor=request.actor,
                review_result=request.review_result,
                review_note=request.review_note,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        sync_session.commit()
        customer = result["customer"]
        compliance_review = result["compliance_review"]
        review_log = result["review_log"]
        return StagingPromoteResponse(
            staging_lead_id=lead_id,
            customer_id=customer.id,
            customer_external_id=customer.external_id,
            customer_status=customer.status.value,
            do_not_contact=customer.do_not_contact,
            requires_compliance_review=result["requires_compliance_review"],
            compliance_review_id=compliance_review.id if compliance_review is not None else None,
            review_log_id=review_log.id,
        )

    return await async_session.run_sync(run)


@router.post("/{lead_id:uuid}/promote-to-customer", response_model=PromoteStagingLeadToCustomerResponse)
async def promote_staging_lead_to_customer(
    lead_id: UUID,
    request: PromoteStagingLeadToCustomerRequest,
    async_session: AsyncSession = Depends(get_async_session),
) -> PromoteStagingLeadToCustomerResponse:
    def run(sync_session):
        service = CustomerPromotionService(sync_session)
        lead = service.get_staging_lead(lead_id)
        if lead is None:
            raise HTTPException(status_code=404, detail="staging lead not found")
        try:
            result = service.promote_to_customer(lead, request=request)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        sync_session.commit()
        customer = result["customer"]
        lead_source = result["lead_source"]
        compliance_review = result["compliance_review"]
        review_log = result["review_log"]
        return PromoteStagingLeadToCustomerResponse(
            staging_lead_id=lead_id,
            customer_id=customer.id,
            customer_external_id=customer.external_id,
            lead_source_id=lead_source.id,
            contact_method_ids=[contact.id for contact in result["contact_methods"]],
            customer_status=customer.status,
            do_not_contact=customer.do_not_contact,
            requires_compliance_review=result["requires_compliance_review"],
            compliance_review_id=compliance_review.id if compliance_review is not None else None,
            review_log_id=review_log.id,
        )

    return await async_session.run_sync(run)


@router.patch("/{lead_id:uuid}/mark-watch", response_model=StagingLeadExitActionResponse)
async def mark_staging_lead_watch(
    lead_id: UUID,
    request: StagingLeadMarkWatchRequest,
    async_session: AsyncSession = Depends(get_async_session),
) -> StagingLeadExitActionResponse:
    def run(sync_session):
        service = StagingLeadActionService(sync_session)
        lead = service.get_staging_lead(lead_id)
        if lead is None:
            raise HTTPException(status_code=404, detail="staging lead not found")
        result = service.mark_watch(lead, request=request)
        sync_session.commit()
        return serialize_exit_action_result(result)

    return await async_session.run_sync(run)


@router.patch("/{lead_id:uuid}/mark-invalid", response_model=StagingLeadExitActionResponse)
async def mark_staging_lead_invalid(
    lead_id: UUID,
    request: StagingLeadMarkInvalidRequest,
    async_session: AsyncSession = Depends(get_async_session),
) -> StagingLeadExitActionResponse:
    def run(sync_session):
        service = StagingLeadActionService(sync_session)
        lead = service.get_staging_lead(lead_id)
        if lead is None:
            raise HTTPException(status_code=404, detail="staging lead not found")
        result = service.mark_invalid(lead, request=request)
        sync_session.commit()
        return serialize_exit_action_result(result)

    return await async_session.run_sync(run)


@router.patch("/{lead_id:uuid}/abandon", response_model=StagingLeadExitActionResponse)
async def abandon_staging_lead(
    lead_id: UUID,
    request: StagingLeadAbandonRequest,
    async_session: AsyncSession = Depends(get_async_session),
) -> StagingLeadExitActionResponse:
    def run(sync_session):
        service = StagingLeadActionService(sync_session)
        lead = service.get_staging_lead(lead_id)
        if lead is None:
            raise HTTPException(status_code=404, detail="staging lead not found")
        result = service.abandon(lead, request=request)
        sync_session.commit()
        return serialize_exit_action_result(result)

    return await async_session.run_sync(run)


@router.patch("/{lead_id:uuid}/grade", response_model=StagingLeadExitActionResponse)
async def update_staging_lead_grade(
    lead_id: UUID,
    request: StagingLeadGradeUpdateRequest,
    async_session: AsyncSession = Depends(get_async_session),
) -> StagingLeadExitActionResponse:
    def run(sync_session):
        service = StagingLeadActionService(sync_session)
        lead = service.get_staging_lead(lead_id)
        if lead is None:
            raise HTTPException(status_code=404, detail="staging lead not found")
        try:
            result = service.update_grade(lead, request=request)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        sync_session.commit()
        return serialize_exit_action_result(result)

    return await async_session.run_sync(run)


@router.patch("/{lead_id:uuid}", response_model=StagingLeadResponse)
async def update_staging_lead(
    lead_id: UUID,
    request: StagingLeadUpdate,
    async_session: AsyncSession = Depends(get_async_session),
) -> StagingLeadResponse:
    def run(sync_session):
        service = StagingLeadService(sync_session)
        lead = service.get_staging_lead(lead_id)
        if lead is None:
            raise HTTPException(status_code=404, detail="staging lead not found")
        for field, value in request.model_dump(exclude_unset=True).items():
            setattr(lead, field, value)
        sync_session.commit()
        return serialize_staging_lead(lead)

    return await async_session.run_sync(run)
