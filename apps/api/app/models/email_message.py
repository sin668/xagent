from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import EmailMessageDirection, EmailMessageSourceType, EmailMessageStatus, enum_values


class EmailMessage(Base):
    __tablename__ = "email_messages"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    thread_id: Mapped[UUID] = mapped_column(ForeignKey("email_threads.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_id: Mapped[UUID | None] = mapped_column(ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True)
    direction: Mapped[EmailMessageDirection] = mapped_column(
        Enum(EmailMessageDirection, values_callable=enum_values),
        nullable=False,
        index=True,
    )
    from_email: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    to_emails: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    cc_emails: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    body_text: Mapped[str] = mapped_column(Text, nullable=False)
    body_html: Mapped[str | None] = mapped_column(Text, nullable=True)
    language: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    status: Mapped[EmailMessageStatus] = mapped_column(
        Enum(EmailMessageStatus, values_callable=enum_values),
        nullable=False,
        default=EmailMessageStatus.RECEIVED,
        index=True,
    )
    source_type: Mapped[EmailMessageSourceType] = mapped_column(
        Enum(EmailMessageSourceType, values_callable=enum_values),
        nullable=False,
        default=EmailMessageSourceType.MANUAL,
        index=True,
    )
    external_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
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

    thread = relationship("EmailThread", back_populates="messages")
    customer = relationship("Customer", back_populates="email_messages")
    reply_drafts = relationship("EmailReplyDraft", back_populates="message", cascade="all, delete-orphan")
