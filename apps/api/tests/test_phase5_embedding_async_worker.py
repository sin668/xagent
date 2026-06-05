import asyncio
from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

from app.api import knowledge as knowledge_api
from app.db.session import AsyncSessionLocal
from app.main import app
from app.models.enums import KnowledgeEmbeddingStatus
from app.models.knowledge import KnowledgeCollection, KnowledgeEmbedding, KnowledgeItem


client = TestClient(app)
MARKER = "phase5_embedding_async_worker_"


class FakeEmbeddingProvider:
    model = "phase5-test-embedding"
    dimensions = 1536

    def embed_text(self, text: str) -> list[float]:
        assert "first email" in text
        return [0.02] * self.dimensions


class FailingEmbeddingProvider:
    model = "phase5-failing-embedding"
    dimensions = 1536

    def embed_text(self, text: str) -> list[float]:
        raise RuntimeError("provider timeout")


def cleanup_phase5_embedding_worker_records() -> None:
    async def run_cleanup() -> None:
        async with AsyncSessionLocal() as async_session:
            def run(sync_session):
                collections = sync_session.query(KnowledgeCollection).filter(
                    KnowledgeCollection.name.like(f"{MARKER}%")
                ).all()
                for collection in collections:
                    sync_session.delete(collection)
                sync_session.commit()

            await async_session.run_sync(run)

    asyncio.run(run_cleanup())


@pytest.fixture(autouse=True)
def cleanup_phase5_embedding_worker_records_fixture(monkeypatch):
    cleanup_phase5_embedding_worker_records()
    monkeypatch.setattr(knowledge_api, "create_embedding_provider", lambda: FakeEmbeddingProvider())
    yield
    cleanup_phase5_embedding_worker_records()


def create_draft_item() -> dict:
    collection = client.post(
        "/knowledge/collections",
        json={
            "name": f"{MARKER}collection",
            "description": "第五阶段 embedding worker 测试集合",
            "status": "active",
            "review_status": "approved",
        },
    )
    assert collection.status_code == 200
    response = client.post(
        "/knowledge/items",
        json={
            "collection_id": collection.json()["id"],
            "title": f"{MARKER}item",
            "body": "white list first email logistics cooperation process",
            "language": "ru",
            "status": "draft",
            "review_status": "pending",
            "content_type": "email_reply_template",
            "business_scene": "first_outreach",
            "risk_level": "Low",
            "auto_reply_allowed": True,
        },
    )
    assert response.status_code == 200
    return response.json()


def list_item_embeddings(item_id: str) -> list[dict]:
    async def run_query() -> list[dict]:
        async with AsyncSessionLocal() as async_session:
            def run(sync_session):
                records = (
                    sync_session.query(KnowledgeEmbedding)
                    .filter(KnowledgeEmbedding.item_id == item_id)
                    .order_by(KnowledgeEmbedding.created_at.asc())
                    .all()
                )
                return [
                    {
                        "id": str(record.id),
                        "status": record.embedding_status.value,
                        "model": record.embedding_model,
                        "dimensions": record.embedding_dimensions,
                        "has_embedding": record.embedding is not None,
                        "error_message": record.error_message,
                    }
                    for record in records
                ]

            return await async_session.run_sync(run)

    return asyncio.run(run_query())


def test_phase5_publish_enqueues_pending_embedding_and_worker_marks_ready(monkeypatch) -> None:
    started_tasks: list[Callable[[], None]] = []

    def fake_start(*, name: str, target: Callable[[], None]):
        assert name.startswith("knowledge-embedding-worker-")
        started_tasks.append(target)
        return object()

    monkeypatch.setattr(knowledge_api.AgentThreadRunner, "start", fake_start)
    item = create_draft_item()

    publish = client.post(
        f"/knowledge/items/{item['id']}/publish",
        json={"actor": "知识管理员", "actor_role": "knowledge_admin", "review_note": "审核通过"},
    )

    assert publish.status_code == 200
    assert publish.json()["metadata_json"]["workflow_state"] == "pending_embedding"
    assert len(started_tasks) == 1
    pending_records = list_item_embeddings(item["id"])
    assert pending_records == [
        {
            "id": pending_records[0]["id"],
            "status": KnowledgeEmbeddingStatus.PENDING.value,
            "model": "phase5-test-embedding",
            "dimensions": 1536,
            "has_embedding": False,
            "error_message": None,
        }
    ]

    started_tasks[0]()

    ready_records = list_item_embeddings(item["id"])
    assert ready_records[0]["status"] == KnowledgeEmbeddingStatus.READY.value
    assert ready_records[0]["model"] == "phase5-test-embedding"
    assert ready_records[0]["dimensions"] == 1536
    assert ready_records[0]["has_embedding"] is True
    assert ready_records[0]["error_message"] is None


def test_phase5_embedding_provider_failure_does_not_break_publish_api(monkeypatch) -> None:
    started_tasks: list[Callable[[], None]] = []

    def fake_start(*, name: str, target: Callable[[], None]):
        started_tasks.append(target)
        return object()

    monkeypatch.setattr(knowledge_api.AgentThreadRunner, "start", fake_start)
    monkeypatch.setattr(knowledge_api, "create_embedding_provider", lambda: FailingEmbeddingProvider())
    item = create_draft_item()

    publish = client.post(
        f"/knowledge/items/{item['id']}/publish",
        json={"actor": "知识管理员", "actor_role": "knowledge_admin", "review_note": "审核通过"},
    )
    started_tasks[0]()

    assert publish.status_code == 200
    assert publish.json()["metadata_json"]["workflow_state"] == "pending_embedding"
    failed_records = list_item_embeddings(item["id"])
    assert failed_records[0]["status"] == KnowledgeEmbeddingStatus.FAILED.value
    assert failed_records[0]["model"] == "phase5-failing-embedding"
    assert "provider timeout" in failed_records[0]["error_message"]
