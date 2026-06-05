from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import (
    LeadEnrichmentFieldReviewStatus,
    LeadEnrichmentFieldSourceType,
    LeadEnrichmentResultStatus,
    LeadEnrichmentType,
)


class LeadEnrichmentRunCreate(BaseModel):
    triggered_by: str = Field(min_length=1, max_length=120)
    manual_keywords: list[str] = Field(default_factory=list)
    allowed_channel_scope: list[str] = Field(default_factory=list)
    note: str | None = None


class ManualEnrichmentFieldCreate(BaseModel):
    field_name: str = Field(min_length=1, max_length=120)
    candidate_value: Any
    source_type: LeadEnrichmentFieldSourceType
    source_url: str | None = None
    evidence_note: str = Field(min_length=1)
    confidence_score: float | None = Field(default=None, ge=0, le=1)


class ManualEnrichmentCreate(BaseModel):
    operator: str = Field(min_length=1, max_length=120)
    note: str | None = None
    fields: list[ManualEnrichmentFieldCreate] = Field(min_length=1)


class LeadEnrichmentRunResponse(BaseModel):
    id: UUID
    staging_lead_id: UUID
    enrichment_type: LeadEnrichmentType
    triggered_by: str
    status: LeadEnrichmentResultStatus
    input_snapshot_json: dict
    output_json: dict | None
    evidence_links: list[str]
    confidence_score: float | None
    missing_fields: list[str]
    recommended_action: str | None
    agent_task_run_id: UUID | None
    quota_daily_limit: int
    quota_used_today: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LeadEnrichmentFieldCandidateItem(BaseModel):
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


class LeadEnrichmentResultItem(BaseModel):
    id: UUID
    staging_lead_id: UUID
    enrichment_type: LeadEnrichmentType
    triggered_by: str
    status: LeadEnrichmentResultStatus
    input_snapshot_json: dict
    output_json: dict | None
    evidence_links: list[str]
    confidence_score: float | None
    missing_fields: list[str]
    recommended_action: str | None
    agent_task_run_id: UUID | None
    created_at: datetime
    updated_at: datetime
    field_candidates: list[LeadEnrichmentFieldCandidateItem] = Field(default_factory=list)


class LeadEnrichmentResultsResponse(BaseModel):
    staging_lead_id: UUID
    items: list[LeadEnrichmentResultItem] = Field(default_factory=list)
