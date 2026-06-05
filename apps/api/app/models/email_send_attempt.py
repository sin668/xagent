from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import EmailSendAttemptStatus, enum_values


class EmailSendAttempt(Base):
    __tablename__ = "email_send_attempts"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    reply_draft_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("email_reply_drafts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    outreach_record_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("outreach_records.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    provider: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    provider_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    from_email: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    to_emails: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    cc_emails: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    bcc_emails: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    subject_snapshot: Mapped[str] = mapped_column(String(500), nullable=False)
    body_text_snapshot: Mapped[str] = mapped_column(Text, nullable=False)
    body_html_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[EmailSendAttemptStatus] = mapped_column(
        Enum(EmailSendAttemptStatus, values_callable=enum_values),
        nullable=False,
        default=EmailSendAttemptStatus.PENDING,
        index=True,
    )
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    error_code: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    bounce_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
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

    reply_draft = relationship("EmailReplyDraft", back_populates="send_attempts")
    outreach_record = relationship("OutreachRecord", back_populates="email_send_attempts")
