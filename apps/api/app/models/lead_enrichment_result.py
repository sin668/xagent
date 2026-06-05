from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import JsonType
from app.models.enums import LeadEnrichmentResultStatus, LeadEnrichmentType, enum_values


class LeadEnrichmentResult(Base):
    __tablename__ = "lead_enrichment_results"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    staging_lead_id: Mapped[UUID] = mapped_column(
        ForeignKey("staging_leads.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    enrichment_type: Mapped[LeadEnrichmentType] = mapped_column(
        Enum(LeadEnrichmentType, values_callable=enum_values),
        nullable=False,
        index=True,
    )
    triggered_by: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    status: Mapped[LeadEnrichmentResultStatus] = mapped_column(
        Enum(LeadEnrichmentResultStatus, values_callable=enum_values),
        nullable=False,
        default=LeadEnrichmentResultStatus.PENDING,
        index=True,
    )
    input_snapshot_json: Mapped[dict] = mapped_column(JsonType, nullable=False, default=dict)
    output_json: Mapped[dict | None] = mapped_column(JsonType, nullable=True)
    evidence_links: Mapped[list] = mapped_column(JsonType, nullable=False, default=list)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    missing_fields: Mapped[list] = mapped_column(JsonType, nullable=False, default=list)
    recommended_action: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    agent_task_run_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("agent_task_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
