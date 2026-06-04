from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class InventoryItemCreate(BaseModel):
    external_id: str | None = None
    brand: str = Field(min_length=1)
    model: str = Field(min_length=1)
    year: int | None = None
    mileage_km: int | None = None
    vehicle_type: str | None = None
    condition_summary: str | None = None
    configuration: str | None = None
    quoted_price: Decimal | None = None
    currency: str = "USD"
    quote_status: str = Field(default="pending", pattern="^(pending|confirmed|expired|recheck_required)$")
    export_ready: bool = False
    media_urls: list[str] = Field(default_factory=list)
    valid_until: datetime | None = None
    source_ref: str | None = None


class InventoryItemResponse(BaseModel):
    id: UUID
    external_id: str | None
    brand: str
    model: str
    year: int | None
    mileage_km: int | None
    vehicle_type: str | None
    condition_summary: str | None
    configuration: str | None
    quoted_price: Decimal | None
    currency: str
    quote_status: str
    export_ready: bool
    media_urls: list[str]
    valid_until: datetime | None
    source_ref: str | None
    is_expired: bool
    can_ai_quote: bool
    priority_recommendable: bool
    risk_flags: list[str]


class InventoryItemListResponse(BaseModel):
    items: list[InventoryItemResponse]


class InventoryQuoteSafetyResponse(BaseModel):
    external_id: str | None
    can_ai_quote: bool
    blocking_reasons: list[str]
