from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import AgentTaskRunStatus, AgentTaskType


class AgentTaskRunCreate(BaseModel):
    task_type: AgentTaskType
    trigger_source: str = Field(min_length=1, max_length=80)
    input_json: dict = Field(default_factory=dict)
    llm_provider: str | None = Field(default=None, max_length=80)
    llm_model: str | None = Field(default=None, max_length=120)
    prompt_template_id: UUID | None = None
    prompt_version: str | None = Field(default=None, max_length=40)


class AgentTaskRunUpdate(BaseModel):
    status: AgentTaskRunStatus | None = None
    output_summary_json: dict | None = None
    token_usage_json: dict | None = None
    latency_ms: int | None = Field(default=None, ge=0)
    error_message: str | None = None
    retry_count: int | None = Field(default=None, ge=0)
    started_at: datetime | None = None
    finished_at: datetime | None = None


class AgentTaskRunResponse(BaseModel):
    id: UUID
    task_type: AgentTaskType
    status: AgentTaskRunStatus
    trigger_source: str
    input_json: dict
    output_summary_json: dict | None
    llm_provider: str | None
    llm_model: str | None
    prompt_template_id: UUID | None
    prompt_version: str | None
    token_usage_json: dict | None
    latency_ms: int | None
    error_message: str | None
    retry_count: int
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AgentTaskRunListResponse(BaseModel):
    items: list[AgentTaskRunResponse]
