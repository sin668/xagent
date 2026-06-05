import asyncio

import pytest
from fastapi.testclient import TestClient

from app.db.session import AsyncSessionLocal
from app.main import app
from app.models.enums import KnowledgeEmbeddingStatus
from app.models.knowledge import KnowledgeCollection, KnowledgeEmbedding
from app.services.knowledge import KnowledgeService


client = TestClient(app)
MARKER = "phase5_rag_test_"
TEST_EMBEDDING = [0.04] * 1536


def cleanup_phase5_rag_test_records() -> None:
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
def cleanup_phase5_rag_test_records_fixture():
    cleanup_phase5_rag_test_records()
    yield
    cleanup_phase5_rag_test_records()


def seed_rag_test_knowledge() -> dict[str, str]:
    result: dict[str, str] = {}

    async def seed() -> None:
        async with AsyncSessionLocal() as async_session:
            def run(sync_session):
                service = KnowledgeService(sync_session)
                collection = service.create_collection(
                    name=f"{MARKER}collection",
                    description="第五阶段后台 RAG 召回测试集合",
                    status="active",
                    review_status="approved",
                )
                ready = service.create_item(
                    collection_id=collection.id,
                    title=f"{MARKER}ready_template",
                    body="white list first email logistics cooperation process",
                    language="ru",
                    country="Russia",
                    applicable_channels=["email"],
                    status="active",
                    review_status="approved",
                    content_type="email_reply_template",
                    business_scene="first_outreach",
                    risk_level="Low",
                    auto_reply_allowed=True,
                    market="ru",
                    tone="professional",
                    version="v1",
                )
                blocked = service.create_item(
                    collection_id=collection.id,
                    title=f"{MARKER}blocked_template",
                    body="white list first email logistics cooperation process",
                    language="ru",
                    country="Russia",
                    applicable_channels=["email"],
                    status="active",
                    review_status="approved",
                    content_type="email_reply_template",
                    business_scene="first_outreach",
                    risk_level="blocked",
                    auto_reply_allowed=True,
                    market="ru",
                    tone="professional",
                )
                for item in (ready, blocked):
                    sync_session.add(
                        KnowledgeEmbedding(
                            item_id=item.id,
                            embedding_model="test-embedding",
                            embedding=TEST_EMBEDDING,
                            embedding_dimensions=1536,
                            embedding_status=KnowledgeEmbeddingStatus.READY,
                        )
                    )
                sync_session.commit()
                result["ready_id"] = str(ready.id)

            await async_session.run_sync(run)

    asyncio.run(seed())
    return result


def test_phase5_rag_retrieval_test_api_returns_hits_filters_and_dry_run_flag() -> None:
    seeded = seed_rag_test_knowledge()

    response = client.post(
        "/knowledge/rag-test",
        json={
            "query": "logistics cooperation",
            "language": "ru",
            "channel": "email",
            "content_type": "email_reply_template",
            "business_scene": "first_outreach",
            "auto_send_context": True,
            "market": "ru",
            "limit": 10,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["dry_run"] is True
    assert body["triggered_send"] is False
    assert body["rejection_reason"] is None
    assert body["total"] == 1
    assert body["filter_conditions"] == {
        "language": "ru",
        "channel": "email",
        "content_types": ["email_reply_template"],
        "business_scene": "first_outreach",
        "auto_send_candidate": True,
        "market": "ru",
    }
    assert body["items"][0]["knowledge_item_id"] == seeded["ready_id"]
    assert body["items"][0]["title"] == f"{MARKER}ready_template"
    assert body["items"][0]["similarity_score"] > 0


def test_phase5_rag_retrieval_test_api_reports_miss_reason_without_sending() -> None:
    seed_rag_test_knowledge()

    response = client.post(
        "/knowledge/rag-test",
        json={
            "query": "logistics cooperation",
            "language": "ja",
            "channel": "email",
            "content_type": "email_reply_template",
            "business_scene": "first_outreach",
            "auto_send_context": True,
            "market": "ru",
            "limit": 10,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["dry_run"] is True
    assert body["triggered_send"] is False
    assert body["items"] == []
    assert body["total"] == 0
    assert body["rejection_reason"] == "缺少同语言 embedding_ready 知识，不能自动发送。"
