from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models.enums import AITaskType
from app.services.knowledge_search import KnowledgeSearchResult, KnowledgeSearchService


class RAGPromptContextService:
    """Build auditable RAG context blocks for LLM prompt inputs."""

    HARD_RULE_BOUNDARY = "RAG 仅作为 LLM 上下文，合规硬规则必须由规则服务执行。"
    COLLECTIONS_BY_TASK = {
        AITaskType.LEAD_EXTRACTION: ("keyword_library", "channel_sop"),
        AITaskType.LEAD_GRADING: ("compliance_rules", "failed_cases", "channel_sop"),
        AITaskType.OUTREACH_DRAFT: ("faq", "script_template", "compliance_rules"),
    }

    def __init__(self, session: Session) -> None:
        self.session = session
        self.search_service = KnowledgeSearchService(session)

    @classmethod
    def normalize_task_type(cls, task_type: str | AITaskType) -> AITaskType:
        return task_type if isinstance(task_type, AITaskType) else AITaskType(task_type)

    @classmethod
    def collections_for_task(cls, task_type: str | AITaskType) -> tuple[str, ...]:
        return cls.COLLECTIONS_BY_TASK.get(cls.normalize_task_type(task_type), ())

    @classmethod
    def _collection_name(cls, item: Any) -> str | None:
        return getattr(getattr(item, "collection", None), "name", None)

    @classmethod
    def _item_ref(cls, result: KnowledgeSearchResult) -> dict:
        item = result.item
        return {
            "knowledge_item_id": str(getattr(item, "id", "")),
            "collection": cls._collection_name(item),
            "title": getattr(item, "title", "Unknown"),
            "source_ref": getattr(item, "source_ref", None),
            "version": getattr(item, "version", None),
            "score": result.score,
            "match_reason": result.match_reason,
            "search_mode": result.search_mode,
        }

    @classmethod
    def _context_line(cls, result: KnowledgeSearchResult) -> str:
        item = result.item
        collection = cls._collection_name(item) or "unknown_collection"
        body = (getattr(item, "body", "") or "").strip()
        if len(body) > 700:
            body = f"{body[:700]}..."
        return f"[{collection}] {getattr(item, 'title', 'Unknown')}\n{body}"

    @classmethod
    def _context_payload(
        cls,
        *,
        task_type: str | AITaskType,
        query: str | None,
        country: str | None,
        channel: str | None,
        language: str | None,
        results: list[KnowledgeSearchResult],
        fallback_notes: list[str] | None = None,
    ) -> dict:
        refs = [cls._item_ref(result) for result in results]
        return {
            "task_type": cls.normalize_task_type(task_type).value,
            "context_status": "ready" if refs else "empty_context",
            "query": query,
            "country": country,
            "channel": channel,
            "language": language,
            "knowledge_item_refs": refs,
            "context_text": "\n\n".join(cls._context_line(result) for result in results),
            "fallback_notes": fallback_notes or [],
            "hard_rule_boundary": cls.HARD_RULE_BOUNDARY,
        }

    @classmethod
    def build_context_from_items(
        cls,
        items: list,
        *,
        task_type: str | AITaskType,
        query: str | None = None,
        country: str | None = None,
        channel: str | None = None,
        language: str | None = None,
        limit_per_collection: int = 3,
    ) -> dict:
        results: list[KnowledgeSearchResult] = []
        for collection in cls.collections_for_task(task_type):
            results.extend(
                KnowledgeSearchService.keyword_fallback_search(
                    items,
                    collection=collection,
                    country=country,
                    language=language,
                    channel=channel,
                    query=query,
                    limit=limit_per_collection,
                )
            )
        return cls._context_payload(
            task_type=task_type,
            query=query,
            country=country,
            channel=channel,
            language=language,
            results=cls._dedupe_results(results),
        )

    @staticmethod
    def _dedupe_results(results: list[KnowledgeSearchResult]) -> list[KnowledgeSearchResult]:
        deduped: list[KnowledgeSearchResult] = []
        seen: set[str] = set()
        for result in results:
            key = str(getattr(result.item, "id", "")) or f"{getattr(result.item, 'title', '')}:{getattr(result.item, 'source_ref', '')}"
            if key in seen:
                continue
            seen.add(key)
            deduped.append(result)
        return deduped

    def build_context(
        self,
        *,
        task_type: str | AITaskType,
        query: str | None = None,
        country: str | None = None,
        channel: str | None = None,
        language: str | None = "zh",
        query_embedding: list[float] | None = None,
        limit_per_collection: int = 3,
    ) -> dict:
        results: list[KnowledgeSearchResult] = []
        fallback_notes: list[str] = []
        for collection in self.collections_for_task(task_type):
            collection_results, mode = self.search_service.search(
                collection=collection,
                country=country,
                language=language,
                channel=channel,
                query=query,
                query_embedding=query_embedding,
                allow_keyword_fallback=True,
                limit=limit_per_collection,
            )
            results.extend(collection_results)
            if mode.get("fallback_reason"):
                fallback_notes.append(f"{collection}: {mode['fallback_reason']}")

        return self._context_payload(
            task_type=task_type,
            query=query,
            country=country,
            channel=channel,
            language=language,
            results=self._dedupe_results(results),
            fallback_notes=fallback_notes,
        )

    def safe_build_context(self, **kwargs) -> dict:
        try:
            return self.build_context(**kwargs)
        except Exception as exc:  # noqa: BLE001 - RAG must not block base extraction/grading.
            return {
                "task_type": self.normalize_task_type(kwargs["task_type"]).value,
                "context_status": "empty_context",
                "query": kwargs.get("query"),
                "country": kwargs.get("country"),
                "channel": kwargs.get("channel"),
                "language": kwargs.get("language", "zh"),
                "knowledge_item_refs": [],
                "context_text": "",
                "fallback_notes": [f"rag_context_error: {exc}"],
                "hard_rule_boundary": self.HARD_RULE_BOUNDARY,
            }
