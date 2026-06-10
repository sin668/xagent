from uuid import UUID

from pydantic import BaseModel, Field


class OutreachDraftComplianceCheck(BaseModel):
    key: str
    label: str
    passed: bool


class OutreachDraftAudit(BaseModel):
    model: str
    prompt_version: str
    input_saved: bool
    output_saved: bool
    rag_context: dict | None = None


class OutreachDraftResponse(BaseModel):
    customer_id: UUID
    customer_name: str
    template_id: str
    template_status: str
    version: str
    generated_at: str
    subject: str
    body: str
    refusal_path: str
    risk_tips: list[str]
    compliance_checks: list[OutreachDraftComplianceCheck]
    block_reasons: list[str]
    can_generate_draft: bool
    can_record_sent: bool
    manual_only: bool
    auto_send_enabled: bool
    audit: OutreachDraftAudit


class ManualSendRecordRequest(BaseModel):
    human_confirmed: bool
    sender: str = Field(min_length=1)
    channel: str = Field(min_length=1)


class ManualSendRecordResponse(BaseModel):
    customer_id: UUID
    draft_id: str
    template_id: str
    status: str
    sender: str
    channel: str
    sent_at: str
    auto_send: bool


class OutreachEmailSendRequest(BaseModel):
    to_email: str = Field(min_length=1)
    subject: str = Field(min_length=1)
    body: str = Field(min_length=1)
    sender: str = Field(default="mobile-operator", min_length=1)
    human_confirmed: bool = True


class OutreachEmailSendResponse(BaseModel):
    customer_id: UUID
    status: str
    provider: str
    provider_message_id: str | None = None
    to_email: str
    subject: str
    auto_send: bool = False
