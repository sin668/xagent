from uuid import UUID

from pydantic import BaseModel, Field


class StagingLeadCreate(BaseModel):
    candidate_url_id: UUID
    customer_name: str | None = None
    country: str | None = None
    city: str | None = None
    customer_type: str | None = None
    contacts_json: list = Field(default_factory=list)
    activity_level: str | None = None
    scale_signal: str | None = None
    import_used_car_relevance: str | None = None
    source_evidence: str | None = None
    recommended_grade: str = Field(pattern="^(A|B|C|Invalid|Watch)$")
    recommended_reason: str | None = None
    missing_fields: list = Field(default_factory=list)
    source_risk_level: str = Field(pattern="^(Low|Medium|High|Forbidden)$")


class StagingLeadUpdate(BaseModel):
    customer_name: str | None = None
    country: str | None = None
    city: str | None = None
    customer_type: str | None = None
    contacts_json: list | None = None
    activity_level: str | None = None
    scale_signal: str | None = None
    import_used_car_relevance: str | None = None
    source_evidence: str | None = None
    recommended_reason: str | None = None
    missing_fields: list | None = None


class DuplicateCandidateResponse(BaseModel):
    target_type: str
    target_id: str
    reason: str
    source_url: str | None = None
    evidence_note: str | None = None


class DuplicateSignalResponse(DuplicateCandidateResponse):
    pass


class DuplicateSignalsResponse(BaseModel):
    has_strong_duplicate: bool = False
    blocks_promotion: bool = False
    requires_manual_review: bool = False
    strong_duplicates: list[DuplicateCandidateResponse] = Field(default_factory=list)
    suspected_duplicates: list[DuplicateCandidateResponse] = Field(default_factory=list)
    source_duplicates: list[DuplicateCandidateResponse] = Field(default_factory=list)


class StagingLeadResponse(BaseModel):
    id: UUID
    candidate_url_id: UUID
    source_url: str | None = None
    source_risk_level: str | None = None
    requires_secondary_verification: bool
    has_contact: bool
    evidence_status: str
    risk_markers: list[str]
    duplicate_signals: DuplicateSignalsResponse = Field(default_factory=DuplicateSignalsResponse)
    customer_name: str
    country: str
    city: str | None
    customer_type: str
    contacts_json: list
    activity_level: str | None
    scale_signal: str | None
    import_used_car_relevance: str | None
    source_evidence: str | None
    recommended_grade: str
    recommended_reason: str | None
    missing_fields: list
    review_status: str
    queue_status: str
    dedupe_key: str | None
    requires_compliance_review: bool
    created_at: str
    updated_at: str


class StagingLeadListResponse(BaseModel):
    items: list[StagingLeadResponse]


class CandidateUrlEvidenceResponse(BaseModel):
    id: UUID
    url: str | None
    source_platform: str | None
    source_risk_level: str | None
    source_usage_type: str | None
    requires_secondary_verification: bool
    queue_eligible: bool
    discovery_reason: str | None
    status: str | None


class PageSnapshotEvidenceResponse(BaseModel):
    id: UUID
    page_title: str | None
    evidence_note: str
    read_status: str
    captured_at: str
    robots_or_policy_note: str | None


class AIAuditSummaryResponse(BaseModel):
    id: UUID | None = None
    task_type: str | None = None
    model_name: str
    prompt_version: str
    recommended_grade: str | None = None
    recommended_reason: str | None = None
    missing_fields: list
    risk_blocked: bool
    risk_block_reason: str | None = None
    executed_at: str | None = None


class CoreGateResponse(BaseModel):
    status: str
    can_promote_to_core: bool
    reasons: list[str]


class StagingLeadDetailResponse(BaseModel):
    staging_lead: StagingLeadResponse
    candidate_url: CandidateUrlEvidenceResponse | None = None
    latest_page_snapshot: PageSnapshotEvidenceResponse | None = None
    ai_audit_summary: AIAuditSummaryResponse
    core_gate: CoreGateResponse


class DuplicateResolveRequest(BaseModel):
    actor: str = Field(min_length=1)
    action: str = Field(pattern="^(merge_to_core|mark_duplicate|dismiss)$")
    target_customer_id: UUID | None = None
    note: str | None = None


class DuplicateResolveResponse(BaseModel):
    staging_lead_id: UUID
    action: str
    review_status: str
    queue_status: str
    target_customer_id: UUID | None = None
    review_log_id: UUID


class StagingPromoteRequest(BaseModel):
    actor: str = Field(min_length=1)
    review_result: str = Field(pattern="^approved$")
    review_note: str | None = None


class StagingPromoteResponse(BaseModel):
    staging_lead_id: UUID
    customer_id: UUID
    customer_external_id: str | None
    customer_status: str
    do_not_contact: bool
    requires_compliance_review: bool
    compliance_review_id: UUID | None = None
    review_log_id: UUID
