from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import ChannelRiskLevel, RiskEventSeverity, RiskEventStatus, enum_values


class RiskEvent(Base):
    __tablename__ = "risk_events"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    channel_plan_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("channel_plans.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    task_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    agent_name: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    action: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    channel: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    risk_level: Mapped[ChannelRiskLevel] = mapped_column(
        Enum(ChannelRiskLevel, values_callable=enum_values),
        nullable=False,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    severity: Mapped[RiskEventSeverity] = mapped_column(
        Enum(RiskEventSeverity, values_callable=enum_values),
        nullable=False,
        index=True,
    )
    resolution_status: Mapped[RiskEventStatus] = mapped_column(
        Enum(RiskEventStatus, values_callable=enum_values),
        nullable=False,
        index=True,
    )
    block_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    pause_suggested: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    resolution_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    input_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    output_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    result: Mapped[str] = mapped_column(String(80), nullable=False, default="blocked", index=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
