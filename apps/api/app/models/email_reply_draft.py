from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import EmailReplyDraftStatus, enum_values


class EmailReplyDraft(Base):
    __tablename__ = "email_reply_drafts"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    thread_id: Mapped[UUID] = mapped_column(ForeignKey("email_threads.id", ondelete="CASCADE"), nullable=False, index=True)
    message_id: Mapped[UUID] = mapped_column(ForeignKey("email_messages.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_id: Mapped[UUID | None] = mapped_column(ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True)
    agent_service_run_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True, index=True)
    agent_task_run_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("agent_task_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    prompt_template_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("llm_prompt_templates.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    prompt_version: Mapped[str | None] = mapped_column(String(40), nullable=True)
    model: Mapped[str | None] = mapped_column(String(120), nullable=True)
    detected_language: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    reply_language: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    language_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    ai_suggested_subject: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ai_suggested_body: Mapped[str] = mapped_column(Text, nullable=False)
    final_subject: Mapped[str | None] = mapped_column(String(500), nullable=True)
    final_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    knowledge_hits_json: Mapped[list[dict]] = mapped_column(JSONB, nullable=False, default=list)
    auto_send_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    auto_send_decision_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    manual_review_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    manual_review_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[EmailReplyDraftStatus] = mapped_column(
        Enum(EmailReplyDraftStatus, values_callable=enum_values),
        nullable=False,
        default=EmailReplyDraftStatus.DRAFTED,
        index=True,
    )
    reviewed_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sent_record_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("outreach_records.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    thread = relationship("EmailThread", back_populates="reply_drafts")
    message = relationship("EmailMessage", back_populates="reply_drafts")
    customer = relationship("Customer", back_populates="email_reply_drafts")
    agent_task_run = relationship("AgentTaskRun")
    prompt_template = relationship("LLMPromptTemplate")
    sent_record = relationship("OutreachRecord")
    send_attempts = relationship("EmailSendAttempt", back_populates="reply_draft")
