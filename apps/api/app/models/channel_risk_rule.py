from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Enum, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import ChannelRiskLevel, enum_values


class ChannelRiskRule(Base):
    __tablename__ = "channel_risk_rules"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    external_id: Mapped[str | None] = mapped_column(String(120), nullable=True, unique=True, index=True)
    channel_name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    channel_type: Mapped[str] = mapped_column(String(120), nullable=False)
    risk_level: Mapped[ChannelRiskLevel] = mapped_column(
        Enum(ChannelRiskLevel, values_callable=enum_values),
        nullable=False,
        index=True,
    )
    collection_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ai_processing_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    allowed_actions: Mapped[str] = mapped_column(Text, nullable=False)
    forbidden_actions: Mapped[str] = mapped_column(Text, nullable=False)
    policy_source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    last_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
