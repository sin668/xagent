import asyncio

import pytest
from fastapi.testclient import TestClient

from app.db.session import AsyncSessionLocal
from app.main import app
from app.models.enums import KnowledgeEmbeddingStatus
from app.models.knowledge import KnowledgeCollection, KnowledgeEmbedding, KnowledgeItem
from app.services.knowledge import KnowledgeService


client = TestClient(app)
MARKER = "phase5_embedding_stale_"
TEST_EMBEDDING = [0.03] * 1536


def cleanup_phase5_embedding_stale_records() -> None:
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
def cleanup_phase5_embedding_stale_records_fixture():
    cleanup_phase5_embedding_stale_records()
    yield
    cleanup_phase5_embedding_stale_records()


def seed_active_knowledge_with_ready_embedding() -> dict[str, str]:
    result: dict[str, str] = {}

    async def seed() -> None:
        async with AsyncSessionLocal() as async_session:
            def run(sync_session):
                service = KnowledgeService(sync_session)
                collection = service.create_collection(
                    name=f"{MARKER}collection",
                    description="第五阶段 stale embedding 测试集合",
                    status="active",
                    review_status="approved",
                )
                item = service.create_item(
                    collection_id=collection.id,
                    title=f"{MARKER}active_v1",
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
                result["item_id"] = str(item.id)

            await async_session.run_sync(run)

    asyncio.run(seed())
    return result


def test_phase5_editing_active_knowledge_marks_old_embedding_stale_and_excludes_it_from_default_retrieval() -> None:
    seeded = seed_active_knowledge_with_ready_embedding()

    draft_response = client.patch(
        f"/knowledge/items/{seeded['item_id']}",
        json={
            "body": "更新后的邮件模板，需要重新生成 embedding",
            "version": "v2-draft",
            "change_reason": "邮件回复知识更新",
        },
    )
    old_detail = client.get(f"/knowledge/items/{seeded['item_id']}")
    retrieval = client.post(
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

    assert draft_response.status_code == 200
    draft = draft_response.json()
    assert draft["id"] != seeded["item_id"]
    assert draft["metadata_json"]["parent_item_id"] == seeded["item_id"]
    assert draft["metadata_json"]["embedding_stale"] is True
    assert draft["metadata_json"]["stale_reason"] == "new_version_pending_embedding"

    assert old_detail.status_code == 200
    old_metadata = old_detail.json()["metadata_json"]
    assert old_metadata["embedding_stale"] is True
    assert old_metadata["stale_reason"] == "new_version_created"
    assert old_metadata["replacement_item_id"] == draft["id"]

    assert retrieval.status_code == 200
    assert retrieval.json()["items"] == []
    assert retrieval.json()["rejection_reason"] == "缺少同语言 embedding_ready 知识，不能自动发送。"
