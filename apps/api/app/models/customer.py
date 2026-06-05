from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Enum, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import CustomerGrade, CustomerStatus, CustomerType, enum_values


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    external_id: Mapped[str | None] = mapped_column(String(120), nullable=True, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    normalized_name: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    country: Mapped[str] = mapped_column(String(80), nullable=False, default="Russia", index=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    customer_type: Mapped[CustomerType] = mapped_column(
        Enum(CustomerType, values_callable=enum_values),
        nullable=False,
        default=CustomerType.UNKNOWN,
    )
    grade: Mapped[CustomerGrade] = mapped_column(
        Enum(CustomerGrade, values_callable=enum_values),
        nullable=False,
        default=CustomerGrade.A,
        index=True,
    )
    status: Mapped[CustomerStatus] = mapped_column(
        Enum(CustomerStatus, values_callable=enum_values),
        nullable=False,
        default=CustomerStatus.PENDING_REVIEW,
        index=True,
    )
    owner: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    owner_team: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    do_not_contact: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    do_not_contact_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    do_not_contact_marked_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    do_not_contact_marked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ai_recommended_grade: Mapped[CustomerGrade | None] = mapped_column(
        Enum(CustomerGrade, values_callable=enum_values),
        nullable=True,
    )
    ai_recommendation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    missing_fields: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    sources = relationship("LeadSource", back_populates="customer", cascade="all, delete-orphan")
    contact_methods = relationship("ContactMethod", back_populates="customer", cascade="all, delete-orphan")
    outreach_records = relationship("OutreachRecord", back_populates="customer", cascade="all, delete-orphan")
    ai_audit_logs = relationship("AIAuditLog", back_populates="customer", cascade="all, delete-orphan")
    compliance_reviews = relationship("ComplianceReview", back_populates="customer", cascade="all, delete-orphan")
    vehicle_intents = relationship("CustomerVehicleIntent", back_populates="customer", cascade="all, delete-orphan")
    followups = relationship("CustomerFollowup", back_populates="customer", cascade="all, delete-orphan")
    email_threads = relationship("EmailThread", back_populates="customer")
    email_messages = relationship("EmailMessage", back_populates="customer")
