from uuid import UUID

from pydantic import BaseModel, Field


class FailedCaseCreate(BaseModel):
    case_type: str = Field(pattern="^(fetch_failed|schema_invalid|missing_evidence|risk_blocked|duplicate|llm_suspected_fabrication)$")
    source_url: str | None = None
    risk_level: str | None = Field(default=None, pattern="^(Low|Medium|High|Forbidden)$")
    related_task_type: str | None = None
    related_object_type: str | None = None
    related_object_id: str | None = None
    failure_reason: str = Field(min_length=1)
    evidence_note: str | None = None
    raw_input_ref: str | None = None
    raw_output_json: dict | None = None
    model_name: str | None = None
    prompt_version: str | None = None
    usable_for_rag: bool = True


class FailedCaseResponse(BaseModel):
    id: UUID
    case_type: str
    source_url: str | None
    risk_level: str | None
    related_task_type: str | None
    related_object_type: str | None
    related_object_id: str | None
    failure_reason: str
    evidence_note: str | None
    raw_input_ref: str | None
    raw_output_json: dict | None
    model_name: str | None
    prompt_version: str | None
    usable_for_rag: bool
    touch_queue_allowed: bool
    created_at: str


class FailedCaseListResponse(BaseModel):
    items: list[FailedCaseResponse]

