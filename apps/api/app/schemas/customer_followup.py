from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.models.enums import CustomerFollowupTeam, CustomerFollowupType


class CustomerFollowupCreate(BaseModel):
    customer_id: UUID
    owner_id: str = Field(min_length=1, max_length=120)
    team: CustomerFollowupTeam
    followup_type: CustomerFollowupType
    content: str = Field(min_length=1)
    customer_feedback: str | None = None
    next_action: str | None = None
    next_followup_at: datetime | None = None
    triggered_dnc: bool = False
    triggered_compliance_review: bool = False
    created_by: str = Field(min_length=1, max_length=120)

    @model_validator(mode="after")
    def validate_dnc_feedback(self) -> "CustomerFollowupCreate":
        if self.triggered_dnc and not self.customer_feedback:
            raise ValueError("triggered_dnc followup must include customer_feedback")
        return self


class CustomerFollowupUpdate(BaseModel):
    owner_id: str | None = Field(default=None, max_length=120)
    team: CustomerFollowupTeam | None = None
    followup_type: CustomerFollowupType | None = None
    content: str | None = None
    customer_feedback: str | None = None
    next_action: str | None = None
    next_followup_at: datetime | None = None
    triggered_dnc: bool | None = None
    triggered_compliance_review: bool | None = None

    @model_validator(mode="after")
    def validate_dnc_feedback(self) -> "CustomerFollowupUpdate":
        if self.triggered_dnc and not self.customer_feedback:
            raise ValueError("triggered_dnc followup must include customer_feedback")
        return self


class CustomerFollowupResponse(BaseModel):
    id: UUID
    customer_id: UUID
    owner_id: str
    team: CustomerFollowupTeam
    followup_type: CustomerFollowupType
    content: str
    customer_feedback: str | None
    next_action: str | None
    next_followup_at: datetime | None
    triggered_dnc: bool
    triggered_compliance_review: bool
    created_by: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
