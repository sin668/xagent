import asyncio

import pytest
from fastapi.testclient import TestClient

from app.db.session import AsyncSessionLocal
from app.main import app
from app.models.knowledge import KnowledgeCollection, KnowledgeItem
from app.services.knowledge import KnowledgeService
from app.services.knowledge_search import KnowledgeSearchService


client = TestClient(app)


def cleanup_phase5_knowledge_records(marker: str = "phase5_knowledge_business_") -> None:
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
def cleanup_phase5_knowledge_business_records():
    cleanup_phase5_knowledge_records()
    yield
    cleanup_phase5_knowledge_records()


def create_collection() -> str:
    response = client.post(
        "/knowledge/collections",
        json={
            "name": "phase5_knowledge_business_collection",
            "description": "第五阶段邮件回复知识库",
            "status": "active",
            "review_status": "approved",
            "version": "v1",
        },
    )
    assert response.status_code == 200
    return response.json()["id"]


def test_phase5_knowledge_item_supports_business_fields_and_allowed_content_types() -> None:
    collection_id = create_collection()

    response = client.post(
        "/knowledge/items",
        json={
            "collection_id": collection_id,
            "title": "phase5_knowledge_business_email_template",
            "body": "低风险白名单客户首次邮件回复模板。",
            "language": "ru",
            "country": "Russia",
            "applicable_channels": ["email"],
            "status": "active",
            "review_status": "approved",
            "version": "v1",
            "content_type": "email_reply_template",
            "business_scene": "first_outreach",
            "risk_level": "Low",
            "auto_reply_allowed": True,
            "market": "ru",
            "tone": "professional",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["content_type"] == "email_reply_template"
    assert body["business_scene"] == "first_outreach"
    assert body["risk_level"] == "Low"
    assert body["auto_reply_allowed"] is True
    assert body["market"] == "ru"
    assert body["tone"] == "professional"


def test_phase5_knowledge_item_rejects_unknown_content_type() -> None:
    collection_id = create_collection()

    response = client.post(
        "/knowledge/items",
        json={
            "collection_id": collection_id,
            "title": "phase5_knowledge_business_unknown_type",
            "body": "未知类型不应进入第五阶段知识库。",
            "content_type": "random_note",
        },
    )

    assert response.status_code == 422


def test_phase5_knowledge_search_filters_business_fields_and_excludes_blocked_auto_reply_candidates() -> None:
    collection_id = create_collection()

    async def seed_items() -> None:
        async with AsyncSessionLocal() as async_session:
            def run(sync_session):
                service = KnowledgeService(sync_session)
                service.create_item(
                    collection_id=collection_id,
                    title="phase5_knowledge_business_allowed",
                    body="white list first email logistics price",
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
                service.create_item(
                    collection_id=collection_id,
                    title="phase5_knowledge_business_blocked",
                    body="white list first email logistics price",
                    language="ru",
                    country="Russia",
                    applicable_channels=["email"],
                    status="active",
                    review_status="approved",
                    content_type="compliance_phrase",
                    business_scene="first_outreach",
                    risk_level="blocked",
                    auto_reply_allowed=True,
                    market="ru",
                    tone="professional",
                )
                service.create_item(
                    collection_id=collection_id,
                    title="phase5_knowledge_business_manual_only",
                    body="white list first email logistics price",
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
                sync_session.commit()

            await async_session.run_sync(run)

    asyncio.run(seed_items())

    response = client.post(
        "/knowledge/search",
        json={
            "query": "logistics price",
            "language": "ru",
            "channel": "email",
            "content_type": "email_reply_template",
            "business_scene": "first_outreach",
            "risk_level": "Low",
            "auto_reply_only": True,
            "market": "ru",
            "tone": "professional",
            "limit": 10,
        },
    )

    assert response.status_code == 200
    titles = [result["item"]["title"] for result in response.json()["items"]]
    assert titles == ["phase5_knowledge_business_allowed"]


def test_phase5_knowledge_service_declares_supported_content_types() -> None:
    assert KnowledgeService.SUPPORTED_CONTENT_TYPES == {
        "qa_entry",
        "email_reply_template",
        "compliance_phrase",
        "vehicle_product_note",
        "process_sop",
    }
    assert KnowledgeSearchService.BLOCKED_RISK_LEVELS == {"blocked", "Forbidden", "High"}
