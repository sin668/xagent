from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import JsonType
from app.models.enums import ChannelPlanStatus, ChannelRiskLevel, SourceUsageType, enum_values


class ChannelPlan(Base):
    __tablename__ = "channel_plans"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    country: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    city: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    channel_name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    channel_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    risk_level: Mapped[ChannelRiskLevel] = mapped_column(
        Enum(ChannelRiskLevel, values_callable=enum_values),
        nullable=False,
        index=True,
    )
    source_usage_type: Mapped[SourceUsageType] = mapped_column(
        Enum(SourceUsageType, values_callable=enum_values),
        nullable=False,
        index=True,
    )
    keywords: Mapped[list[str]] = mapped_column(JsonType, nullable=False, default=list)
    daily_url_limit: Mapped[int] = mapped_column(Integer, nullable=False)
    daily_lead_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[ChannelPlanStatus] = mapped_column(
        Enum(ChannelPlanStatus, values_callable=enum_values),
        nullable=False,
        default=ChannelPlanStatus.DRAFT,
        index=True,
    )
    owner: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
