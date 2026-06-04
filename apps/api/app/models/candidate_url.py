from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import CandidateUrlStatus, ChannelRiskLevel, SourcePlatform, SourceUsageType, enum_values


class CandidateUrl(Base):
    __tablename__ = "candidate_urls"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    task_id: Mapped[UUID] = mapped_column(ForeignKey("collection_tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    url_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    source_platform: Mapped[SourcePlatform] = mapped_column(
        Enum(SourcePlatform, values_callable=enum_values),
        nullable=False,
        index=True,
    )
    source_risk_level: Mapped[ChannelRiskLevel] = mapped_column(
        Enum(ChannelRiskLevel, values_callable=enum_values),
        nullable=False,
        index=True,
    )
    source_usage_type: Mapped[SourceUsageType] = mapped_column(
        Enum(SourceUsageType, values_callable=enum_values),
        nullable=False,
        index=True,
    )
    requires_secondary_verification: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    queue_eligible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    discovery_reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[CandidateUrlStatus] = mapped_column(
        Enum(CandidateUrlStatus, values_callable=enum_values),
        nullable=False,
        default=CandidateUrlStatus.NEW,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    task = relationship("CollectionTask", back_populates="candidate_urls")
    page_snapshots = relationship("PageSnapshot", back_populates="candidate_url", cascade="all, delete-orphan")
    staging_leads = relationship("StagingLead", back_populates="candidate_url")
