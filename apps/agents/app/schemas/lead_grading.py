from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


LeadGrade = Literal["A", "B", "C", "Watch", "Invalid"]
LeadStatusRoute = Literal[
    "ready_for_manual_review",
    "needs_compliance_review",
    "needs_manual_risk_review",
    "risk_blocked",
]


class LeadGradingSuggestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_url: str = Field(min_length=1)
    recommended_grade: LeadGrade
    status_route: LeadStatusRoute
    confidence_score: float = Field(ge=0, le=1)
    reasons: list[str] = Field(min_length=1)
    triggered_rules: list[str] = Field(min_length=1)
    explanations: dict[str, str] = Field(default_factory=dict)
    auto_promote_customer: bool = False

    @model_validator(mode="after")
    def reject_auto_customer_promotion(self) -> "LeadGradingSuggestion":
        if self.auto_promote_customer:
            raise ValueError("Lead Grading 不允许自动晋级客户。")
        return self


class LeadGradingAgentOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["phase4.agent.lead_grading.v1"]
    grading_run_id: UUID | str
    agent_mode: Literal["active", "shadow"] = "shadow"
    suggestions: list[LeadGradingSuggestion] = Field(default_factory=list)
    audit: dict = Field(default_factory=dict)
