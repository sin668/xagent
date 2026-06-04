from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import ChannelRiskLevel, SourcePlatform, enum_values


class LeadSource(Base):
    __tablename__ = "lead_sources"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    external_id: Mapped[str | None] = mapped_column(String(120), nullable=True, unique=True, index=True)
    customer_id: Mapped[UUID] = mapped_column(ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    platform: Mapped[SourcePlatform] = mapped_column(Enum(SourcePlatform, values_callable=enum_values), nullable=False, index=True)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    source_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    evidence_note: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    channel_risk_level: Mapped[ChannelRiskLevel] = mapped_column(
        Enum(ChannelRiskLevel, values_callable=enum_values),
        nullable=False,
        index=True,
    )
    collected_keyword: Mapped[str | None] = mapped_column(String(255), nullable=True)
    collected_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    customer = relationship("Customer", back_populates="sources")
