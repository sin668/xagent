from uuid import UUID

from pydantic import BaseModel, Field


class ComplianceReviewStatusResponse(BaseModel):
    customer_id: str
    status: str
    reviewer: str | None = None
    reviewed_at: str | None = None
    reason: str | None = None
    risk_note: str | None = None
    quote_contract_blocked: bool
    ai_risk_tip: str


class CompliancePendingItem(BaseModel):
    customer_id: str
    customer_name: str
    grade: str
    status: str
    city: str | None = None
    risk_note: str | None = None


class CompliancePendingListResponse(BaseModel):
    items: list[CompliancePendingItem]


class ComplianceReviewRequest(BaseModel):
    actor: str = Field(min_length=1)
    actor_role: str = Field(min_length=1)
    status: str = Field(pattern="^(approved|rejected|pending)$")
    reason: str = Field(min_length=1)
    risk_note: str | None = None


class ComplianceReviewResponse(BaseModel):
    id: UUID
    customer_id: UUID
    status: str
    reviewer: str | None
    reviewed_at: str | None
    reason: str | None
    risk_note: str | None


class MarkQuotedRequest(BaseModel):
    actor: str = Field(min_length=1)
    actor_role: str = Field(default="sales", min_length=1)


class MarkQuotedResponse(BaseModel):
    customer_id: str
    quoted_status: str
