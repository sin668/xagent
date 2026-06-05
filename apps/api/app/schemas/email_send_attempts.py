from pydantic import BaseModel, Field


class EmailSendAttemptActionRequest(BaseModel):
    actor: str = Field(min_length=1, max_length=120)
    bounce_reason: str | None = None


class EmailSendAttemptResponse(BaseModel):
    id: str
    reply_draft_id: str | None = None
    outreach_record_id: str | None = None
    provider: str
    provider_message_id: str | None = None
    from_email: str
    to_emails: list[str]
    cc_emails: list[str] | None = None
    subject_snapshot: str
    body_text_snapshot: str
    status: str
    attempt_count: int
    error_code: str | None = None
    error_message: str | None = None
    bounce_reason: str | None = None
    sent_at: str | None = None
