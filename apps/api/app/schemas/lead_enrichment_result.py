from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import LeadEnrichmentResultStatus, LeadEnrichmentType


class LeadEnrichmentResultCreate(BaseModel):
    staging_lead_id: UUID
    enrichment_type: LeadEnrichmentType
    triggered_by: str = Field(min_length=1, max_length=120)
    status: LeadEnrichmentResultStatus = LeadEnrichmentResultStatus.PENDING
    input_snapshot_json: dict = Field(default_factory=dict)
    output_json: dict | None = None
    evidence_links: list[str] = Field(default_factory=list)
    confidence_score: float | None = Field(default=None, ge=0, le=1)
    missing_fields: list[str] = Field(default_factory=list)
    recommended_action: str | None = Field(default=None, max_length=120)
    agent_task_run_id: UUID | None = None


class LeadEnrichmentResultUpdate(BaseModel):
    status: LeadEnrichmentResultStatus | None = None
    output_json: dict | None = None
    evidence_links: list[str] | None = None
    confidence_score: float | None = Field(default=None, ge=0, le=1)
    missing_fields: list[str] | None = None
    recommended_action: str | None = Field(default=None, max_length=120)
    agent_task_run_id: UUID | None = None


class LeadEnrichmentResultResponse(BaseModel):
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

    model_config = {"from_attributes": True}
