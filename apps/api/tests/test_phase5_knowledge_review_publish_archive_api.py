import asyncio

import pytest
from fastapi.testclient import TestClient

from app.db.session import AsyncSessionLocal
from app.main import app
from app.models.knowledge import KnowledgeCollection, KnowledgeItem
from app.models.review_log import ReviewLog


client = TestClient(app)


def cleanup_phase5_knowledge_review_records(marker: str = "phase5_knowledge_review_") -> None:
    async def run_cleanup() -> None:
        async with AsyncSessionLocal() as async_session:
            def run(sync_session):
                item_ids = [
                    str(item_id)
                    for item_id in sync_session.query(KnowledgeItem.id).filter(
                        KnowledgeItem.title.like(f"{marker}%")
                    )
                ]
                if item_ids:
                    sync_session.query(ReviewLog).filter(ReviewLog.task_id.in_(item_ids)).delete(
                        synchronize_session=False
                    )
                collections = sync_session.query(KnowledgeCollection).filter(
                    KnowledgeCollection.name.like(f"{marker}%")
                ).all()
                for collection in collections:
                    sync_session.delete(collection)
                sync_session.commit()

            await async_session.run_sync(run)

    asyncio.run(run_cleanup())


@pytest.fixture(autouse=True)
def cleanup_phase5_knowledge_review_api_records():
    cleanup_phase5_knowledge_review_records()
    yield
    cleanup_phase5_knowledge_review_records()


def create_collection() -> str:
    response = client.post(
        "/knowledge/collections",
        json={
            "name": "phase5_knowledge_review_collection",
            "description": "第五阶段知识审核发布测试集合",
            "status": "active",
            "review_status": "approved",
        },
    )
    assert response.status_code == 200
    return response.json()["id"]


def create_draft_item(collection_id: str, title: str = "phase5_knowledge_review_draft") -> dict:
    response = client.post(
        "/knowledge/items",
        json={
            "collection_id": collection_id,
            "title": title,
            "body": "white list first email logistics price",
            "language": "ru",
            "country": "Russia",
            "applicable_channels": ["email"],
            "status": "draft",
            "review_status": "pending",
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
    return response.json()


def test_phase5_knowledge_review_publish_activate_flow_writes_audit_and_controls_retrieval() -> None:
    collection_id = create_collection()
    item = create_draft_item(collection_id)

    submit = client.post(
        f"/knowledge/items/{item['id']}/submit-review",
        json={"actor": "运营", "actor_role": "operator", "review_note": "提交审核"},
    )
    publish = client.post(
        f"/knowledge/items/{item['id']}/publish",
        json={"actor": "知识管理员", "actor_role": "knowledge_admin", "review_note": "审核通过"},
    )
    pending_search = client.post(
        "/knowledge/search",
        json={"query": "logistics price", "content_type": "email_reply_template", "auto_reply_only": True},
    )
    activate = client.post(
        f"/knowledge/items/{item['id']}/activate-retrieval",
        json={"actor": "技术管理员", "actor_role": "tech_admin", "review_note": "embedding ready"},
    )
    active_search = client.post(
        "/knowledge/search",
        json={"query": "logistics price", "content_type": "email_reply_template", "auto_reply_only": True},
    )
    audit = client.get(f"/knowledge/items/{item['id']}/review-logs")

    assert submit.status_code == 200
    assert submit.json()["status"] == "draft"
    assert submit.json()["review_status"] == "approved"
    assert submit.json()["metadata_json"]["workflow_state"] == "in_review"

    assert publish.status_code == 200
    assert publish.json()["status"] == "draft"
    assert publish.json()["review_status"] == "approved"
    assert publish.json()["metadata_json"]["workflow_state"] == "pending_embedding"
    assert publish.json()["metadata_json"]["published_by"] == "知识管理员"

    assert pending_search.status_code == 200
    assert pending_search.json()["items"] == []

    assert activate.status_code == 200
    assert activate.json()["status"] == "active"
    assert activate.json()["review_status"] == "approved"
    assert activate.json()["metadata_json"]["workflow_state"] == "active_for_retrieval"

    assert active_search.status_code == 200
    assert [result["item"]["id"] for result in active_search.json()["items"]] == [item["id"]]

    assert audit.status_code == 200
    actions = [entry["action"] for entry in audit.json()["items"]]
    assert actions == ["knowledge_activate_retrieval", "knowledge_publish", "knowledge_submit_review"]


def test_phase5_knowledge_archive_and_block_exclude_items_from_retrieval_and_write_audit() -> None:
    collection_id = create_collection()
    archived_item = create_draft_item(collection_id, "phase5_knowledge_review_archive")
    blocked_item = create_draft_item(collection_id, "phase5_knowledge_review_block")

    for item in (archived_item, blocked_item):
        assert client.post(
            f"/knowledge/items/{item['id']}/submit-review",
            json={"actor": "运营", "actor_role": "operator", "review_note": "提交审核"},
        ).status_code == 200
        assert client.post(
            f"/knowledge/items/{item['id']}/publish",
            json={"actor": "知识管理员", "actor_role": "knowledge_admin", "review_note": "审核通过"},
        ).status_code == 200
        assert client.post(
            f"/knowledge/items/{item['id']}/activate-retrieval",
            json={"actor": "技术管理员", "actor_role": "tech_admin", "review_note": "embedding ready"},
        ).status_code == 200

    archive = client.post(
        f"/knowledge/items/{archived_item['id']}/archive",
        json={"actor": "知识管理员", "actor_role": "knowledge_admin", "review_note": "内容过期"},
    )
    block = client.post(
        f"/knowledge/items/{blocked_item['id']}/block",
        json={"actor": "合规", "actor_role": "compliance", "review_note": "存在合规风险"},
    )
    search = client.post(
        "/knowledge/search",
        json={"query": "logistics price", "content_type": "email_reply_template", "auto_reply_only": True},
    )

    assert archive.status_code == 200
    assert archive.json()["status"] == "deprecated"
    assert archive.json()["metadata_json"]["workflow_state"] == "archived"

    assert block.status_code == 200
    assert block.json()["status"] == "disabled"
    assert block.json()["review_status"] == "rejected"
    assert block.json()["metadata_json"]["workflow_state"] == "blocked"
    assert block.json()["metadata_json"]["risk_level"] == "blocked"
    assert block.json()["metadata_json"]["auto_reply_allowed"] is False

    assert search.status_code == 200
    assert search.json()["items"] == []

    archived_audit = client.get(f"/knowledge/items/{archived_item['id']}/review-logs").json()
    blocked_audit = client.get(f"/knowledge/items/{blocked_item['id']}/review-logs").json()
    assert archived_audit["items"][0]["action"] == "knowledge_archive"
    assert blocked_audit["items"][0]["action"] == "knowledge_block"


def test_phase5_knowledge_review_rejects_unauthorized_publish() -> None:
    collection_id = create_collection()
    item = create_draft_item(collection_id, "phase5_knowledge_review_unauthorized")
    assert client.post(
        f"/knowledge/items/{item['id']}/submit-review",
        json={"actor": "运营", "actor_role": "operator", "review_note": "提交审核"},
    ).status_code == 200

    response = client.post(
        f"/knowledge/items/{item['id']}/publish",
        json={"actor": "销售", "actor_role": "sales_manager", "review_note": "尝试发布"},
    )

    assert response.status_code == 403
