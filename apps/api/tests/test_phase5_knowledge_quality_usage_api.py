import asyncio

import pytest
from fastapi.testclient import TestClient

from app.db.session import AsyncSessionLocal
from app.main import app
from app.models.email_message import EmailMessage
from app.models.email_reply_draft import EmailReplyDraft
from app.models.email_thread import EmailThread
from app.models.enums import EmailMessageDirection, EmailMessageSourceType, EmailMessageStatus, EmailReplyDraftStatus
from app.models.knowledge import KnowledgeCollection
from app.services.knowledge import KnowledgeService


client = TestClient(app)
MARKER = "phase5_knowledge_quality_usage_"


def cleanup_phase5_knowledge_quality_usage_records() -> None:
    async def run_cleanup() -> None:
        async with AsyncSessionLocal() as async_session:
            def run(sync_session):
                collections = sync_session.query(KnowledgeCollection).filter(
                    KnowledgeCollection.name.like(f"{MARKER}%")
                ).all()
                for collection in collections:
                    sync_session.delete(collection)
                threads = sync_session.query(EmailThread).filter(EmailThread.subject.like(f"{MARKER}%")).all()
                for thread in threads:
                    sync_session.delete(thread)
                sync_session.commit()

            await async_session.run_sync(run)

    asyncio.run(run_cleanup())


@pytest.fixture(autouse=True)
def cleanup_phase5_knowledge_quality_usage_api_records():
    cleanup_phase5_knowledge_quality_usage_records()
    yield
    cleanup_phase5_knowledge_quality_usage_records()


def seed_knowledge_and_reply_draft() -> dict[str, str]:
    result: dict[str, str] = {}

    async def seed() -> None:
        async with AsyncSessionLocal() as async_session:
            def run(sync_session):
                service = KnowledgeService(sync_session)
                collection = service.create_collection(
                    name=f"{MARKER}collection",
                    description="第五阶段知识质量使用记录 API 测试集合",
                    status="active",
                    review_status="approved",
                )
                item = service.create_item(
                    collection_id=collection.id,
                    title=f"{MARKER}email_template",
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
                    version="v3",
                )
                thread = EmailThread(subject=f"{MARKER}thread", status="open", channel_account="ops@example.com")
                sync_session.add(thread)
                sync_session.flush()
                message = EmailMessage(
                    thread_id=thread.id,
                    direction=EmailMessageDirection.INBOUND,
                    from_email="buyer@example.com",
                    to_emails=["ops@example.com"],
                    subject=f"{MARKER}thread",
                    body_text="Need logistics details",
                    language="ru",
                    status=EmailMessageStatus.PENDING_REPLY,
                    source_type=EmailMessageSourceType.MANUAL,
                )
                sync_session.add(message)
                sync_session.flush()
                draft = EmailReplyDraft(
                    thread_id=thread.id,
                    message_id=message.id,
                    prompt_version="v1",
                    model="test-model",
                    detected_language="ru",
                    reply_language="ru",
                    language_confidence=0.98,
                    ai_suggested_subject="Re: logistics",
                    ai_suggested_body="Thanks, here is the process.",
                    knowledge_hits_json=[{"knowledge_item_id": str(item.id), "version": item.version}],
                    auto_send_allowed=False,
                    auto_send_decision_json={"reason": "manual_review"},
                    manual_review_required=True,
                    manual_review_reason="人工确认",
                    status=EmailReplyDraftStatus.PENDING_REVIEW,
                )
                sync_session.add(draft)
                sync_session.commit()
                result["item_id"] = str(item.id)
                result["draft_id"] = str(draft.id)

            await async_session.run_sync(run)

    asyncio.run(seed())
    return result


def test_phase5_knowledge_usage_api_records_email_reply_draft_usage_and_quality_summary() -> None:
    ids = seed_knowledge_and_reply_draft()

    first = client.post(
        f"/knowledge/items/{ids['item_id']}/usage-records",
        json={
            "email_reply_draft_id": ids["draft_id"],
            "retrieval_query": "logistics cooperation",
            "similarity_score": 0.91,
            "rank": 1,
            "filters_json": {"language": "ru", "business_scene": "first_outreach"},
            "outcome": "adopted",
            "adopted": True,
            "edit_distance_ratio": 0.2,
            "caused_bounce": False,
            "customer_replied": True,
            "suggest_deprecate": False,
        },
    )
    second = client.post(
        f"/knowledge/items/{ids['item_id']}/usage-records",
        json={
            "retrieval_query": "logistics cooperation",
            "similarity_score": 0.4,
            "rank": 2,
            "filters_json": {"language": "ru", "business_scene": "first_outreach"},
            "outcome": "bounced",
            "adopted": False,
            "edit_distance_ratio": None,
            "caused_bounce": True,
            "customer_replied": False,
            "suggest_deprecate": True,
            "suggest_deprecate_reason": "退信且未被采纳",
        },
    )
    summary = client.get(f"/knowledge/items/{ids['item_id']}/quality-summary")

    assert first.status_code == 200
    assert first.json()["knowledge_item_id"] == ids["item_id"]
    assert first.json()["knowledge_version"] == "v3"
    assert first.json()["email_reply_draft_id"] == ids["draft_id"]
    assert first.json()["outcome"] == "adopted"

    assert second.status_code == 200
    assert second.json()["caused_bounce"] is True
    assert second.json()["suggest_deprecate"] is True

    assert summary.status_code == 200
    body = summary.json()
    assert body["knowledge_item_id"] == ids["item_id"]
    assert body["knowledge_version"] == "v3"
    assert body["retrieval_count"] == 2
    assert body["adoption_count"] == 1
    assert body["adoption_rate"] == 0.5
    assert body["average_edit_distance_ratio"] == 0.2
    assert body["bounce_count"] == 1
    assert body["bounce_rate"] == 0.5
    assert body["customer_reply_count"] == 1
    assert body["customer_reply_rate"] == 0.5
    assert body["suggest_deprecate"] is True
    assert body["suggest_deprecate_reason"] == "退信且未被采纳"


def test_phase5_knowledge_usage_api_rejects_unknown_email_reply_draft() -> None:
    ids = seed_knowledge_and_reply_draft()

    response = client.post(
        f"/knowledge/items/{ids['item_id']}/usage-records",
        json={
            "email_reply_draft_id": "00000000-0000-0000-0000-000000000000",
            "retrieval_query": "logistics cooperation",
            "filters_json": {"language": "ru"},
            "outcome": "retrieved",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "email reply draft 不存在。"
