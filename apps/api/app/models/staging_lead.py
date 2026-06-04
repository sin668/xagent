from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import (
    CustomerGrade,
    CustomerType,
    StagingQueueStatus,
    StagingReviewStatus,
    enum_values,
)


class StagingLead(Base):
    __tablename__ = "staging_leads"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    candidate_url_id: Mapped[UUID] = mapped_column(ForeignKey("candidate_urls.id", ondelete="RESTRICT"), nullable=False, index=True)
    customer_name: Mapped[str] = mapped_column(String(255), nullable=False, default="Unknown", index=True)
    country: Mapped[str] = mapped_column(String(80), nullable=False, default="Unknown", index=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    customer_type: Mapped[CustomerType] = mapped_column(
        Enum(CustomerType, values_callable=enum_values),
        nullable=False,
        default=CustomerType.UNKNOWN,
        index=True,
    )
    contacts_json: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    activity_level: Mapped[str | None] = mapped_column(String(80), nullable=True)
    scale_signal: Mapped[str | None] = mapped_column(Text, nullable=True)
    import_used_car_relevance: Mapped[str | None] = mapped_column(String(120), nullable=True)
    source_evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommended_grade: Mapped[CustomerGrade] = mapped_column(
        Enum(CustomerGrade, values_callable=enum_values),
        nullable=False,
        index=True,
    )
    recommended_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    missing_fields: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    review_status: Mapped[StagingReviewStatus] = mapped_column(
        Enum(StagingReviewStatus, values_callable=enum_values),
        nullable=False,
        index=True,
    )
    queue_status: Mapped[StagingQueueStatus] = mapped_column(
        Enum(StagingQueueStatus, values_callable=enum_values),
        nullable=False,
        index=True,
    )
    dedupe_key: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    requires_compliance_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    candidate_url = relationship("CandidateUrl", back_populates="staging_leads")
