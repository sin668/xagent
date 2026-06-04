from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import (
    ChannelRiskLevel,
    LeadSourceCandidateExtractionStatus,
    LeadSourceCandidateReviewStatus,
    SourcePlatform,
)


class LeadSourceCandidateCreate(BaseModel):
    source_url: str = Field(min_length=1)
    normalized_domain: str = Field(min_length=1, max_length=255)
    platform: SourcePlatform
    channel_name: str = Field(min_length=1, max_length=120)
    country: str = Field(min_length=1, max_length=80)
    city: str | None = Field(default=None, max_length=120)
    risk_level: ChannelRiskLevel
    discovery_method: str = Field(min_length=1, max_length=120)
    discovery_query: str | None = None
    discovery_reason: str = Field(min_length=1)
    evidence_note: str = Field(min_length=1)
    evidence_links: list[str] = Field(default_factory=list)
    llm_provider: str | None = Field(default=None, max_length=80)
    llm_model: str | None = Field(default=None, max_length=120)
    llm_output_json: dict | None = None
    confidence_score: float | None = Field(default=None, ge=0, le=1)
    created_by_task_run_id: UUID | None = None


class LeadSourceCandidateUpdate(BaseModel):
    review_status: LeadSourceCandidateReviewStatus | None = None
    approved_for_extraction: bool | None = None
    reviewer_id: str | None = Field(default=None, max_length=120)
    review_note: str | None = None
    reviewed_at: datetime | None = None
    extraction_status: LeadSourceCandidateExtractionStatus | None = None
    last_extracted_at: datetime | None = None
    next_retry_at: datetime | None = None
    retry_count: int | None = Field(default=None, ge=0)
    duplicate_of_id: UUID | None = None
    is_duplicate: bool | None = None


class LeadSourceCandidateResponse(BaseModel):
    id: UUID
    source_url: str
    normalized_domain: str
    platform: SourcePlatform
    channel_name: str
    country: str
    city: str | None
    risk_level: ChannelRiskLevel
    review_status: LeadSourceCandidateReviewStatus
    approved_for_extraction: bool
    reviewer_id: str | None
    review_note: str | None
    reviewed_at: datetime | None
    discovery_method: str
    discovery_query: str | None
    discovery_reason: str
    evidence_note: str
    evidence_links: list[str]
    llm_provider: str | None
    llm_model: str | None
    llm_output_json: dict | None
    confidence_score: float | None
    extraction_status: LeadSourceCandidateExtractionStatus
    last_extracted_at: datetime | None
    next_retry_at: datetime | None
    retry_count: int
    dedupe_key: str
    duplicate_of_id: UUID | None
    is_duplicate: bool
    created_by_task_run_id: UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LeadSourceCandidateListResponse(BaseModel):
    items: list[LeadSourceCandidateResponse]
    total: int = 0
    limit: int | None = None
    offset: int = 0


class LeadSourceCandidateDetailResponse(LeadSourceCandidateResponse):
    llm_output_summary: dict


LeadSourceCandidateReviewAction = Literal[
    "approve_for_extraction",
    "reject",
    "mark_high_risk",
    "pause_channel",
    "add_review_note",
]


class LeadSourceCandidateReviewActionRequest(BaseModel):
    action: LeadSourceCandidateReviewAction
    reviewer_id: str = Field(min_length=1, max_length=120)
    review_note: str = Field(min_length=1)


class LeadSourceCandidateReviewActionResponse(LeadSourceCandidateDetailResponse):
    audit_task_run_id: UUID
