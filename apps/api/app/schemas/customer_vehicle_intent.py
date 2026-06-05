from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import CustomerVehicleIntentSourceType, CustomerVehicleIntentStatus


class CustomerVehicleIntentCreate(BaseModel):
    customer_id: UUID
    brand: str | None = Field(default=None, max_length=120)
    model: str | None = Field(default=None, max_length=120)
    year_range: str | None = Field(default=None, max_length=80)
    vehicle_age: str | None = Field(default=None, max_length=80)
    quantity: int | None = Field(default=None, ge=1)
    budget_range: str | None = Field(default=None, max_length=120)
    purchase_frequency: str | None = Field(default=None, max_length=120)
    delivery_country: str | None = Field(default=None, max_length=80)
    delivery_city: str | None = Field(default=None, max_length=120)
    concerns: list[str] = Field(default_factory=list)
    source_type: CustomerVehicleIntentSourceType
    source_note: str | None = None
    status: CustomerVehicleIntentStatus = CustomerVehicleIntentStatus.ACTIVE
    created_by: str = Field(min_length=1, max_length=120)


class CustomerVehicleIntentUpdate(BaseModel):
    brand: str | None = Field(default=None, max_length=120)
    model: str | None = Field(default=None, max_length=120)
    year_range: str | None = Field(default=None, max_length=80)
    vehicle_age: str | None = Field(default=None, max_length=80)
    quantity: int | None = Field(default=None, ge=1)
    budget_range: str | None = Field(default=None, max_length=120)
    purchase_frequency: str | None = Field(default=None, max_length=120)
    delivery_country: str | None = Field(default=None, max_length=80)
    delivery_city: str | None = Field(default=None, max_length=120)
    concerns: list[str] | None = None
    source_type: CustomerVehicleIntentSourceType | None = None
    source_note: str | None = None
    status: CustomerVehicleIntentStatus | None = None


class CustomerVehicleIntentResponse(BaseModel):
    id: UUID
    customer_id: UUID
    brand: str | None
    model: str | None
    year_range: str | None
    vehicle_age: str | None
    quantity: int | None
    budget_range: str | None
    purchase_frequency: str | None
    delivery_country: str | None
    delivery_city: str | None
    concerns: list[str]
    source_type: CustomerVehicleIntentSourceType
    source_note: str | None
    status: CustomerVehicleIntentStatus
    created_by: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
