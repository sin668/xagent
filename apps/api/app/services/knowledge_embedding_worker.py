from __future__ import annotations

import asyncio
import logging
from uuid import UUID

from app.db.session import AsyncSessionLocal
from app.models.knowledge import KnowledgeEmbedding
from app.services.embedding_provider import EmbeddingProvider
from app.services.knowledge import KnowledgeService


logger = logging.getLogger("uvicorn.error")


class KnowledgeEmbeddingWorker:
    def __init__(self, provider: EmbeddingProvider) -> None:
        self.provider = provider

    def run_once(self, embedding_id: UUID) -> None:
        asyncio.run(self._run_once(embedding_id))

    async def _run_once(self, embedding_id: UUID) -> None:
        async with AsyncSessionLocal() as async_session:
            def run(sync_session):
                service = KnowledgeService(sync_session)
                record = sync_session.get(KnowledgeEmbedding, embedding_id)
                if record is None:
                    logger.warning("知识 embedding worker 跳过：任务不存在 embedding_id=%s", embedding_id)
                    return None
                item = record.item
                text = self._build_embedding_text(item)
                try:
                    embedding = self.provider.embed_text(text)
                    dimensions = len(embedding)
                    expected_dimensions = getattr(self.provider, "dimensions", dimensions)
                    if dimensions != expected_dimensions:
                        raise RuntimeError(
                            f"Embedding dimensions mismatch: expected {expected_dimensions}, got {dimensions}."
                        )
                    service.mark_embedding_ready(
                        embedding_id,
                        embedding=embedding,
                        embedding_model=self.provider.model,
                        embedding_dimensions=dimensions,
                    )
                    sync_session.commit()
                    logger.info(
                        "知识 embedding worker 完成：embedding_id=%s item_id=%s model=%s dimensions=%s",
                        embedding_id,
                        item.id,
                        self.provider.model,
                        dimensions,
                    )
                except Exception as exc:
                    sync_session.rollback()
                    service.mark_embedding_failed(embedding_id, error_message=str(exc))
                    sync_session.commit()
                    logger.exception(
                        "知识 embedding worker 失败：embedding_id=%s item_id=%s error=%s",
                        embedding_id,
                        item.id,
                        exc,
                    )
                return None

            await async_session.run_sync(run)

    def _build_embedding_text(self, item) -> str:
        metadata = item.metadata_json or {}
        parts = [
            item.title,
            item.body,
            f"language={item.language}",
            f"country={item.country or 'Unknown'}",
            f"content_type={metadata.get('content_type') or 'Unknown'}",
            f"business_scene={metadata.get('business_scene') or 'Unknown'}",
            f"risk_level={metadata.get('risk_level') or 'Unknown'}",
            f"market={metadata.get('market') or 'Unknown'}",
            f"tone={metadata.get('tone') or 'Unknown'}",
        ]
        return "\n".join(parts)
