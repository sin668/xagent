from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import KnowledgeCollection, KnowledgeEmbedding, KnowledgeItem, KnowledgeUsageRecord
from app.models.email_reply_draft import EmailReplyDraft
from app.models.enums import KnowledgeEmbeddingStatus, KnowledgeItemStatus, KnowledgeReviewStatus, KnowledgeUsageOutcome
from app.models.review_log import ReviewLog


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
    REVIEW_SUBMIT_ROLES = {"operator", "admin", "knowledge_admin", "tech_admin"}
    REVIEW_PUBLISH_ROLES = {"knowledge_admin", "admin", "tech_admin"}
    RETRIEVAL_ACTIVATE_ROLES = {"tech_admin", "knowledge_admin", "admin"}
    ARCHIVE_ROLES = {"knowledge_admin", "admin", "tech_admin"}
    BLOCK_ROLES = {"compliance", "knowledge_admin", "admin", "tech_admin"}

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
        if error_message:
            embedding_status = KnowledgeEmbeddingStatus.FAILED
        elif embedding is None:
            embedding_status = KnowledgeEmbeddingStatus.PENDING
        else:
            embedding_status = KnowledgeEmbeddingStatus.READY
        return {
            "item_id": UUID(str(item_id)),
            "embedding_model": embedding_model,
            "embedding": embedding,
            "embedding_dimensions": embedding_dimensions,
            "embedding_status": embedding_status,
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

    def list_review_logs(self, item_id: UUID) -> list[ReviewLog]:
        return list(
            self.session.scalars(
                select(ReviewLog)
                .where(ReviewLog.task_id == str(item_id))
                .where(ReviewLog.agent_name == "knowledge_governance")
                .order_by(ReviewLog.created_at.desc(), ReviewLog.id.desc())
            ).all()
        )

    def create_usage_record(self, item_id: UUID, *, payload: dict) -> KnowledgeUsageRecord:
        item = self._require_item(item_id)
        email_reply_draft_id = payload.get("email_reply_draft_id")
        if email_reply_draft_id is not None and self.session.get(EmailReplyDraft, email_reply_draft_id) is None:
            raise ValueError("email reply draft 不存在。")
        record = KnowledgeUsageRecord(
            knowledge_item_id=item.id,
            knowledge_version=item.version,
            email_reply_draft_id=email_reply_draft_id,
            retrieval_query=payload.get("retrieval_query"),
            similarity_score=payload.get("similarity_score"),
            rank=payload.get("rank"),
            filters_json=payload.get("filters_json") or {},
            outcome=KnowledgeUsageOutcome(payload.get("outcome", KnowledgeUsageOutcome.RETRIEVED.value)),
            adopted=payload.get("adopted", False),
            edit_distance_ratio=payload.get("edit_distance_ratio"),
            caused_bounce=payload.get("caused_bounce", False),
            customer_replied=payload.get("customer_replied", False),
            suggest_deprecate=payload.get("suggest_deprecate", False),
            suggest_deprecate_reason=payload.get("suggest_deprecate_reason"),
        )
        self.session.add(record)
        self.session.flush()
        return record

    def quality_summary(self, item_id: UUID) -> dict:
        item = self._require_item(item_id)
        records = list(
            self.session.scalars(
                select(KnowledgeUsageRecord)
                .where(KnowledgeUsageRecord.knowledge_item_id == item.id)
                .order_by(KnowledgeUsageRecord.created_at.desc())
            ).all()
        )
        retrieval_count = len(records)
        adoption_count = sum(1 for record in records if record.adopted)
        bounce_count = sum(1 for record in records if record.caused_bounce)
        customer_reply_count = sum(1 for record in records if record.customer_replied)
        edit_ratios = [record.edit_distance_ratio for record in records if record.edit_distance_ratio is not None]
        suggest_deprecate_records = [record for record in records if record.suggest_deprecate]
        return {
            "knowledge_item_id": item.id,
            "knowledge_version": item.version,
            "retrieval_count": retrieval_count,
            "adoption_count": adoption_count,
            "adoption_rate": self._rate(adoption_count, retrieval_count),
            "average_edit_distance_ratio": round(sum(edit_ratios) / len(edit_ratios), 4) if edit_ratios else None,
            "bounce_count": bounce_count,
            "bounce_rate": self._rate(bounce_count, retrieval_count),
            "customer_reply_count": customer_reply_count,
            "customer_reply_rate": self._rate(customer_reply_count, retrieval_count),
            "suggest_deprecate": bool(suggest_deprecate_records),
            "suggest_deprecate_reason": suggest_deprecate_records[0].suggest_deprecate_reason
            if suggest_deprecate_records
            else None,
        }

    def submit_review(self, item_id: UUID, *, actor: str, actor_role: str, review_note: str | None) -> KnowledgeItem:
        self._ensure_role(actor_role, self.REVIEW_SUBMIT_ROLES, "只有运营、管理员或知识管理员可以提交知识审核")
        item = self._require_item(item_id)
        self._set_workflow_state(
            item,
            workflow_state="in_review",
            status=KnowledgeItemStatus.DRAFT,
            review_status=KnowledgeReviewStatus.APPROVED,
            actor=actor,
            review_note=review_note,
            action="knowledge_submit_review",
        )
        return item

    def publish_item(self, item_id: UUID, *, actor: str, actor_role: str, review_note: str | None) -> KnowledgeItem:
        self._ensure_role(actor_role, self.REVIEW_PUBLISH_ROLES, "只有知识管理员、管理员或技术管理员可以发布知识")
        item = self._require_item(item_id)
        self._set_workflow_state(
            item,
            workflow_state="pending_embedding",
            status=KnowledgeItemStatus.DRAFT,
            review_status=KnowledgeReviewStatus.APPROVED,
            actor=actor,
            review_note=review_note,
            action="knowledge_publish",
            extra_metadata={"published_by": actor, "published_at": datetime.utcnow().isoformat()},
        )
        return item

    def activate_retrieval(self, item_id: UUID, *, actor: str, actor_role: str, review_note: str | None) -> KnowledgeItem:
        self._ensure_role(actor_role, self.RETRIEVAL_ACTIVATE_ROLES, "只有技术管理员、知识管理员或管理员可以激活知识召回")
        item = self._require_item(item_id)
        self._set_workflow_state(
            item,
            workflow_state="active_for_retrieval",
            status=KnowledgeItemStatus.ACTIVE,
            review_status=KnowledgeReviewStatus.APPROVED,
            actor=actor,
            review_note=review_note,
            action="knowledge_activate_retrieval",
            extra_metadata={"activated_by": actor, "activated_at": datetime.utcnow().isoformat()},
        )
        return item

    def archive_item(self, item_id: UUID, *, actor: str, actor_role: str, review_note: str | None) -> KnowledgeItem:
        self._ensure_role(actor_role, self.ARCHIVE_ROLES, "只有知识管理员、管理员或技术管理员可以下线知识")
        item = self._require_item(item_id)
        self._set_workflow_state(
            item,
            workflow_state="archived",
            status=KnowledgeItemStatus.DEPRECATED,
            review_status=KnowledgeReviewStatus.APPROVED,
            actor=actor,
            review_note=review_note,
            action="knowledge_archive",
            extra_metadata={"auto_reply_allowed": False},
        )
        return item

    def block_item(self, item_id: UUID, *, actor: str, actor_role: str, review_note: str | None) -> KnowledgeItem:
        self._ensure_role(actor_role, self.BLOCK_ROLES, "只有合规、知识管理员、管理员或技术管理员可以阻断知识")
        item = self._require_item(item_id)
        self._set_workflow_state(
            item,
            workflow_state="blocked",
            status=KnowledgeItemStatus.DISABLED,
            review_status=KnowledgeReviewStatus.REJECTED,
            actor=actor,
            review_note=review_note,
            action="knowledge_block",
            extra_metadata={"risk_level": "blocked", "auto_reply_allowed": False},
        )
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

    def retry_embedding(self, embedding_id: UUID) -> KnowledgeEmbedding:
        record = self.session.get(KnowledgeEmbedding, embedding_id)
        if record is None:
            raise ValueError("embedding 任务不存在。")
        if record.embedding_status != KnowledgeEmbeddingStatus.FAILED:
            raise PermissionError("只有 failed 状态的 embedding 任务可以重试。")
        record.embedding_status = KnowledgeEmbeddingStatus.PENDING
        record.embedding = None
        record.error_message = None
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

    def _require_item(self, item_id: UUID) -> KnowledgeItem:
        item = self.get_item(item_id)
        if item is None:
            raise ValueError("knowledge item 不存在。")
        return item

    @staticmethod
    def _ensure_role(actor_role: str, allowed_roles: set[str], message: str) -> None:
        role = str(actor_role or "").strip().lower()
        if role not in allowed_roles:
            raise PermissionError(message)

    @staticmethod
    def _rate(numerator: int, denominator: int) -> float:
        if denominator == 0:
            return 0.0
        return round(numerator / denominator, 4)

    def _set_workflow_state(
        self,
        item: KnowledgeItem,
        *,
        workflow_state: str,
        status: KnowledgeItemStatus,
        review_status: KnowledgeReviewStatus,
        actor: str,
        review_note: str | None,
        action: str,
        extra_metadata: dict | None = None,
    ) -> None:
        metadata = dict(item.metadata_json or {})
        metadata.update(extra_metadata or {})
        metadata["workflow_state"] = workflow_state
        if review_note is not None:
            metadata["last_review_note"] = review_note
        item.metadata_json = metadata
        item.status = status
        item.review_status = review_status
        item.updated_at = datetime.utcnow()
        self.session.add(
            ReviewLog(
                task_id=str(item.id),
                agent_name="knowledge_governance",
                action=action,
                reviewer=actor,
                input_ref=review_note,
                output_ref=f"workflow_state={workflow_state};status={status.value};review_status={review_status.value}",
                result="success",
            )
        )
        self.session.flush()

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
