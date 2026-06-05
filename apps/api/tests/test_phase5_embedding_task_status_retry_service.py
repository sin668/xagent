import asyncio

import pytest
from fastapi.testclient import TestClient

from app.db.session import AsyncSessionLocal
from app.main import app
from app.models.knowledge import KnowledgeCollection
from app.services.knowledge import KnowledgeService


client = TestClient(app)
MARKER = "phase5_embedding_task_status_"


def cleanup_phase5_embedding_task_records() -> None:
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
def cleanup_phase5_embedding_task_status_records():
    cleanup_phase5_embedding_task_records()
    yield
    cleanup_phase5_embedding_task_records()


def create_knowledge_item() -> str:
    response = client.post(
        "/knowledge/collections",
        json={
            "name": f"{MARKER}collection",
            "description": "第五阶段 embedding 状态重试测试集合",
            "status": "active",
            "review_status": "approved",
        },
    )
    assert response.status_code == 200
    collection_id = response.json()["id"]

    item = client.post(
        "/knowledge/items",
        json={
            "collection_id": collection_id,
            "title": f"{MARKER}item",
            "body": "white list first email logistics cooperation process",
            "language": "ru",
            "status": "active",
            "review_status": "approved",
            "content_type": "email_reply_template",
            "business_scene": "first_outreach",
            "risk_level": "Low",
            "auto_reply_allowed": True,
        },
    )
    assert item.status_code == 200
    return item.json()["id"]


def test_phase5_embedding_task_can_be_created_pending_then_failed_and_retried() -> None:
    item_id = create_knowledge_item()

    pending = client.post(
        f"/knowledge/items/{item_id}/embedding",
        json={
            "embedding_model": "test-embedding",
            "embedding": None,
            "embedding_dimensions": 1536,
        },
    )
    failed = client.post(
        f"/knowledge/items/{item_id}/embedding",
        json={
            "embedding_model": "test-embedding",
            "embedding": None,
            "embedding_dimensions": 1536,
            "error_message": "embedding provider timeout",
        },
    )

    assert pending.status_code == 200
    assert pending.json()["embedding_status"] == "pending"
    assert pending.json()["error_message"] is None

    assert failed.status_code == 200
    assert failed.json()["embedding_status"] == "failed"
    assert failed.json()["error_message"] == "embedding provider timeout"

    retry = client.post(f"/knowledge/embeddings/{failed.json()['id']}/retry")
    assert retry.status_code == 200
    assert retry.json()["embedding_status"] == "pending"
    assert retry.json()["error_message"] is None


def test_phase5_embedding_retry_rejects_ready_task() -> None:
    item_id = create_knowledge_item()
    ready = client.post(
        f"/knowledge/items/{item_id}/embedding",
        json={
            "embedding_model": "test-embedding",
            "embedding": [0.01] * 1536,
            "embedding_dimensions": 1536,
        },
    )
    assert ready.status_code == 200
    assert ready.json()["embedding_status"] == "ready"

    retry = client.post(f"/knowledge/embeddings/{ready.json()['id']}/retry")

    assert retry.status_code == 409
    assert retry.json()["detail"] == "只有 failed 状态的 embedding 任务可以重试。"
