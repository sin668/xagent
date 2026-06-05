from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import ContactMethodType, OutreachStatus, enum_values


class OutreachRecord(Base):
    __tablename__ = "outreach_records"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    external_id: Mapped[str | None] = mapped_column(String(120), nullable=True, unique=True, index=True)
    customer_id: Mapped[UUID] = mapped_column(ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    channel: Mapped[ContactMethodType] = mapped_column(Enum(ContactMethodType, values_callable=enum_values), nullable=False)
    status: Mapped[OutreachStatus] = mapped_column(
        Enum(OutreachStatus, values_callable=enum_values),
        nullable=False,
        default=OutreachStatus.DRAFT,
    )
    script_version: Mapped[str | None] = mapped_column(String(80), nullable=True)
    sent_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    owner: Mapped[str | None] = mapped_column(String(120), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    response_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_action: Mapped[str | None] = mapped_column(String(120), nullable=True)
    triggers_do_not_contact: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    do_not_contact_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    customer = relationship("Customer", back_populates="outreach_records")
    email_send_attempts = relationship("EmailSendAttempt", back_populates="outreach_record")
