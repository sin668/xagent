from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SourceCandidateOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str = Field(min_length=1)
    normalized_url: str = Field(min_length=1)
    source_type: Literal["official_website", "public_directory", "public_social", "marketplace", "unknown"]
    risk_level: Literal["low", "medium", "high"]
    evidence_summary: str = Field(min_length=1)
    discovery_query: str | None = None
    review_status: Literal["shadow_only", "needs_manual_review"] = "shadow_only"


class SourceDiscoveryAgentOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["phase4.agent.source_discovery.v1"]
    discovery_run_id: UUID | str
    agent_mode: Literal["active", "shadow"] = "shadow"
    candidates: list[SourceCandidateOutput] = Field(default_factory=list)
    blocked_items: list[dict] = Field(default_factory=list)
    audit: dict = Field(default_factory=dict)
