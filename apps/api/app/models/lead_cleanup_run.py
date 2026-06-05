from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import JsonType
from app.models.enums import LeadCleanupRunStatus, enum_values


class LeadCleanupRun(Base):
    __tablename__ = "lead_cleanup_runs"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    trigger_source: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    status: Mapped[LeadCleanupRunStatus] = mapped_column(
        Enum(LeadCleanupRunStatus, values_callable=enum_values),
        nullable=False,
        default=LeadCleanupRunStatus.PENDING,
        index=True,
    )
    input_filter_json: Mapped[dict] = mapped_column(JsonType, nullable=False, default=dict)
    output_summary_json: Mapped[dict | None] = mapped_column(JsonType, nullable=True)
    llm_provider: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    llm_model: Mapped[str | None] = mapped_column(String(120), nullable=True)
    prompt_template_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("llm_prompt_templates.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
