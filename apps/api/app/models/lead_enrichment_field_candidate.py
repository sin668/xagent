from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import JsonType
from app.models.enums import (
    LeadEnrichmentFieldReviewStatus,
    LeadEnrichmentFieldSourceType,
    enum_values,
)


class LeadEnrichmentFieldCandidate(Base):
    __tablename__ = "lead_enrichment_field_candidates"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    enrichment_result_id: Mapped[UUID] = mapped_column(
        ForeignKey("lead_enrichment_results.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    staging_lead_id: Mapped[UUID] = mapped_column(
        ForeignKey("staging_leads.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    field_name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    candidate_value: Mapped[object] = mapped_column(JsonType, nullable=False)
    source_type: Mapped[LeadEnrichmentFieldSourceType] = mapped_column(
        Enum(LeadEnrichmentFieldSourceType, values_callable=enum_values),
        nullable=False,
        index=True,
    )
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_note: Mapped[str] = mapped_column(Text, nullable=False)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    review_status: Mapped[LeadEnrichmentFieldReviewStatus] = mapped_column(
        Enum(LeadEnrichmentFieldReviewStatus, values_callable=enum_values),
        nullable=False,
        default=LeadEnrichmentFieldReviewStatus.PENDING,
        index=True,
    )
    accepted_by: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
