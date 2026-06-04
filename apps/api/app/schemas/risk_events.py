from uuid import UUID

from pydantic import BaseModel, Field


class RiskEventCreate(BaseModel):
    channel: str = Field(min_length=1, max_length=120)
    risk_level: str = Field(pattern="^(Low|Medium|High|Forbidden)$")
    event_type: str = Field(min_length=1, max_length=120)
    block_reason: str = Field(min_length=1)
    channel_plan_id: UUID | None = None
    severity: str | None = Field(default=None, pattern="^(low|medium|high|critical)$")
    resolution_status: str | None = Field(default=None, pattern="^(open|investigating|resolved|dismissed)$")
    task_id: str | None = Field(default=None, max_length=120)
    agent_name: str | None = Field(default=None, max_length=120)
    action: str | None = Field(default=None, max_length=120)
    input_ref: str | None = None
    output_ref: str | None = None
    result: str = Field(default="blocked", max_length=80)
    error_message: str | None = None


class RiskEventResolve(BaseModel):
    resolution_note: str = Field(min_length=1)
    resolved_by: str | None = Field(default=None, max_length=120)


class RiskEventResponse(BaseModel):
    id: UUID
    channel_plan_id: UUID | None
    task_id: str | None
    agent_name: str | None
    action: str | None
    channel: str
    risk_level: str
    event_type: str
    severity: str
    resolution_status: str
    block_reason: str | None
    pause_suggested: bool
    resolution_note: str | None
    resolved_by: str | None
    input_ref: str | None
    output_ref: str | None
    result: str
    error_message: str | None
    created_at: str
    resolved_at: str | None


class RiskEventListResponse(BaseModel):
    items: list[RiskEventResponse]
