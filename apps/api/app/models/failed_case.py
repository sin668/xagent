from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Enum, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import JsonType
from app.models.enums import ChannelRiskLevel, FailedCaseType, enum_values


class FailedCase(Base):
    __tablename__ = "failed_cases"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    case_type: Mapped[FailedCaseType] = mapped_column(
        Enum(FailedCaseType, values_callable=enum_values),
        nullable=False,
        index=True,
    )
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    risk_level: Mapped[ChannelRiskLevel | None] = mapped_column(
        Enum(ChannelRiskLevel, values_callable=enum_values),
        nullable=True,
        index=True,
    )
    related_task_type: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    related_object_type: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    related_object_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    failure_reason: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_input_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_output_json: Mapped[dict | None] = mapped_column(JsonType, nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    prompt_version: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    usable_for_rag: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    touch_queue_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

