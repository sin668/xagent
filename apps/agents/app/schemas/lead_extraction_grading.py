from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.lead_extraction import LeadExtractionAgentOutput
from app.schemas.lead_grading import LeadGradingAgentOutput


class LeadExtractionGradingHardRuleSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hard_rules_applied: bool = False
    triggered_rules: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)


class LeadExtractionGradingValidationSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_passed: bool
    schema_pass_rate: float = Field(ge=0, le=1)
    evidence_hit_rate: float = Field(ge=0, le=1)
    contact_anti_fabrication_passed: bool
    contact_anti_fabrication_pass_rate: float = Field(ge=0, le=1)
    hard_rule_consistency_rate: float = Field(ge=0, le=1)
    invalid_contacts: list[dict[str, str]] = Field(default_factory=list)
    validation_errors: list[str] = Field(default_factory=list)


class LeadExtractionGradingAgentOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["phase4.agent.lead_extraction_grading.v1"]
    combined_run_id: UUID | str
    agent_mode: Literal["active", "shadow"] = "shadow"
    extraction: LeadExtractionAgentOutput
    grading: LeadGradingAgentOutput
    hard_rule_summary: LeadExtractionGradingHardRuleSummary
    validation_summary: LeadExtractionGradingValidationSummary
    grade_delta_explanations: dict[str, str] = Field(default_factory=dict)
    batch_results: list[dict] = Field(default_factory=list)
    audit: dict = Field(default_factory=dict)
