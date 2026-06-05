from pydantic import BaseModel, Field


class EmailKnowledgeHitResponse(BaseModel):
    id: str | None = None
    title: str
    note: str | None = None
    similarity_score: float | None = None
    auto_reply_allowed: bool = False


class EmailReplySummary(BaseModel):
    id: str
    thread_id: str | None = None
    customer_name: str
    customer_grade: str
    subject: str
    preview: str | None = None
    language: str | None = None
    auto_send_decision: str = Field(pattern="^(auto_send_allowed|manual_review|blocked)$")
    hard_block_reasons: list[str] = Field(default_factory=list)
    knowledge_hits: list[EmailKnowledgeHitResponse] = Field(default_factory=list)
    risk_level: str | None = None
    received_at: str | None = None


class EmailReplyListResponse(BaseModel):
    items: list[EmailReplySummary] = Field(default_factory=list)
    total: int = 0


class EmailReplyDraftResponse(BaseModel):
    subject: str | None = None
    body: str | None = None
    prompt_version: str = "email-reply-v1"


class EmailAutoSendCheckResponse(BaseModel):
    decision: str = Field(pattern="^(auto_send_allowed|manual_review|blocked)$")
    allow_auto_send: bool = False
    reasons: list[str] = Field(default_factory=list)
    hard_blocks: list[str] = Field(default_factory=list)


class EmailReplyDetailResponse(EmailReplySummary):
    inbound_body: str | None = None
    reply_draft: EmailReplyDraftResponse = Field(default_factory=EmailReplyDraftResponse)
    auto_send_check: EmailAutoSendCheckResponse
    ai_audit: dict = Field(default_factory=dict)


class EmailReplyActionRequest(BaseModel):
    actor: str = Field(min_length=1)
    review_note: str | None = None
    manual_confirmed: bool = True
    final_subject: str | None = None
    final_body: str | None = None


class EmailSendPreviewResponse(BaseModel):
    reply_id: str
    decision: str = Field(pattern="^(auto_send_allowed|manual_review|blocked)$")
    allow_auto_send: bool = False
    send_triggered: bool = False
    from_email: str
    to_emails: list[str] = Field(default_factory=list)
    cc_emails: list[str] = Field(default_factory=list)
    subject: str
    body_text: str
    knowledge_hit_count: int = 0
    reasons: list[str] = Field(default_factory=list)
    hard_blocks: list[str] = Field(default_factory=list)
    manual_review_required: bool = True
    manual_review_reason: str | None = None
