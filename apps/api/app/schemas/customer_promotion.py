from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import CustomerStatus


class CustomerPromotionEligibilityResponse(BaseModel):
    staging_lead_id: UUID
    can_promote: bool
    status: str
    reasons: list[str]
    missing_required_fields: list[str]
    pending_optional_fields: list[str]
    requires_compliance_review: bool
    source_url: str | None = None


class PromoteStagingLeadToCustomerRequest(BaseModel):
    actor: str = Field(min_length=1, max_length=120)
    accepted_fields_json: dict = Field(min_length=1)
    review_note: str | None = None


class PromoteStagingLeadToCustomerResponse(BaseModel):
    staging_lead_id: UUID
    customer_id: UUID
    customer_external_id: str | None
    lead_source_id: UUID
    contact_method_ids: list[UUID] = Field(default_factory=list)
    customer_status: CustomerStatus
    do_not_contact: bool
    requires_compliance_review: bool
    compliance_review_id: UUID | None = None
    review_log_id: UUID
