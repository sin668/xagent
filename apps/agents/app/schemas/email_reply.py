from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


EMAIL_REPLY_SCHEMA_VERSION = "email-reply-v1"


class EmailReplyRequestEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["email-reply-v1"] = EMAIL_REPLY_SCHEMA_VERSION
    request_id: UUID
    draft_id: UUID | None = None
    thread_id: UUID
    message_id: UUID
    customer_id: UUID | None = None
    context: dict[str, Any] = Field(default_factory=dict)
    prompt: dict[str, Any] = Field(default_factory=dict)
    options: dict[str, Any] = Field(default_factory=dict)


class EmailReplyKnowledgeHit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    knowledge_item_id: UUID | str
    title: str = Field(min_length=1)
    version: str = Field(min_length=1)
    similarity_score: float | None = Field(default=None, ge=0)
    evidence_note: str | None = None


class EmailReplyAgentOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["email-reply-v1"]
    reply_language: str = Field(min_length=1, max_length=20)
    detected_language: str | None = Field(default=None, max_length=20)
    suggested_subject: str = Field(min_length=1, max_length=500)
    suggested_body: str = Field(min_length=1)
    knowledge_hits: list[EmailReplyKnowledgeHit] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    auto_send_allowed: bool = False
    manual_review_required: bool = True
    next_action: Literal[
        "auto_send_candidate",
        "hold_for_manual_review",
        "block",
        "transfer_to_compliance",
        "reject",
    ]
    audit: dict[str, Any] = Field(default_factory=lambda: {"writes_core_tables": False})

    @model_validator(mode="after")
    def validate_safety_contract(self) -> "EmailReplyAgentOutput":
        if self.audit.get("writes_core_tables") is not False:
            raise ValueError("EMAIL_REPLY audit.writes_core_tables must be false.")
        if not self.auto_send_allowed and not self.manual_review_required:
            raise ValueError("manual_review_required must be true when auto_send_allowed is false.")
        if self.auto_send_allowed and self.manual_review_required:
            raise ValueError("manual_review_required must be false when auto_send_allowed is true.")
        if self.auto_send_allowed and self.next_action != "auto_send_candidate":
            raise ValueError("auto_send_allowed requires next_action=auto_send_candidate.")
        if not self.auto_send_allowed and self.next_action == "auto_send_candidate":
            raise ValueError("next_action=auto_send_candidate requires auto_send_allowed=true.")
        return self
