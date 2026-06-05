from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class FieldCandidateOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field_name: str = Field(min_length=1, max_length=120)
    candidate_value: Any
    source_type: Literal[
        "ai_public_source",
        "manual_public_info",
        "manual_customer_reply",
        "manual_business_note",
        "unknown",
    ]
    source_url: str | None = None
    evidence_note: str = Field(min_length=1)
    confidence_score: float | None = Field(default=None, ge=0, le=1)
    review_status: Literal["pending"] = "pending"


class DeepEnrichmentAgentOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["phase3.agent.deep_enrichment.v1"]
    agent_run_id: UUID
    staging_lead_id: UUID
    field_candidates: list[FieldCandidateOutput] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    recommended_next_action: Literal["manual_review", "continue_enrichment", "abandon", "no_action"] = "manual_review"
    audit: dict = Field(default_factory=dict)
