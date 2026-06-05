from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import JsonType
from app.models.enums import LeadCleanupSuggestionReviewStatus, LeadCleanupSuggestionType, enum_values


class LeadCleanupSuggestion(Base):
    __tablename__ = "lead_cleanup_suggestions"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    cleanup_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("lead_cleanup_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    staging_lead_id: Mapped[UUID] = mapped_column(
        ForeignKey("staging_leads.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    suggestion_type: Mapped[LeadCleanupSuggestionType] = mapped_column(
        Enum(LeadCleanupSuggestionType, values_callable=enum_values),
        nullable=False,
        index=True,
    )
    target_lead_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("staging_leads.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_json: Mapped[dict] = mapped_column(JsonType, nullable=False, default=dict)
    recommended_action: Mapped[str] = mapped_column(Text, nullable=False)
    review_status: Mapped[LeadCleanupSuggestionReviewStatus] = mapped_column(
        Enum(LeadCleanupSuggestionReviewStatus, values_callable=enum_values),
        nullable=False,
        default=LeadCleanupSuggestionReviewStatus.PENDING,
        index=True,
    )
    reviewer_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    executed_by: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    execution_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
