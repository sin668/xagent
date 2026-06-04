from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import ChannelRiskLevel, CollectionTaskStatus, SourceUsageType, enum_values


class CollectionTask(Base):
    __tablename__ = "collection_tasks"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    plan_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True, index=True)
    task_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    channel_name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
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
    max_sample_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    allowed_actions: Mapped[str] = mapped_column(Text, nullable=False)
    forbidden_actions: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[CollectionTaskStatus] = mapped_column(
        Enum(CollectionTaskStatus, values_callable=enum_values),
        nullable=False,
        default=CollectionTaskStatus.PENDING,
        index=True,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    candidate_urls = relationship("CandidateUrl", back_populates="task", cascade="all, delete-orphan")
