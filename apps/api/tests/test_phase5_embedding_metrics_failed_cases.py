import asyncio

import pytest
from fastapi.testclient import TestClient

from app.db.session import AsyncSessionLocal
from app.main import app
from app.models.enums import KnowledgeEmbeddingStatus
from app.models.knowledge import KnowledgeCollection, KnowledgeEmbedding
from app.services.knowledge import KnowledgeService


client = TestClient(app)
MARKER = "phase5_embedding_metrics_"
TEST_EMBEDDING = [0.05] * 1536


def cleanup_phase5_embedding_metrics_records() -> None:
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
def cleanup_phase5_embedding_metrics_records_fixture():
    cleanup_phase5_embedding_metrics_records()
    yield
    cleanup_phase5_embedding_metrics_records()


def seed_embedding_metrics_data() -> dict[str, str]:
    result: dict[str, str] = {}

    async def seed() -> None:
        async with AsyncSessionLocal() as async_session:
            def run(sync_session):
                service = KnowledgeService(sync_session)
                collection = service.create_collection(
                    name=f"{MARKER}collection",
                    description="第五阶段 embedding 指标测试集合",
                    status="active",
                    review_status="approved",
                )
                ready_item = service.create_item(
                    collection_id=collection.id,
                    title=f"{MARKER}ready",
                    body="ready embedding knowledge",
                    language="ru",
                    status="active",
                    review_status="approved",
                    content_type="email_reply_template",
                    business_scene="first_outreach",
                    risk_level="Low",
                    auto_reply_allowed=True,
                )
                pending_item = service.create_item(
                    collection_id=collection.id,
                    title=f"{MARKER}pending",
                    body="pending embedding knowledge",
                    language="ru",
                    status="active",
                    review_status="approved",
                    content_type="email_reply_template",
                    business_scene="first_outreach",
                    risk_level="Low",
                    auto_reply_allowed=True,
                )
                failed_item = service.create_item(
                    collection_id=collection.id,
                    title=f"{MARKER}failed",
                    body="failed embedding knowledge",
                    language="ru",
                    status="active",
                    review_status="approved",
                    content_type="email_reply_template",
                    business_scene="first_outreach",
                    risk_level="Low",
                    auto_reply_allowed=True,
                )
                sync_session.add_all(
                    [
                        KnowledgeEmbedding(
                            item_id=ready_item.id,
                            embedding_model="test-embedding",
                            embedding=TEST_EMBEDDING,
                            embedding_dimensions=1536,
                            embedding_status=KnowledgeEmbeddingStatus.READY,
                        ),
                        KnowledgeEmbedding(
                            item_id=pending_item.id,
                            embedding_model="test-embedding",
                            embedding=None,
                            embedding_dimensions=1536,
                            embedding_status=KnowledgeEmbeddingStatus.PENDING,
                        ),
                        KnowledgeEmbedding(
                            item_id=failed_item.id,
                            embedding_model="test-embedding",
                            embedding=None,
                            embedding_dimensions=1536,
                            embedding_status=KnowledgeEmbeddingStatus.FAILED,
                            error_message="embedding provider timeout",
                        ),
                    ]
                )
                sync_session.commit()
                failed_embedding = (
                    sync_session.query(KnowledgeEmbedding)
                    .filter(KnowledgeEmbedding.item_id == failed_item.id)
                    .one()
                )
                result["failed_embedding_id"] = str(failed_embedding.id)

            await async_session.run_sync(run)

    asyncio.run(seed())
    return result


def test_phase5_embedding_metrics_reports_ready_rate_failures_and_retry_count() -> None:
    ids = seed_embedding_metrics_data()

    retry = client.post(f"/knowledge/embeddings/{ids['failed_embedding_id']}/retry")
    metrics = client.get("/knowledge/embeddings/metrics")

    assert retry.status_code == 200
    assert retry.json()["embedding_status"] == "pending"
    assert retry.json()["retry_count"] == 1

    assert metrics.status_code == 200
    body = metrics.json()
    assert body["published_knowledge_count"] == 3
    assert body["embedding_task_count"] == 3
    assert body["ready_count"] == 1
    assert body["pending_count"] == 2
    assert body["failed_count"] == 0
    assert body["ready_rate"] == pytest.approx(1 / 3)
    assert body["total_retry_count"] == 1
    assert body["go_no_go_ready"] is False
    assert body["failure_reason_groups"] == [
        {"reason": "embedding provider timeout", "count": 1}
    ]
    assert body["failed_cases"] == [
        {
            "embedding_id": ids["failed_embedding_id"],
            "knowledge_title": f"{MARKER}failed",
            "embedding_model": "test-embedding",
            "error_message": "embedding provider timeout",
            "retry_count": 1,
        }
    ]
