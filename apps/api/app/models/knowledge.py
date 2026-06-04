from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import JsonType, VectorType
from app.models.enums import KnowledgeEmbeddingStatus, KnowledgeItemStatus, KnowledgeReviewStatus, enum_values


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

