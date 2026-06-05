from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

from app.models import KnowledgeCollection, KnowledgeEmbedding, KnowledgeItem
from app.models.enums import KnowledgeEmbeddingStatus, KnowledgeItemStatus, KnowledgeReviewStatus
from app.services.knowledge import KnowledgeService


@dataclass(frozen=True)
class KnowledgeSearchResult:
    item: KnowledgeItem
    score: float
    match_reason: str
    search_mode: str


@dataclass(frozen=True)
class KnowledgeRetrievalFilterResult:
    item: KnowledgeItem
    similarity_score: float
    filter_conditions: dict


class KnowledgeSearchService:
    BLOCKED_RISK_LEVELS = {"blocked", "Forbidden", "High"}
    MISSING_LANGUAGE_READY_REASON = "缺少同语言 embedding_ready 知识，不能自动发送。"

    def __init__(self, session: Session) -> None:
        self.session = session

    @staticmethod
    def resolve_search_mode(
        *,
        query_embedding: list[float] | None,
        allow_keyword_fallback: bool,
    ) -> dict:
        if query_embedding:
            return {"search_mode": "vector", "fallback_reason": None}
        if allow_keyword_fallback:
            return {
                "search_mode": "keyword_fallback",
                "fallback_reason": "pgvector query embedding unavailable; using keyword fallback.",
            }
        return {
            "search_mode": "unavailable",
            "fallback_reason": "pgvector query embedding unavailable and keyword fallback disabled.",
        }

    @staticmethod
    def item_is_production_rag_eligible(item) -> bool:
        return KnowledgeService.is_rag_eligible(status=item.status, review_status=item.review_status)

    @classmethod
    def item_matches_filters(
        cls,
        item,
        *,
        collection: str | None = None,
        country: str | None = None,
        language: str | None = None,
        channel: str | None = None,
        content_type: str | None = None,
        business_scene: str | None = None,
        risk_level: str | None = None,
        auto_reply_only: bool = False,
        market: str | None = None,
        tone: str | None = None,
    ) -> bool:
        if not cls.item_is_production_rag_eligible(item):
            return False
        if KnowledgeItemStatus(item.status) == KnowledgeItemStatus.DEPRECATED:
            return False
        metadata = getattr(item, "metadata_json", None) or {}
        item_risk_level = metadata.get("risk_level")
        if item_risk_level in cls.BLOCKED_RISK_LEVELS:
            return False
        if auto_reply_only and metadata.get("auto_reply_allowed") is not True:
            return False
        if collection and getattr(getattr(item, "collection", None), "name", None) != collection:
            return False
        if country and item.country != country:
            return False
        if language and item.language != language:
            return False
        if channel and channel not in (item.applicable_channels or []):
            return False
        if content_type and metadata.get("content_type") != content_type:
            return False
        if business_scene and metadata.get("business_scene") != business_scene:
            return False
        if risk_level and item_risk_level != risk_level:
            return False
        if market and metadata.get("market") != market:
            return False
        if tone and metadata.get("tone") != tone:
            return False
        return True

    @staticmethod
    def keyword_score(item, query: str | None) -> float:
        if not (query or "").strip():
            return 1.0
        terms = [term.lower() for term in query.split() if term.strip()]
        haystack = f"{item.title}\n{item.body}".lower()
        score = sum(haystack.count(term) for term in terms)
        return float(score)

    @classmethod
    def keyword_fallback_search(
        cls,
        items: list,
        *,
        collection: str | None = None,
        country: str | None = None,
        language: str | None = None,
        channel: str | None = None,
        content_type: str | None = None,
        business_scene: str | None = None,
        risk_level: str | None = None,
        auto_reply_only: bool = False,
        market: str | None = None,
        tone: str | None = None,
        query: str | None = None,
        limit: int = 10,
    ) -> list[KnowledgeSearchResult]:
        results: list[KnowledgeSearchResult] = []
        for item in items:
            if not cls.item_matches_filters(
                item,
                collection=collection,
                country=country,
                language=language,
                channel=channel,
                content_type=content_type,
                business_scene=business_scene,
                risk_level=risk_level,
                auto_reply_only=auto_reply_only,
                market=market,
                tone=tone,
            ):
                continue
            score = cls.keyword_score(item, query)
            if query and score <= 0:
                continue
            results.append(
                KnowledgeSearchResult(
                    item=item,
                    score=score,
                    match_reason="keyword_match" if query else "approved_filter_match",
                    search_mode="keyword_fallback",
                )
            )
        return sorted(results, key=lambda result: result.score, reverse=True)[:limit]

    def list_candidate_items(self) -> list[KnowledgeItem]:
        statement = (
            select(KnowledgeItem)
            .options(selectinload(KnowledgeItem.collection))
            .where(KnowledgeItem.status == KnowledgeItemStatus.ACTIVE)
            .where(KnowledgeItem.review_status == KnowledgeReviewStatus.APPROVED)
            .where(KnowledgeItem.status != KnowledgeItemStatus.DEPRECATED)
        )
        return list(self.session.scalars(statement).all())

    def search(
        self,
        *,
        collection: str | None = None,
        country: str | None = None,
        language: str | None = None,
        channel: str | None = None,
        content_type: str | None = None,
        business_scene: str | None = None,
        risk_level: str | None = None,
        auto_reply_only: bool = False,
        market: str | None = None,
        tone: str | None = None,
        query: str | None = None,
        query_embedding: list[float] | None = None,
        allow_keyword_fallback: bool = True,
        limit: int = 10,
    ) -> tuple[list[KnowledgeSearchResult], dict]:
        mode = self.resolve_search_mode(
            query_embedding=query_embedding,
            allow_keyword_fallback=allow_keyword_fallback,
        )
        if mode["search_mode"] == "unavailable":
            raise ValueError(mode["fallback_reason"])

        if mode["search_mode"] == "vector":
            try:
                query_vector = "[" + ",".join(str(float(item)) for item in query_embedding or []) + "]"
                statement = (
                    select(KnowledgeItem)
                    .join(KnowledgeCollection)
                    .join(KnowledgeEmbedding)
                    .options(selectinload(KnowledgeItem.collection))
                    .where(KnowledgeItem.status == KnowledgeItemStatus.ACTIVE)
                    .where(KnowledgeItem.review_status == KnowledgeReviewStatus.APPROVED)
                    .where(KnowledgeItem.status != KnowledgeItemStatus.DEPRECATED)
                    .where(KnowledgeEmbedding.embedding_status == KnowledgeEmbeddingStatus.READY)
                    .order_by(KnowledgeEmbedding.embedding.op("<->")(query_vector))
                    .limit(limit)
                )
                if collection is not None:
                    statement = statement.where(KnowledgeCollection.name == collection)
                if country is not None:
                    statement = statement.where(KnowledgeItem.country == country)
                if language is not None:
                    statement = statement.where(KnowledgeItem.language == language)
                items = list(self.session.scalars(statement).all())
                items = [
                    item
                    for item in items
                    if self.item_matches_filters(
                        item,
                        collection=collection,
                        country=country,
                        language=language,
                        channel=channel,
                        content_type=content_type,
                        business_scene=business_scene,
                        risk_level=risk_level,
                        auto_reply_only=auto_reply_only,
                        market=market,
                        tone=tone,
                    )
                ]
                return (
                    [
                        KnowledgeSearchResult(
                            item=item,
                            score=1.0 / float(index + 1),
                            match_reason="vector_similarity",
                            search_mode="vector",
                        )
                        for index, item in enumerate(items)
                    ],
                    mode,
                )
            except SQLAlchemyError as exc:
                if not allow_keyword_fallback:
                    raise ValueError(f"pgvector search failed: {exc}") from exc
                mode = {
                    "search_mode": "keyword_fallback",
                    "fallback_reason": f"pgvector search failed; using keyword fallback: {exc}",
                }

        return (
            self.keyword_fallback_search(
                self.list_candidate_items(),
                collection=collection,
                country=country,
                language=language,
                channel=channel,
                content_type=content_type,
                business_scene=business_scene,
                risk_level=risk_level,
                auto_reply_only=auto_reply_only,
                market=market,
                tone=tone,
                query=query,
                limit=limit,
            ),
            mode,
        )

    @staticmethod
    def retrieval_filter_conditions(
        *,
        language: str,
        channel: str | None,
        content_types: list[str],
        business_scene: str | None,
        auto_send_candidate: bool,
        market: str | None,
        tone: str | None,
    ) -> dict:
        conditions = {
            "language": language,
            "channel": channel,
            "content_types": content_types,
            "business_scene": business_scene,
            "auto_send_candidate": auto_send_candidate,
            "market": market,
        }
        if tone is not None:
            conditions["tone"] = tone
        return conditions

    def retrieve_for_email_reply(
        self,
        *,
        query: str | None,
        language: str,
        channel: str | None,
        content_types: list[str],
        business_scene: str | None,
        auto_send_candidate: bool,
        market: str | None,
        tone: str | None,
        limit: int,
    ) -> tuple[list[KnowledgeRetrievalFilterResult], str | None]:
        filter_conditions = self.retrieval_filter_conditions(
            language=language,
            channel=channel,
            content_types=content_types,
            business_scene=business_scene,
            auto_send_candidate=auto_send_candidate,
            market=market,
            tone=tone,
        )
        statement = (
            select(KnowledgeItem)
            .join(KnowledgeEmbedding)
            .options(selectinload(KnowledgeItem.collection))
            .where(KnowledgeItem.status == KnowledgeItemStatus.ACTIVE)
            .where(KnowledgeItem.review_status == KnowledgeReviewStatus.APPROVED)
            .where(KnowledgeEmbedding.embedding_status == KnowledgeEmbeddingStatus.READY)
            .where(KnowledgeItem.language == language)
        )
        items = list(self.session.scalars(statement).unique().all())
        if not items:
            return [], self.MISSING_LANGUAGE_READY_REASON

        results: list[KnowledgeRetrievalFilterResult] = []
        for item in items:
            metadata = item.metadata_json or {}
            if metadata.get("risk_level") in self.BLOCKED_RISK_LEVELS:
                continue
            if auto_send_candidate and metadata.get("auto_reply_allowed") is not True:
                continue
            if channel and channel not in (item.applicable_channels or []):
                continue
            if content_types and metadata.get("content_type") not in content_types:
                continue
            if business_scene and metadata.get("business_scene") != business_scene:
                continue
            if market and metadata.get("market") != market:
                continue
            if tone and metadata.get("tone") != tone:
                continue
            score = self.keyword_score(item, query)
            if query and score <= 0:
                continue
            results.append(
                KnowledgeRetrievalFilterResult(
                    item=item,
                    similarity_score=score if score > 0 else 1.0,
                    filter_conditions=filter_conditions,
                )
            )

        return sorted(results, key=lambda result: result.similarity_score, reverse=True)[:limit], None
