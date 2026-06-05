import asyncio

import pytest
from fastapi.testclient import TestClient

from app.db.session import AsyncSessionLocal
from app.main import app
from app.models.knowledge import KnowledgeCollection, KnowledgeItem


client = TestClient(app)


def cleanup_phase5_knowledge_crud_records(marker: str = "phase5_knowledge_crud_") -> None:
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
def cleanup_phase5_knowledge_crud_api_records():
    cleanup_phase5_knowledge_crud_records()
    yield
    cleanup_phase5_knowledge_crud_records()


def create_collection(name: str = "phase5_knowledge_crud_collection") -> str:
    response = client.post(
        "/knowledge/collections",
        json={
            "name": name,
            "description": "第五阶段后台知识库 CRUD 测试集合",
            "status": "active",
            "review_status": "approved",
            "version": "v1",
        },
    )
    assert response.status_code == 200
    return response.json()["id"]


def create_item(collection_id: str, title: str, **overrides) -> dict:
    payload = {
        "collection_id": collection_id,
        "title": title,
        "body": f"{title} body",
        "language": "ru",
        "country": "Russia",
        "applicable_channels": ["email"],
        "status": "draft",
        "review_status": "pending",
        "version": "v1",
        "content_type": "qa_entry",
        "business_scene": "first_outreach",
        "risk_level": "Low",
        "auto_reply_allowed": False,
        "market": "ru",
        "tone": "professional",
    }
    payload.update(overrides)
    response = client.post("/knowledge/items", json=payload)
    assert response.status_code == 200
    return response.json()


def test_phase5_knowledge_crud_lists_items_by_business_filters_and_status() -> None:
    collection_id = create_collection()
    create_item(
        collection_id,
        "phase5_knowledge_crud_ru_template",
        status="active",
        review_status="approved",
        content_type="email_reply_template",
        business_scene="first_outreach",
        risk_level="Low",
        auto_reply_allowed=True,
        tone="friendly",
    )
    create_item(
        collection_id,
        "phase5_knowledge_crud_zh_template",
        language="zh",
        status="active",
        review_status="approved",
        content_type="email_reply_template",
        business_scene="first_outreach",
        risk_level="Low",
        auto_reply_allowed=True,
        tone="friendly",
    )
    create_item(
        collection_id,
        "phase5_knowledge_crud_ru_compliance",
        status="active",
        review_status="approved",
        content_type="compliance_phrase",
        business_scene="compliance_review",
        risk_level="Medium",
        auto_reply_allowed=False,
    )

    response = client.get(
        "/knowledge/items",
        params={
            "content_type": "email_reply_template",
            "language": "ru",
            "business_scene": "first_outreach",
            "risk_level": "Low",
            "status": "active",
            "review_status": "approved",
            "auto_reply_allowed": True,
            "market": "ru",
            "tone": "friendly",
        },
    )

    assert response.status_code == 200
    titles = [item["title"] for item in response.json()["items"]]
    assert titles == ["phase5_knowledge_crud_ru_template"]


def test_phase5_knowledge_crud_detail_and_draft_update() -> None:
    collection_id = create_collection()
    item = create_item(collection_id, "phase5_knowledge_crud_detail")

    detail = client.get(f"/knowledge/items/{item['id']}")
    update = client.patch(
        f"/knowledge/items/{item['id']}",
        json={
            "title": "phase5_knowledge_crud_detail_updated",
            "body": "更新后的草稿内容",
            "content_type": "process_sop",
            "business_scene": "after_sales_followup",
            "risk_level": "Medium",
            "auto_reply_allowed": False,
            "tone": "formal",
        },
    )

    assert detail.status_code == 200
    assert detail.json()["id"] == item["id"]
    assert update.status_code == 200
    updated = update.json()
    assert updated["id"] == item["id"]
    assert updated["title"] == "phase5_knowledge_crud_detail_updated"
    assert updated["content_type"] == "process_sop"
    assert updated["business_scene"] == "after_sales_followup"
    assert updated["risk_level"] == "Medium"
    assert updated["tone"] == "formal"


def test_phase5_knowledge_crud_editing_published_item_creates_new_draft_version() -> None:
    collection_id = create_collection()
    active_item = create_item(
        collection_id,
        "phase5_knowledge_crud_active_template",
        status="active",
        review_status="approved",
        version="v1",
        content_type="email_reply_template",
        auto_reply_allowed=True,
    )

    response = client.patch(
        f"/knowledge/items/{active_item['id']}",
        json={
            "body": "基于已发布模板生成的新草稿版本",
            "version": "v2-draft",
            "change_reason": "运营调整邮件回复模板",
        },
    )

    assert response.status_code == 200
    draft = response.json()
    assert draft["id"] != active_item["id"]
    assert draft["status"] == "draft"
    assert draft["review_status"] == "pending"
    assert draft["version"] == "v2-draft"
    assert draft["body"] == "基于已发布模板生成的新草稿版本"
    assert draft["metadata_json"]["parent_item_id"] == active_item["id"]
    assert draft["metadata_json"]["change_reason"] == "运营调整邮件回复模板"

    old_detail = client.get(f"/knowledge/items/{active_item['id']}").json()
    assert old_detail["status"] == "active"
    assert old_detail["review_status"] == "approved"


def test_phase5_knowledge_crud_draft_content_is_not_production_rag_candidate() -> None:
    collection_id = create_collection()
    create_item(
        collection_id,
        "phase5_knowledge_crud_draft_not_rag",
        body="logistics price reply template",
        status="draft",
        review_status="pending",
        content_type="email_reply_template",
        auto_reply_allowed=True,
    )

    response = client.post(
        "/knowledge/search",
        json={
            "query": "logistics price",
            "content_type": "email_reply_template",
            "auto_reply_only": True,
            "limit": 10,
        },
    )

    assert response.status_code == 200
    assert response.json()["items"] == []
