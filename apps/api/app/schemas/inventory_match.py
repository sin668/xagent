from uuid import UUID

from pydantic import BaseModel, Field


class InventoryMatchRequest(BaseModel):
    vehicle_type: str | None = None
    min_year: int | None = None
    max_price: float | None = None
    requires_compliance_review: bool = False


class InventoryMatchItemResponse(BaseModel):
    match_id: UUID
    inventory_item_id: UUID
    inventory_external_id: str | None
    brand: str
    model: str
    year: int | None
    vehicle_type: str | None
    condition_summary: str | None
    quoted_price: float | None
    currency: str
    export_ready: bool
    valid_until: str | None
    priority_recommendable: bool
    recommendation_reason: str
    risk_tips: list[str]
    requires_compliance_review: bool


class InventoryMatchListResponse(BaseModel):
    customer_id: UUID
    quote_disclaimer: str
    items: list[InventoryMatchItemResponse]


class InventoryMatchDecisionRequest(BaseModel):
    decision: str = Field(pattern="^(advance_quote|not_match)$")
    owner: str = Field(min_length=1)
    note: str | None = None


class InventoryMatchDecisionResponse(BaseModel):
    match_id: UUID
    decision: str
    owner: str
    note: str | None
    formal_quote_allowed: bool
    next_gate: str
