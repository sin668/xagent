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
        status: str | KnowledgeItemStatus | None = None,
        review_status: str | KnowledgeReviewStatus | None = None,
        language: str | None = None,
        content_type: str | None = None,
        business_scene: str | None = None,
        risk_level: str | None = None,
        auto_reply_allowed: bool | None = None,
        market: str | None = None,
        tone: str | None = None,
        limit: int = 100,
    ) -> list[KnowledgeItem]:
        statement = select(KnowledgeItem).order_by(KnowledgeItem.created_at.desc()).limit(limit)
        if production_rag_only:
            filters = self.production_rag_filters()
            statement = statement.where(KnowledgeItem.status == filters["status"])
            statement = statement.where(KnowledgeItem.review_status == filters["review_status"])
            statement = statement.where(KnowledgeItem.status.not_in(filters["exclude_statuses"]))
        if status is not None:
            statement = statement.where(KnowledgeItem.status == KnowledgeItemStatus(status))
        if review_status is not None:
            statement = statement.where(KnowledgeItem.review_status == KnowledgeReviewStatus(review_status))
        if language is not None:
            statement = statement.where(KnowledgeItem.language == language)
        items = list(self.session.scalars(statement).all())
        return [
            item
            for item in items
            if self.item_matches_business_filters(
                item,
                content_type=content_type,
                business_scene=business_scene,
                risk_level=risk_level,
                auto_reply_allowed=auto_reply_allowed,
                market=market,
                tone=tone,
            )
        ]

    def get_item(self, item_id: UUID) -> KnowledgeItem | None:
        return self.session.get(KnowledgeItem, item_id)

    def update_item(self, item_id: UUID, *, payload: dict) -> KnowledgeItem:
        item = self.get_item(item_id)
        if item is None:
            raise ValueError("knowledge item 不存在。")
        if item.status == KnowledgeItemStatus.ACTIVE and item.review_status == KnowledgeReviewStatus.APPROVED:
            return self._create_draft_version_from_published(item, payload=payload)
        self._apply_item_payload(item, payload=payload)
        self.session.flush()
        return item

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
    def item_matches_business_filters(
        cls,
        item: KnowledgeItem,
        *,
        content_type: str | None = None,
        business_scene: str | None = None,
        risk_level: str | None = None,
        auto_reply_allowed: bool | None = None,
        market: str | None = None,
        tone: str | None = None,
    ) -> bool:
        metadata = item.metadata_json or {}
        expected = {
            "content_type": content_type,
            "business_scene": business_scene,
            "risk_level": risk_level,
            "auto_reply_allowed": auto_reply_allowed,
            "market": market,
            "tone": tone,
        }
        return all(value is None or metadata.get(field_name) == value for field_name, value in expected.items())

    def _apply_item_payload(self, item: KnowledgeItem, *, payload: dict) -> None:
        metadata = self.build_business_metadata(
            metadata_json=payload.get("metadata_json", item.metadata_json),
            content_type=payload.get("content_type"),
            business_scene=payload.get("business_scene"),
            risk_level=payload.get("risk_level"),
            auto_reply_allowed=payload.get("auto_reply_allowed"),
            market=payload.get("market"),
            tone=payload.get("tone"),
        )
        for field_name in (
            "title",
            "body",
            "language",
            "country",
            "applicable_channels",
            "source_ref",
            "version",
        ):
            if field_name in payload and payload[field_name] is not None:
                setattr(item, field_name, payload[field_name])
        if "status" in payload and payload["status"] is not None:
            item.status = KnowledgeItemStatus(payload["status"])
        if "review_status" in payload and payload["review_status"] is not None:
            item.review_status = KnowledgeReviewStatus(payload["review_status"])
        item.metadata_json = metadata
        item.updated_at = datetime.utcnow()

    def _create_draft_version_from_published(self, item: KnowledgeItem, *, payload: dict) -> KnowledgeItem:
        metadata = dict(item.metadata_json or {})
        metadata.update(payload.get("metadata_json") or {})
        metadata["parent_item_id"] = str(item.id)
        if payload.get("change_reason") is not None:
            metadata["change_reason"] = payload["change_reason"]
        metadata = self.build_business_metadata(
            metadata_json=metadata,
            content_type=payload.get("content_type"),
            business_scene=payload.get("business_scene"),
            risk_level=payload.get("risk_level"),
            auto_reply_allowed=payload.get("auto_reply_allowed"),
            market=payload.get("market"),
            tone=payload.get("tone"),
        )
        draft = KnowledgeItem(
            collection_id=item.collection_id,
            title=payload.get("title") or item.title,
            body=payload.get("body") or item.body,
            language=payload.get("language") or item.language,
            country=payload.get("country") if payload.get("country") is not None else item.country,
            applicable_channels=payload.get("applicable_channels") or item.applicable_channels,
            status=KnowledgeItemStatus.DRAFT,
            review_status=KnowledgeReviewStatus.PENDING,
            source_ref=payload.get("source_ref") if payload.get("source_ref") is not None else item.source_ref,
            version=payload.get("version") or f"{item.version}-draft",
            metadata_json=metadata,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        self.session.add(draft)
        self.session.flush()
        return draft

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
