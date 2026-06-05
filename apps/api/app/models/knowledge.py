from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import JsonType, VectorType
from app.models.enums import KnowledgeEmbeddingStatus, KnowledgeItemStatus, KnowledgeReviewStatus, KnowledgeUsageOutcome, enum_values


class KnowledgeCollection(Base):
    __tablename__ = "knowledge_collections"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(160), nullable=False, unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[KnowledgeItemStatus] = mapped_column(
        Enum(KnowledgeItemStatus, values_callable=enum_values),
        nullable=False,
        default=KnowledgeItemStatus.DRAFT,
        index=True,
    )
    review_status: Mapped[KnowledgeReviewStatus] = mapped_column(
        Enum(KnowledgeReviewStatus, values_callable=enum_values),
        nullable=False,
        default=KnowledgeReviewStatus.PENDING,
        index=True,
    )
    version: Mapped[str] = mapped_column(String(80), nullable=False, default="v1")
    source_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    items = relationship("KnowledgeItem", back_populates="collection", cascade="all, delete-orphan")


class KnowledgeItem(Base):
    __tablename__ = "knowledge_items"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    collection_id: Mapped[UUID] = mapped_column(
        ForeignKey("knowledge_collections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(String(20), nullable=False, default="zh", index=True)
    country: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    applicable_channels: Mapped[list] = mapped_column(JsonType, nullable=False, default=list)
    status: Mapped[KnowledgeItemStatus] = mapped_column(
        Enum(KnowledgeItemStatus, values_callable=enum_values),
        nullable=False,
        default=KnowledgeItemStatus.DRAFT,
        index=True,
    )
    review_status: Mapped[KnowledgeReviewStatus] = mapped_column(
        Enum(KnowledgeReviewStatus, values_callable=enum_values),
        nullable=False,
        default=KnowledgeReviewStatus.PENDING,
        index=True,
    )
    source_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[str] = mapped_column(String(80), nullable=False, default="v1", index=True)
    metadata_json: Mapped[dict | None] = mapped_column(JsonType, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    collection = relationship("KnowledgeCollection", back_populates="items")
    embeddings = relationship("KnowledgeEmbedding", back_populates="item", cascade="all, delete-orphan")
    usage_records = relationship("KnowledgeUsageRecord", back_populates="knowledge_item", cascade="all, delete-orphan")
    quality_metrics = relationship("KnowledgeQualityMetric", back_populates="knowledge_item", cascade="all, delete-orphan")


class KnowledgeEmbedding(Base):
    __tablename__ = "knowledge_embeddings"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    item_id: Mapped[UUID] = mapped_column(ForeignKey("knowledge_items.id", ondelete="CASCADE"), nullable=False, index=True)
    embedding_model: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    embedding: Mapped[list | None] = mapped_column(VectorType(1536), nullable=True)
    embedding_dimensions: Mapped[int] = mapped_column(Integer, nullable=False, default=1536)
    embedding_status: Mapped[KnowledgeEmbeddingStatus] = mapped_column(
        Enum(KnowledgeEmbeddingStatus, values_callable=enum_values),
        nullable=False,
        default=KnowledgeEmbeddingStatus.PENDING,
        index=True,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    item = relationship("KnowledgeItem", back_populates="embeddings")


class KnowledgeUsageRecord(Base):
    __tablename__ = "knowledge_usage_records"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    knowledge_item_id: Mapped[UUID] = mapped_column(
        ForeignKey("knowledge_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    knowledge_version: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    email_reply_draft_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("email_reply_drafts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    retrieval_query: Mapped[str | None] = mapped_column(Text, nullable=True)
    similarity_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    filters_json: Mapped[dict] = mapped_column(JsonType, nullable=False, default=dict)
    outcome: Mapped[KnowledgeUsageOutcome] = mapped_column(
        Enum(KnowledgeUsageOutcome, values_callable=enum_values),
        nullable=False,
        default=KnowledgeUsageOutcome.RETRIEVED,
        index=True,
    )
    adopted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    edit_distance_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    caused_bounce: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    customer_replied: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    suggest_deprecate: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    suggest_deprecate_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    knowledge_item = relationship("KnowledgeItem", back_populates="usage_records")
    email_reply_draft = relationship("EmailReplyDraft", back_populates="knowledge_usage_records")


class KnowledgeQualityMetric(Base):
    __tablename__ = "knowledge_quality_metrics"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    knowledge_item_id: Mapped[UUID] = mapped_column(
        ForeignKey("knowledge_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    knowledge_version: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    retrieval_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    adoption_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    adoption_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    average_edit_distance_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    bounce_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    bounce_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    customer_reply_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    customer_reply_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    suggest_deprecate: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    suggest_deprecate_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    knowledge_item = relationship("KnowledgeItem", back_populates="quality_metrics")
