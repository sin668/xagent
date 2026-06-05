from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.models.enums import LeadEnrichmentFieldReviewStatus, LeadEnrichmentFieldSourceType


class LeadEnrichmentFieldCandidateCreate(BaseModel):
    enrichment_result_id: UUID
    staging_lead_id: UUID
    field_name: str = Field(min_length=1, max_length=120)
    candidate_value: Any
    source_type: LeadEnrichmentFieldSourceType
    source_url: str | None = None
    evidence_note: str = Field(min_length=1)
    confidence_score: float | None = Field(default=None, ge=0, le=1)
    review_status: LeadEnrichmentFieldReviewStatus = LeadEnrichmentFieldReviewStatus.PENDING
    accepted_by: str | None = Field(default=None, max_length=120)
    accepted_at: datetime | None = None
    rejected_reason: str | None = None

    @model_validator(mode="after")
    def validate_review_audit(self) -> "LeadEnrichmentFieldCandidateCreate":
        if self.review_status == LeadEnrichmentFieldReviewStatus.ACCEPTED and not self.accepted_by:
            raise ValueError("accepted field candidate must include accepted_by")
        if self.review_status == LeadEnrichmentFieldReviewStatus.REJECTED and not self.rejected_reason:
            raise ValueError("rejected field candidate must include rejected_reason")
        return self


class LeadEnrichmentFieldCandidateUpdate(BaseModel):
    candidate_value: Any | None = None
    source_type: LeadEnrichmentFieldSourceType | None = None
    source_url: str | None = None
    evidence_note: str | None = None
    confidence_score: float | None = Field(default=None, ge=0, le=1)
    review_status: LeadEnrichmentFieldReviewStatus | None = None
    accepted_by: str | None = Field(default=None, max_length=120)
    accepted_at: datetime | None = None
    rejected_reason: str | None = None

    @model_validator(mode="after")
    def validate_review_audit(self) -> "LeadEnrichmentFieldCandidateUpdate":
        if self.review_status == LeadEnrichmentFieldReviewStatus.ACCEPTED and not self.accepted_by:
            raise ValueError("accepted field candidate must include accepted_by")
        if self.review_status == LeadEnrichmentFieldReviewStatus.REJECTED and not self.rejected_reason:
            raise ValueError("rejected field candidate must include rejected_reason")
        return self


class LeadEnrichmentFieldCandidateAccept(BaseModel):
    accepted_by: str = Field(min_length=1, max_length=120)
    candidate_value: Any | None = None
    source_type: LeadEnrichmentFieldSourceType | None = None
    source_url: str | None = None
    evidence_note: str | None = None
    confidence_score: float | None = Field(default=None, ge=0, le=1)


class LeadEnrichmentFieldCandidateReject(BaseModel):
    rejected_reason: str = Field(min_length=1)


class LeadEnrichmentFieldCandidateResponse(BaseModel):
    id: UUID
    enrichment_result_id: UUID
    staging_lead_id: UUID
    field_name: str
    candidate_value: Any
    source_type: LeadEnrichmentFieldSourceType
    source_url: str | None
    evidence_note: str
    confidence_score: float | None
    review_status: LeadEnrichmentFieldReviewStatus
    accepted_by: str | None
    accepted_at: datetime | None
    rejected_reason: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
