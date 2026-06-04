from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import AgentTaskRunStatus


class SourceDiscoveryRunRequest(BaseModel):
    country: str = Field(min_length=1, max_length=80)
    cities: list[str] = Field(default_factory=list, max_length=20)
    channel_strategy: str = Field(min_length=1, max_length=160)
    keywords: list[str] = Field(default_factory=list, max_length=50)
    limit: int = Field(default=20, ge=20, le=50)


class SourceDiscoveryRunResponse(BaseModel):
    agent_task_run_id: UUID
    status: AgentTaskRunStatus
    created_count: int
    blocked_count: int
    duplicate_count: int

