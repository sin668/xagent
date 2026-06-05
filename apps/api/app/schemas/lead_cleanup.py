from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.models.enums import LeadCleanupRunStatus, LeadCleanupSuggestionReviewStatus, LeadCleanupSuggestionType


class LeadCleanupRunCreate(BaseModel):
    trigger_source: str = Field(min_length=1, max_length=120)
    status: LeadCleanupRunStatus = LeadCleanupRunStatus.PENDING
    input_filter_json: dict = Field(default_factory=dict)
    output_summary_json: dict | None = None
    llm_provider: str | None = Field(default=None, max_length=80)
    llm_model: str | None = Field(default=None, max_length=120)
    prompt_template_id: UUID | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


class LeadCleanupRunUpdate(BaseModel):
    status: LeadCleanupRunStatus | None = None
    output_summary_json: dict | None = None
    llm_provider: str | None = Field(default=None, max_length=80)
    llm_model: str | None = Field(default=None, max_length=120)
    prompt_template_id: UUID | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


class LeadCleanupRunResponse(BaseModel):
    id: UUID
    trigger_source: str
    status: LeadCleanupRunStatus
    input_filter_json: dict
    output_summary_json: dict | None
    llm_provider: str | None
    llm_model: str | None
    prompt_template_id: UUID | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LeadCleanupSuggestionCreate(BaseModel):
    cleanup_run_id: UUID
    staging_lead_id: UUID
    suggestion_type: LeadCleanupSuggestionType
    target_lead_id: UUID | None = None
    confidence_score: float | None = Field(default=None, ge=0, le=1)
    reason: str = Field(min_length=1)
    evidence_json: dict = Field(default_factory=dict)
    recommended_action: str = Field(min_length=1)
    review_status: LeadCleanupSuggestionReviewStatus = LeadCleanupSuggestionReviewStatus.PENDING
    reviewer_id: str | None = Field(default=None, max_length=120)
    reviewed_at: datetime | None = None
    executed_by: str | None = Field(default=None, max_length=120)
    executed_at: datetime | None = None
    execution_note: str | None = None

    @model_validator(mode="after")
    def validate_review_audit(self) -> "LeadCleanupSuggestionCreate":
        if self.review_status in {
            LeadCleanupSuggestionReviewStatus.APPROVED,
            LeadCleanupSuggestionReviewStatus.REJECTED,
            LeadCleanupSuggestionReviewStatus.EXECUTED,
        } and not self.reviewer_id:
            raise ValueError("reviewed cleanup suggestion must include reviewer_id")
        if self.review_status == LeadCleanupSuggestionReviewStatus.EXECUTED and not self.executed_by:
            raise ValueError("executed cleanup suggestion must include executed_by")
        return self


class LeadCleanupSuggestionUpdate(BaseModel):
    suggestion_type: LeadCleanupSuggestionType | None = None
    target_lead_id: UUID | None = None
    confidence_score: float | None = Field(default=None, ge=0, le=1)
    reason: str | None = None
    evidence_json: dict | None = None
    recommended_action: str | None = None
    review_status: LeadCleanupSuggestionReviewStatus | None = None
    reviewer_id: str | None = Field(default=None, max_length=120)
    reviewed_at: datetime | None = None
    executed_by: str | None = Field(default=None, max_length=120)
    executed_at: datetime | None = None
    execution_note: str | None = None

    @model_validator(mode="after")
    def validate_review_audit(self) -> "LeadCleanupSuggestionUpdate":
        if self.review_status in {
            LeadCleanupSuggestionReviewStatus.APPROVED,
            LeadCleanupSuggestionReviewStatus.REJECTED,
            LeadCleanupSuggestionReviewStatus.EXECUTED,
        } and not self.reviewer_id:
            raise ValueError("reviewed cleanup suggestion must include reviewer_id")
        if self.review_status == LeadCleanupSuggestionReviewStatus.EXECUTED and not self.executed_by:
            raise ValueError("executed cleanup suggestion must include executed_by")
        return self


class LeadCleanupSuggestionResponse(BaseModel):
    id: UUID
    cleanup_run_id: UUID
    staging_lead_id: UUID
    suggestion_type: LeadCleanupSuggestionType
    target_lead_id: UUID | None
    confidence_score: float | None
    reason: str
    evidence_json: dict
    recommended_action: str
    review_status: LeadCleanupSuggestionReviewStatus
    reviewer_id: str | None
    reviewed_at: datetime | None
    executed_by: str | None
    executed_at: datetime | None
    execution_note: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LeadCleanupSuggestionListResponse(BaseModel):
    items: list[LeadCleanupSuggestionResponse]
    total: int


class LeadCleanupSuggestionReviewRequest(BaseModel):
    actor: str = Field(min_length=1, max_length=120)
    actor_role: str = Field(min_length=1, max_length=80)
    review_note: str = Field(min_length=1)


class LeadCleanupSuggestionExecuteRequest(BaseModel):
    actor: str = Field(min_length=1, max_length=120)
    actor_role: str = Field(min_length=1, max_length=80)
    execution_note: str = Field(min_length=1)
