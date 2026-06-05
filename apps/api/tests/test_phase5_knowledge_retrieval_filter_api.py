import asyncio

import pytest
from fastapi.testclient import TestClient

from app.db.session import AsyncSessionLocal
from app.main import app
from app.models.knowledge import KnowledgeCollection, KnowledgeEmbedding, KnowledgeItem
from app.models.enums import KnowledgeEmbeddingStatus
from app.services.knowledge import KnowledgeService


client = TestClient(app)
TEST_EMBEDDING = [0.01] * 1536


def cleanup_phase5_knowledge_retrieval_records(marker: str = "phase5_knowledge_retrieval_") -> None:
    async def run_cleanup() -> None:
        async with AsyncSessionLocal() as async_session:
            def run(sync_session):
                collections = sync_session.query(KnowledgeCollection).filter(
                    KnowledgeCollection.name.like(f"{marker}%")
                ).all()
                for collection in collections:
                    sync_session.delete(collection)
                sync_session.commit()

            await async_session.run_sync(run)

    asyncio.run(run_cleanup())


@pytest.fixture(autouse=True)
def cleanup_phase5_knowledge_retrieval_api_records():
    cleanup_phase5_knowledge_retrieval_records()
    yield
    cleanup_phase5_knowledge_retrieval_records()


def seed_retrieval_knowledge() -> dict[str, str]:
    result: dict[str, str] = {}

    async def seed() -> None:
        async with AsyncSessionLocal() as async_session:
            def run(sync_session):
                service = KnowledgeService(sync_session)
                collection = service.create_collection(
                    name="phase5_knowledge_retrieval_collection",
                    description="第五阶段 EMAIL_REPLY 召回过滤测试集合",
                    status="active",
                    review_status="approved",
                )
                ready = service.create_item(
                    collection_id=collection.id,
                    title="phase5_knowledge_retrieval_ready_ru",
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
                    version="v2",
                )
                pending_embedding = service.create_item(
                    collection_id=collection.id,
                    title="phase5_knowledge_retrieval_pending_embedding",
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
                )
                manual_only = service.create_item(
                    collection_id=collection.id,
                    title="phase5_knowledge_retrieval_manual_only",
                    body="white list first email logistics cooperation process",
                    language="ru",
                    country="Russia",
                    applicable_channels=["email"],
                    status="active",
                    review_status="approved",
                    content_type="email_reply_template",
                    business_scene="first_outreach",
                    risk_level="Low",
                    auto_reply_allowed=False,
                    market="ru",
                    tone="professional",
                )
                blocked = service.create_item(
                    collection_id=collection.id,
                    title="phase5_knowledge_retrieval_blocked",
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
                other_language = service.create_item(
                    collection_id=collection.id,
                    title="phase5_knowledge_retrieval_ready_en",
                    body="white list first email logistics cooperation process",
                    language="en",
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
                )
                for item, status in [
                    (ready, KnowledgeEmbeddingStatus.READY),
                    (manual_only, KnowledgeEmbeddingStatus.READY),
                    (blocked, KnowledgeEmbeddingStatus.READY),
                    (other_language, KnowledgeEmbeddingStatus.READY),
                    (pending_embedding, KnowledgeEmbeddingStatus.PENDING),
                ]:
                    sync_session.add(
                        KnowledgeEmbedding(
                            item_id=item.id,
                            embedding_model="test-embedding",
                            embedding=TEST_EMBEDDING,
                            embedding_dimensions=1536,
                            embedding_status=status,
                        )
                    )
                sync_session.commit()
                result["ready_id"] = str(ready.id)

            await async_session.run_sync(run)

    asyncio.run(seed())
    return result


def test_phase5_retrieval_filter_returns_only_auto_reply_ready_same_language_knowledge() -> None:
    ids = seed_retrieval_knowledge()

    response = client.post(
        "/knowledge/retrieval-filter",
        json={
            "query": "logistics cooperation",
            "language": "ru",
            "channel": "email",
            "content_types": ["email_reply_template"],
            "business_scene": "first_outreach",
            "auto_send_candidate": True,
            "market": "ru",
            "limit": 10,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["rejection_reason"] is None
    assert body["total"] == 1
    assert [item["knowledge_item_id"] for item in body["items"]] == [ids["ready_id"]]
    result = body["items"][0]
    assert result["version"] == "v2"
    assert result["similarity_score"] > 0
    assert result["filter_conditions"] == {
        "language": "ru",
        "channel": "email",
        "content_types": ["email_reply_template"],
        "business_scene": "first_outreach",
        "auto_send_candidate": True,
        "market": "ru",
    }


def test_phase5_retrieval_filter_reports_missing_same_language_embedding_ready_knowledge() -> None:
    seed_retrieval_knowledge()

    response = client.post(
        "/knowledge/retrieval-filter",
        json={
            "query": "logistics cooperation",
            "language": "ja",
            "channel": "email",
            "content_types": ["email_reply_template"],
            "business_scene": "first_outreach",
            "auto_send_candidate": True,
            "market": "ru",
            "limit": 10,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["total"] == 0
    assert body["rejection_reason"] == "缺少同语言 embedding_ready 知识，不能自动发送。"
