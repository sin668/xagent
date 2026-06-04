from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import AgentTaskRunStatus


class LeadExtractionFromSourcesRunRequest(BaseModel):
    limit: int = Field(default=20, ge=1, le=100)
    country: str | None = Field(default=None, max_length=80)
    city: str | None = Field(default=None, max_length=120)
    trigger_source: str = Field(default="lead_extraction_source_selection_api", min_length=1, max_length=80)


class LeadExtractionBlockedCandidateResponse(BaseModel):
    candidate_id: UUID
    risk_level: str
    review_status: str
    extraction_status: str
    block_reason: str


class LeadExtractionFromSourcesRunResponse(BaseModel):
    agent_task_run_id: UUID
    status: AgentTaskRunStatus
    selected_count: int
    blocked_count: int
    candidate_ids: list[UUID]
    blocked_candidates: list[LeadExtractionBlockedCandidateResponse]
