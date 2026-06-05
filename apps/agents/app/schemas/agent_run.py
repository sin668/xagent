from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


AGENT_RUN_SCHEMA_VERSION = "phase4.agent.run.v1"

AgentTriggerSource = Literal["manual_api", "shadow_run", "scheduler", "test"]
AgentMode = Literal["active", "shadow", "dry_run"]
AgentType = Literal["deep_enrichment", "lead_cleanup", "source_discovery", "lead_extraction_grading"]
AgentRunStatus = Literal["pending", "running", "retrying", "succeeded", "failed", "blocked", "cancelled"]


class AgentRunOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_retries: int = Field(default=2, ge=0, le=10)
    timeout_seconds: int = Field(default=120, ge=1, le=3600)
    dry_run: bool = False
    shadow_mode: bool = False


class AgentRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: UUID
    agent_task_run_id: UUID | None = None
    trigger_source: AgentTriggerSource
    agent_mode: AgentMode
    input: dict[str, Any] = Field(default_factory=dict)
    options: AgentRunOptions = Field(default_factory=AgentRunOptions)


class AgentRunAudit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    writes_core_tables: bool = False
    executed_nodes: list[str] = Field(default_factory=list)
    failed_node: str | None = None
    risk_flags: list[str] = Field(default_factory=list)
    source_urls: list[str] = Field(default_factory=list)
    llm_provider: str | None = None
    llm_model: str | None = None

    @model_validator(mode="after")
    def reject_core_table_writes(self) -> "AgentRunAudit":
        if self.writes_core_tables:
            raise ValueError("Agent Run audit must not allow core table writes.")
        return self


class AgentRunError(BaseModel):
    model_config = ConfigDict(extra="forbid")

    error_type: str = Field(min_length=1)
    message: str = Field(min_length=1)
    retryable: bool | None = None
    failed_node: str | None = None


class AgentRunResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["phase4.agent.run.v1"] = AGENT_RUN_SCHEMA_VERSION
    agent_service_run_id: UUID
    request_id: UUID
    status: AgentRunStatus
    agent_type: AgentType
    agent_mode: AgentMode
    output: dict[str, Any] | None = None
    audit: AgentRunAudit = Field(default_factory=AgentRunAudit)
    error: AgentRunError | None = None
