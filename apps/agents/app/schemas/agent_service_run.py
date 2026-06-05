from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AgentServiceRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: UUID
    request_id: UUID
    agent_type: str = Field(min_length=1, max_length=80)
    agent_mode: str = Field(min_length=1, max_length=40)
    status: str = Field(min_length=1, max_length=40)
    trigger_source: str = Field(min_length=1, max_length=80)
    input_json: dict[str, Any] = Field(default_factory=dict)
    output_json: dict[str, Any] | None = None
    output_summary_json: dict[str, Any] | None = None
    audit_json: dict[str, Any] = Field(default_factory=dict)
    retry_count: int = Field(default=0, ge=0)
    max_retries: int = Field(default=2, ge=0)
    next_retry_at: datetime | None = None
    error_type: str | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
