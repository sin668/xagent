import asyncio

import pytest
from fastapi.testclient import TestClient

from app.db.session import AsyncSessionLocal
from app.main import app
from app.models.enums import (
    KnowledgeEmbeddingStatus,
    KnowledgeItemStatus,
    KnowledgeReviewStatus,
    LLMPromptTaskType,
    LLMPromptTemplateStatus,
)
from app.models.knowledge import KnowledgeCollection, KnowledgeEmbedding
from app.models.llm_prompt_template import LLMPromptTemplate
from app.services.knowledge import KnowledgeService


client = TestClient(app)
MARKER = "phase5_quality_foundation_"
TEST_EMBEDDING = [0.07] * 1536


def cleanup_records() -> None:
    async def run_cleanup() -> None:
        async with AsyncSessionLocal() as async_session:
            def run(sync_session):
                sync_session.query(LLMPromptTemplate).filter(
                    LLMPromptTemplate.name.like(f"{MARKER}%")
                ).delete(synchronize_session=False)
                collections = sync_session.query(KnowledgeCollection).filter(
                    KnowledgeCollection.name.like(f"{MARKER}%")
                ).all()
                for collection in collections:
                    sync_session.delete(collection)
                sync_session.commit()

            await async_session.run_sync(run)

    asyncio.run(run_cleanup())


@pytest.fixture(autouse=True)
def cleanup_phase5_quality_foundation_records():
    cleanup_records()
    yield
    cleanup_records()


def seed_quality_foundation_records() -> None:
    async def seed() -> None:
        async with AsyncSessionLocal() as async_session:
            def run(sync_session):
                sync_session.add_all(
                    [
                        LLMPromptTemplate(
                            name=f"{MARKER}lead_extraction",
                            task_type=LLMPromptTaskType.LEAD_EXTRACTION,
                            provider="file-baseline",
                            model="prompt-md",
                            system_prompt="system",
                            user_prompt_template="user",
                            output_schema_json={},
                            version="lead-extraction-v1",
                            status=LLMPromptTemplateStatus.ACTIVE,
                            is_default=True,
                            source_file_path="prompts/lead-extraction.md",
                            source_file_hash="hash-lead-extraction",
                            migration_batch_id=MARKER,
                            validation_status="validation_passed",
                        ),
                        LLMPromptTemplate(
                            name=f"{MARKER}lead_grading",
                            task_type=LLMPromptTaskType.LEAD_GRADING,
                            provider="file-baseline",
                            model="prompt-md",
                            system_prompt="system",
                            user_prompt_template="user",
                            output_schema_json={},
                            version="lead-grading-v1",
                            status=LLMPromptTemplateStatus.ACTIVE,
                            is_default=True,
                            source_file_path="prompts/lead-grading.md",
                            source_file_hash="hash-lead-grading",
                            migration_batch_id=MARKER,
                            validation_status="validation_passed",
                        ),
                    ]
                )
                service = KnowledgeService(sync_session)
                collection = service.create_collection(
                    name=f"{MARKER}collection",
                    description="第五阶段质量基础指标测试集合",
                    status=KnowledgeItemStatus.ACTIVE,
                    review_status=KnowledgeReviewStatus.APPROVED,
                )
                ready_item = service.create_item(
                    collection_id=collection.id,
                    title=f"{MARKER}ready",
                    body="ready knowledge",
                    status=KnowledgeItemStatus.ACTIVE,
                    review_status=KnowledgeReviewStatus.APPROVED,
                    content_type="email_reply_template",
                    business_scene="first_outreach",
                    risk_level="Low",
                    auto_reply_allowed=True,
                )
                pending_item = service.create_item(
                    collection_id=collection.id,
                    title=f"{MARKER}pending",
                    body="pending knowledge",
                    status=KnowledgeItemStatus.ACTIVE,
                    review_status=KnowledgeReviewStatus.APPROVED,
                    content_type="qa_entry",
                    business_scene="faq",
                    risk_level="Low",
                    auto_reply_allowed=True,
                )
                failed_item = service.create_item(
                    collection_id=collection.id,
                    title=f"{MARKER}failed",
                    body="failed knowledge",
                    status=KnowledgeItemStatus.ACTIVE,
                    review_status=KnowledgeReviewStatus.APPROVED,
                    content_type="compliance_phrase",
                    business_scene="risk_guardrail",
                    risk_level="Medium",
                    auto_reply_allowed=False,
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
                            error_message="provider timeout",
                        ),
                    ]
                )
                sync_session.commit()

            await async_session.run_sync(run)

    asyncio.run(seed())


def test_phase5_quality_foundation_metrics_reports_prompt_knowledge_and_embedding_readiness() -> None:
    seed_quality_foundation_records()

    response = client.get(f"/dashboard/phase5-quality-foundation?knowledge_collection_prefix={MARKER}")

    assert response.status_code == 200
    body = response.json()
    assert body["prompt_metrics"]["expected_prompt_file_count"] == 2
    assert body["prompt_metrics"]["covered_prompt_file_count"] == 2
    assert body["prompt_metrics"]["prompt_coverage_rate"] == 1.0
    assert body["prompt_metrics"]["missing_prompt_files"] == []
    assert body["knowledge_metrics"]["published_knowledge_count"] == 3
    assert body["knowledge_metrics"]["active_for_retrieval_count"] == 3
    assert body["knowledge_metrics"]["auto_reply_allowed_count"] == 2
    assert body["embedding_metrics"]["embedding_task_count"] == 3
    assert body["embedding_metrics"]["ready_count"] == 1
    assert body["embedding_metrics"]["pending_count"] == 1
    assert body["embedding_metrics"]["failed_count"] == 1
    assert body["embedding_metrics"]["ready_rate"] == pytest.approx(1 / 3)
    assert body["go_no_go_ready"] is False
    assert "embedding ready 率低于 95%" in body["go_no_go_reasons"]
