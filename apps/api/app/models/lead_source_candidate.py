from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import JsonType
from app.models.enums import (
    ChannelRiskLevel,
    LeadSourceCandidateExtractionStatus,
    LeadSourceCandidateReviewStatus,
    SourcePlatform,
    enum_values,
)


class LeadSourceCandidate(Base):
    __tablename__ = "lead_source_candidates"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_domain: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    platform: Mapped[SourcePlatform] = mapped_column(Enum(SourcePlatform, values_callable=enum_values), nullable=False, index=True)
    channel_name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    country: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    risk_level: Mapped[ChannelRiskLevel] = mapped_column(Enum(ChannelRiskLevel, values_callable=enum_values), nullable=False, index=True)
    review_status: Mapped[LeadSourceCandidateReviewStatus] = mapped_column(
        Enum(LeadSourceCandidateReviewStatus, values_callable=enum_values),
        nullable=False,
        index=True,
    )
    approved_for_extraction: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    reviewer_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    discovery_method: Mapped[str] = mapped_column(String(120), nullable=False)
    discovery_query: Mapped[str | None] = mapped_column(Text, nullable=True)
    discovery_reason: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_note: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_links: Mapped[list] = mapped_column(JsonType, nullable=False, default=list)
    llm_provider: Mapped[str | None] = mapped_column(String(80), nullable=True)
    llm_model: Mapped[str | None] = mapped_column(String(120), nullable=True)
    llm_output_json: Mapped[dict | None] = mapped_column(JsonType, nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    extraction_status: Mapped[LeadSourceCandidateExtractionStatus] = mapped_column(
        Enum(LeadSourceCandidateExtractionStatus, values_callable=enum_values),
        nullable=False,
        default=LeadSourceCandidateExtractionStatus.PENDING,
        index=True,
    )
    last_extracted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    dedupe_key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    duplicate_of_id: Mapped[UUID | None] = mapped_column(ForeignKey("lead_source_candidates.id", ondelete="SET NULL"), nullable=True, index=True)
    is_duplicate: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    created_by_task_run_id: Mapped[UUID | None] = mapped_column(ForeignKey("agent_task_runs.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
