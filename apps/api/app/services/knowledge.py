from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import KnowledgeCollection, KnowledgeEmbedding, KnowledgeItem
from app.models.enums import KnowledgeEmbeddingStatus, KnowledgeItemStatus, KnowledgeReviewStatus


class KnowledgeService:
    SUPPORTED_CONTENT_TYPES = {
        "qa_entry",
        "email_reply_template",
        "compliance_phrase",
        "vehicle_product_note",
        "process_sop",
    }
    BUSINESS_METADATA_FIELDS = {
        "content_type",
        "business_scene",
        "risk_level",
        "auto_reply_allowed",
        "market",
        "tone",
    }

    def __init__(self, session: Session) -> None:
        self.session = session

    @staticmethod
    def is_rag_eligible(
        *,
        status: str | KnowledgeItemStatus,
        review_status: str | KnowledgeReviewStatus,
    ) -> bool:
        return (
            KnowledgeItemStatus(status) == KnowledgeItemStatus.ACTIVE
            and KnowledgeReviewStatus(review_status) == KnowledgeReviewStatus.APPROVED
        )

    @staticmethod
    def production_rag_filters() -> dict:
        return {
            "status": KnowledgeItemStatus.ACTIVE,
            "review_status": KnowledgeReviewStatus.APPROVED,
            "exclude_statuses": [KnowledgeItemStatus.DEPRECATED],
        }

    @staticmethod
    def build_embedding_payload(
        *,
        item_id: UUID | str,
        embedding_model: str,
        embedding: list[float] | None,
        embedding_dimensions: int = 1536,
        error_message: str | None = None,
    ) -> dict:
        return {
            "item_id": UUID(str(item_id)),
            "embedding_model": embedding_model,
            "embedding": embedding,
            "embedding_dimensions": embedding_dimensions,
            "embedding_status": KnowledgeEmbeddingStatus.FAILED if error_message else KnowledgeEmbeddingStatus.READY,
            "error_message": error_message,
        }

    def create_collection(
        self,
        *,
        name: str,
        description: str | None = None,
        status: str | KnowledgeItemStatus = KnowledgeItemStatus.DRAFT,
        review_status: str | KnowledgeReviewStatus = KnowledgeReviewStatus.PENDING,
        version: str = "v1",
        source_ref: str | None = None,
    ) -> KnowledgeCollection:
        collection = KnowledgeCollection(
            name=name,
            description=description,
            status=KnowledgeItemStatus(status),
            review_status=KnowledgeReviewStatus(review_status),
            version=version,
            source_ref=source_ref,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        self.session.add(collection)
        self.session.flush()
        return collection

    def get_collection_by_name(self, name: str) -> KnowledgeCollection | None:
        return self.session.scalar(select(KnowledgeCollection).where(KnowledgeCollection.name == name))

    def get_or_create_collection(
        self,
        *,
        name: str,
        description: str | None = None,
        status: str | KnowledgeItemStatus = KnowledgeItemStatus.DRAFT,
        review_status: str | KnowledgeReviewStatus = KnowledgeReviewStatus.PENDING,
        version: str = "v1",
        source_ref: str | None = None,
    ) -> KnowledgeCollection:
        existing = self.get_collection_by_name(name)
        if existing is not None:
            return existing
        return self.create_collection(
            name=name,
            description=description,
            status=status,
            review_status=review_status,
            version=version,
            source_ref=source_ref,
        )

    def list_collections(self, *, limit: int = 100) -> list[KnowledgeCollection]:
        return list(
            self.session.scalars(
                select(KnowledgeCollection).order_by(KnowledgeCollection.created_at.desc()).limit(limit)
            ).all()
        )

    def create_item(
        self,
        *,
        collection_id: UUID,
        title: str,
        body: str,
        language: str = "zh",
        country: str | None = None,
        applicable_channels: list | None = None,
        status: str | KnowledgeItemStatus = KnowledgeItemStatus.DRAFT,
        review_status: str | KnowledgeReviewStatus = KnowledgeReviewStatus.PENDING,
        source_ref: str | None = None,
        version: str = "v1",
        metadata_json: dict | None = None,
        content_type: str | None = None,
        business_scene: str | None = None,
        risk_level: str | None = None,
        auto_reply_allowed: bool | None = None,
        market: str | None = None,
        tone: str | None = None,
    ) -> KnowledgeItem:
        if self.session.get(KnowledgeCollection, collection_id) is None:
            raise ValueError("knowledge collection 不存在。")
        normalized_metadata = self.build_business_metadata(
            metadata_json=metadata_json,
            content_type=content_type,
            business_scene=business_scene,
            risk_level=risk_level,
            auto_reply_allowed=auto_reply_allowed,
            market=market,
            tone=tone,
        )
        item = KnowledgeItem(
            collection_id=collection_id,
            title=title,
            body=body,
            language=language,
            country=country,
            applicable_channels=applicable_channels or [],
            status=KnowledgeItemStatus(status),
            review_status=KnowledgeReviewStatus(review_status),
            source_ref=source_ref,
            version=version,
            metadata_json=normalized_metadata,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        self.session.add(item)
        self.session.flush()
        return item

    def list_items(
        self,
        *,
        production_rag_only: bool = False,
        limit: int = 100,
    ) -> list[KnowledgeItem]:
        statement = select(KnowledgeItem).order_by(KnowledgeItem.created_at.desc()).limit(limit)
        if production_rag_only:
            filters = self.production_rag_filters()
            statement = statement.where(KnowledgeItem.status == filters["status"])
            statement = statement.where(KnowledgeItem.review_status == filters["review_status"])
            statement = statement.where(KnowledgeItem.status.not_in(filters["exclude_statuses"]))
        return list(self.session.scalars(statement).all())

    def create_embedding(
        self,
        *,
        item_id: UUID,
        embedding_model: str,
        embedding: list[float] | None = None,
        embedding_dimensions: int = 1536,
        error_message: str | None = None,
    ) -> KnowledgeEmbedding:
        if self.session.get(KnowledgeItem, item_id) is None:
            raise ValueError("knowledge item 不存在。")
        record = KnowledgeEmbedding(
            **self.build_embedding_payload(
                item_id=item_id,
                embedding_model=embedding_model,
                embedding=embedding,
                embedding_dimensions=embedding_dimensions,
                error_message=error_message,
            ),
            created_at=datetime.utcnow(),
        )
        self.session.add(record)
        self.session.flush()
        return record

    @classmethod
    def build_business_metadata(
        cls,
        *,
        metadata_json: dict | None = None,
        content_type: str | None = None,
        business_scene: str | None = None,
        risk_level: str | None = None,
        auto_reply_allowed: bool | None = None,
        market: str | None = None,
        tone: str | None = None,
    ) -> dict | None:
        metadata = dict(metadata_json or {})
        field_values = {
            "content_type": content_type,
            "business_scene": business_scene,
            "risk_level": risk_level,
            "auto_reply_allowed": auto_reply_allowed,
            "market": market,
            "tone": tone,
        }
        if field_values["content_type"] is not None and field_values["content_type"] not in cls.SUPPORTED_CONTENT_TYPES:
            raise ValueError("knowledge content_type 不在允许范围内。")
        for field_name, value in field_values.items():
            if value is not None:
                metadata[field_name] = value
        return metadata or None
