from uuid import UUID

from pydantic import BaseModel, Field


class CustomerSummary(BaseModel):
    id: str
    external_id: str | None
    name: str
    grade: str
    status: str
    do_not_contact: bool
    country: str | None = None
    city: str | None = None
    customer_type: str | None = None
    primary_channel: str | None = None
    risk_level: str | None = None
    evidence_note: str | None = None
    ai_recommended_grade: str | None = None
    ai_recommendation_reason: str | None = None
    missing_fields: str | None = None
    sources: list[dict] = Field(default_factory=list)
    contacts: list[dict] = Field(default_factory=list)
    do_not_contact_reason: str | None = None
    do_not_contact_marked_by: str | None = None
    do_not_contact_marked_at: str | None = None


class CustomerListResponse(BaseModel):
    items: list[CustomerSummary]


class DoNotContactRequest(BaseModel):
    actor: str = Field(min_length=1)
    reason: str = Field(min_length=1)


class OutreachRecordCreate(BaseModel):
    channel: str = Field(pattern="^(email|phone|whatsapp|telegram|vkontakte|odnoklassniki|tiktok|max|website|website_form|other)$")
    status: str = Field(pattern="^(draft|ready_for_manual_send|sent|replied|rejected|no_response|bad_contact|closed)$")
    sent_by: str | None = None
    owner: str | None = None
    response_summary: str | None = None
    next_action: str | None = None
    do_not_contact_reason: str | None = None
    external_id: str | None = None
    manual_confirmed: bool = False
    script_version: str | None = None


class OutreachRecordResponse(BaseModel):
    id: UUID
    external_id: str | None
    customer_id: UUID
    channel: str
    status: str
    sent_by: str | None = None
    owner: str | None = None
    script_version: str | None = None
    response_summary: str | None = None
    next_action: str | None = None
    triggers_do_not_contact: bool
    do_not_contact_reason: str | None = None


class OutreachRecordListResponse(BaseModel):
    items: list[OutreachRecordResponse]
