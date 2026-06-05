from __future__ import annotations

from collections import Counter

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.enums import KnowledgeEmbeddingStatus, KnowledgeItemStatus, KnowledgeReviewStatus
from app.models.knowledge import KnowledgeEmbedding, KnowledgeItem


class KnowledgeEmbeddingMetricsService:
    GO_NO_GO_READY_RATE_THRESHOLD = 0.8

    def __init__(self, session: Session) -> None:
        self.session = session

    def metrics(self) -> dict:
        published_items = list(
            self.session.scalars(
                select(KnowledgeItem)
                .options(selectinload(KnowledgeItem.embeddings))
                .where(KnowledgeItem.status == KnowledgeItemStatus.ACTIVE)
                .where(KnowledgeItem.review_status == KnowledgeReviewStatus.APPROVED)
            ).all()
        )
        embeddings = [embedding for item in published_items for embedding in item.embeddings]
        ready_count = sum(1 for embedding in embeddings if embedding.embedding_status == KnowledgeEmbeddingStatus.READY)
        pending_count = sum(1 for embedding in embeddings if embedding.embedding_status == KnowledgeEmbeddingStatus.PENDING)
        failed_count = sum(1 for embedding in embeddings if embedding.embedding_status == KnowledgeEmbeddingStatus.FAILED)
        published_knowledge_count = len(published_items)
        ready_rate = ready_count / published_knowledge_count if published_knowledge_count else 0.0
        total_retry_count = sum(int(embedding.retry_count or 0) for embedding in embeddings)
        failure_reason_counter = Counter(
            reason
            for embedding in embeddings
            if (reason := (embedding.last_error_message or embedding.error_message))
        )
        failed_cases = [
            self._failed_case_payload(embedding)
            for embedding in sorted(embeddings, key=lambda item: item.created_at, reverse=True)
            if embedding.last_error_message or embedding.error_message
        ]
        return {
            "published_knowledge_count": published_knowledge_count,
            "embedding_task_count": len(embeddings),
            "ready_count": ready_count,
            "pending_count": pending_count,
            "failed_count": failed_count,
            "ready_rate": ready_rate,
            "total_retry_count": total_retry_count,
            "go_no_go_ready": ready_rate >= self.GO_NO_GO_READY_RATE_THRESHOLD,
            "failure_reason_groups": [
                {"reason": reason, "count": count}
                for reason, count in sorted(failure_reason_counter.items(), key=lambda item: (-item[1], item[0]))
            ],
            "failed_cases": failed_cases,
        }

    def _failed_case_payload(self, embedding: KnowledgeEmbedding) -> dict:
        return {
            "embedding_id": embedding.id,
            "knowledge_title": embedding.item.title,
            "embedding_model": embedding.embedding_model,
            "error_message": embedding.last_error_message or embedding.error_message or "",
            "retry_count": int(embedding.retry_count or 0),
        }
