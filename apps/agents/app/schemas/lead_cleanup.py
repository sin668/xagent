from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CleanupSuggestionOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    staging_lead_id: UUID
    suggestion_type: Literal[
        "strong_duplicate",
        "possible_duplicate",
        "merge_contact_method",
        "merge_source_evidence",
        "restore_from_watch",
        "confirm_invalid",
        "mark_abandoned",
        "needs_manual_review",
    ]
    target_lead_id: UUID | None = None
    confidence_score: float | None = Field(default=None, ge=0, le=1)
    reason: str = Field(min_length=1)
    evidence_json: dict = Field(default_factory=dict)
    recommended_action: str = Field(min_length=1)
    review_status: Literal["pending"] = "pending"


class CleanupAgentOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["phase3.agent.lead_cleanup.v1"]
    cleanup_run_id: UUID
    suggestions: list[CleanupSuggestionOutput] = Field(default_factory=list)
    blocked_items: list[dict] = Field(default_factory=list)
    audit: dict = Field(default_factory=dict)
