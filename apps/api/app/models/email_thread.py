from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import EmailThreadStatus, enum_values


class EmailThread(Base):
    __tablename__ = "email_threads"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    customer_id: Mapped[UUID | None] = mapped_column(ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[EmailThreadStatus] = mapped_column(
        Enum(EmailThreadStatus, values_callable=enum_values),
        nullable=False,
        default=EmailThreadStatus.OPEN,
        index=True,
    )
    channel_account: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
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

    customer = relationship("Customer", back_populates="email_threads")
    messages = relationship("EmailMessage", back_populates="thread", cascade="all, delete-orphan")
