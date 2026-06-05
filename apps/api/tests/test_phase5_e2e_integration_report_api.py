import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.db.session import AsyncSessionLocal
from app.main import app
from app.models import (
    AgentTaskRun,
    Customer,
    EmailMessage,
    EmailReplyDraft,
    EmailSendAttempt,
    EmailThread,
    KnowledgeCollection,
    KnowledgeEmbedding,
    LLMPromptTemplate,
    OutreachRecord,
)
from app.models.enums import (
    AgentTaskRunStatus,
    AgentTaskType,
    ContactMethodType,
    CustomerGrade,
    CustomerStatus,
    CustomerType,
    EmailMessageDirection,
    EmailMessageSourceType,
    EmailMessageStatus,
    EmailReplyDraftStatus,
    EmailSendAttemptStatus,
    EmailThreadStatus,
    KnowledgeEmbeddingStatus,
    KnowledgeItemStatus,
    KnowledgeReviewStatus,
    LLMPromptTaskType,
    LLMPromptTemplateStatus,
    OutreachStatus,
)
from app.services.knowledge import KnowledgeService


client = TestClient(app)
TEST_PREFIX = "TEST-P5-E9-S4-"
TEST_EMBEDDING = [0.11] * 1536


async def cleanup_records() -> None:
    async with AsyncSessionLocal() as async_session:
        def run(sync_session):
            customer_ids = sync_session.scalars(
                select(Customer.id).where(Customer.external_id.like(f"{TEST_PREFIX}%"))
            ).all()
            if customer_ids:
                draft_ids = sync_session.scalars(
                    select(EmailReplyDraft.id).where(EmailReplyDraft.customer_id.in_(customer_ids))
                ).all()
                if draft_ids:
                    sync_session.execute(delete(EmailSendAttempt).where(EmailSendAttempt.reply_draft_id.in_(draft_ids)))
                sync_session.execute(delete(OutreachRecord).where(OutreachRecord.customer_id.in_(customer_ids)))
                sync_session.execute(delete(EmailReplyDraft).where(EmailReplyDraft.customer_id.in_(customer_ids)))
                sync_session.execute(delete(EmailMessage).where(EmailMessage.customer_id.in_(customer_ids)))
                sync_session.execute(delete(EmailThread).where(EmailThread.customer_id.in_(customer_ids)))
            sync_session.execute(delete(Customer).where(Customer.external_id.like(f"{TEST_PREFIX}%")))
            sync_session.execute(delete(AgentTaskRun).where(AgentTaskRun.trigger_source.like(f"{TEST_PREFIX}%")))
            sync_session.execute(delete(LLMPromptTemplate).where(LLMPromptTemplate.name.like(f"{TEST_PREFIX}%")))
            collections = sync_session.scalars(
                select(KnowledgeCollection).where(KnowledgeCollection.name.like(f"{TEST_PREFIX}%"))
            ).all()
            for collection in collections:
                sync_session.delete(collection)
            sync_session.commit()

        await async_session.run_sync(run)


def setup_function() -> None:
    asyncio.run(cleanup_records())


def teardown_function() -> None:
    asyncio.run(cleanup_records())


async def seed_phase5_e2e_records() -> tuple[str, str]:
    started_at = datetime(2032, 6, 6, 9, 0, tzinfo=UTC)
    async with AsyncSessionLocal() as async_session:
        def run(sync_session):
            sync_session.add(
                LLMPromptTemplate(
                    name=f"{TEST_PREFIX}email_reply_prompt",
                    task_type=LLMPromptTaskType.EMAIL_REPLY_DRAFT,
                    provider="file-baseline",
                    model="prompt-md",
                    system_prompt="EMAIL_REPLY 必须保留风险边界，不自动发送，不编造。",
                    user_prompt_template="请基于客户上下文生成建议回复。",
                    output_schema_json={"type": "object"},
                    version="email-reply-e2e-v1",
                    status=LLMPromptTemplateStatus.ACTIVE,
                    is_default=True,
                    source_file_path="prompts/email-reply-draft.md",
                    source_file_hash=f"{TEST_PREFIX}prompt-hash",
                    migration_batch_id=TEST_PREFIX,
                    validation_status="validation_passed",
                    created_at=started_at,
                    updated_at=started_at,
                )
            )
            service = KnowledgeService(sync_session)
            collection = service.create_collection(
                name=f"{TEST_PREFIX}collection",
                description="第五阶段端到端联调知识集合",
                status=KnowledgeItemStatus.ACTIVE,
                review_status=KnowledgeReviewStatus.APPROVED,
            )
            item = service.create_item(
                collection_id=collection.id,
                title=f"{TEST_PREFIX}fixed_faq",
                body="Approved fixed FAQ for first outreach.",
                status=KnowledgeItemStatus.ACTIVE,
                review_status=KnowledgeReviewStatus.APPROVED,
                content_type="email_reply_template",
                business_scene="first_outreach",
                risk_level="Low",
                auto_reply_allowed=True,
            )
            sync_session.add(
                KnowledgeEmbedding(
                    item_id=item.id,
                    embedding_model="test-embedding",
                    embedding=TEST_EMBEDDING,
                    embedding_dimensions=1536,
                    embedding_status=KnowledgeEmbeddingStatus.READY,
                    created_at=started_at,
                )
            )
            customer = Customer(
                external_id=f"{TEST_PREFIX}{uuid4()}",
                name="E2E Dealer",
                country="Russia",
                city="Moscow",
                customer_type=CustomerType.LOCAL_DEALER_SECONDARY_DEALER,
                grade=CustomerGrade.B,
                status=CustomerStatus.READY_FOR_SALES,
                created_at=started_at,
                updated_at=started_at,
            )
            sync_session.add(customer)
            sync_session.flush()

            def make_thread_message(offset: int) -> tuple[EmailThread, EmailMessage]:
                created_at = started_at + timedelta(minutes=offset)
                thread = EmailThread(
                    customer_id=customer.id,
                    subject=f"E2E inquiry {offset}",
                    status=EmailThreadStatus.OPEN,
                    channel_account="sales@example.com",
                    created_at=created_at,
                    updated_at=created_at,
                )
                sync_session.add(thread)
                sync_session.flush()
                message = EmailMessage(
                    thread_id=thread.id,
                    customer_id=customer.id,
                    direction=EmailMessageDirection.INBOUND,
                    from_email=f"buyer-{offset}@example.ru",
                    to_emails=["sales@example.com"],
                    cc_emails=[],
                    subject=f"E2E inquiry {offset}",
                    body_text="Need vehicle sourcing information.",
                    language="ru",
                    status=EmailMessageStatus.PENDING_REPLY,
                    source_type=EmailMessageSourceType.MAILBOX_SYNC,
                    created_at=created_at,
                )
                sync_session.add(message)
                sync_session.flush()
                return thread, message

            task_run = AgentTaskRun(
                task_type=AgentTaskType.EMAIL_REPLY,
                status=AgentTaskRunStatus.SUCCEEDED,
                trigger_source=f"{TEST_PREFIX}email_reply_runtime",
                input_json={"request_id": str(uuid4())},
                output_summary_json={
                    "schema_version": "email-reply-v1",
                    "knowledge_hit_count": 1,
                    "manual_review_required": True,
                    "writes_core_tables": False,
                },
                prompt_version="email-reply-e2e-v1",
                started_at=started_at + timedelta(minutes=3),
                finished_at=started_at + timedelta(minutes=4),
                created_at=started_at + timedelta(minutes=3),
                updated_at=started_at + timedelta(minutes=4),
            )
            sync_session.add(task_run)
            sync_session.flush()

            manual_thread, manual_message = make_thread_message(10)
            manual_draft = EmailReplyDraft(
                thread_id=manual_thread.id,
                message_id=manual_message.id,
                customer_id=customer.id,
                agent_task_run_id=task_run.id,
                prompt_version="email-reply-e2e-v1",
                model="test-model",
                detected_language="ru",
                reply_language="ru",
                language_confidence=0.96,
                ai_suggested_subject="AI subject",
                ai_suggested_body="AI suggested body",
                final_subject="Human subject",
                final_body="Human reviewed body",
                knowledge_hits_json=[{"knowledge_item_id": str(item.id), "title": item.title, "evidence_note": "approved FAQ"}],
                auto_send_allowed=False,
                auto_send_decision_json={"route": "manual_review", "business_scene": "first_outreach"},
                manual_review_required=True,
                status=EmailReplyDraftStatus.SENT,
                reviewed_by="销售B",
                reviewed_at=started_at + timedelta(minutes=12),
                created_at=started_at + timedelta(minutes=11),
                updated_at=started_at + timedelta(minutes=13),
            )
            sync_session.add(manual_draft)
            sync_session.flush()
            outreach = OutreachRecord(
                customer_id=customer.id,
                channel=ContactMethodType.EMAIL,
                status=OutreachStatus.SENT,
                sent_by="销售B",
                sent_at=started_at + timedelta(minutes=14),
                response_summary="人工确认邮件已发送",
                next_action="等待客户回复",
                script_version="email-reply-e2e-v1",
                created_at=started_at + timedelta(minutes=14),
            )
            sync_session.add(outreach)
            sync_session.flush()
            sync_session.add(
                EmailSendAttempt(
                    reply_draft_id=manual_draft.id,
                    outreach_record_id=outreach.id,
                    provider="fake",
                    from_email="sales@example.com",
                    to_emails=["buyer-10@example.ru"],
                    cc_emails=[],
                    bcc_emails=[],
                    subject_snapshot="Human subject",
                    body_text_snapshot="Human reviewed body",
                    status=EmailSendAttemptStatus.SENT,
                    attempt_count=1,
                    sent_at=started_at + timedelta(minutes=14),
                )
            )
            manual_draft.sent_record_id = outreach.id

            blocked_thread, blocked_message = make_thread_message(20)
            sync_session.add(
                EmailReplyDraft(
                    thread_id=blocked_thread.id,
                    message_id=blocked_message.id,
                    customer_id=customer.id,
                    prompt_version="email-reply-e2e-v1",
                    model="test-model",
                    detected_language="ru",
                    reply_language="ru",
                    language_confidence=0.4,
                    ai_suggested_subject="Blocked subject",
                    ai_suggested_body="Blocked body",
                    final_subject=None,
                    final_body=None,
                    knowledge_hits_json=[],
                    auto_send_allowed=False,
                    auto_send_decision_json={
                        "route": "blocked",
                        "business_scene": "first_outreach",
                        "hard_blocked": True,
                        "auto_send_allowed": False,
                        "block_reasons": [{"code": "missing_knowledge_evidence", "message": "缺少知识证据"}],
                    },
                    manual_review_required=True,
                    manual_review_reason="命中硬拦截规则，禁止自动发送。",
                    status=EmailReplyDraftStatus.BLOCKED,
                    created_at=started_at + timedelta(minutes=21),
                    updated_at=started_at + timedelta(minutes=22),
                )
            )
            sync_session.commit()

        await async_session.run_sync(run)
    return started_at.date().isoformat(), (started_at + timedelta(hours=1)).date().isoformat()


def test_phase5_e2e_integration_report_verifies_real_api_agent_admin_and_metrics_chain() -> None:
    date_from, date_to = asyncio.run(seed_phase5_e2e_records())

    response = client.get(
        f"/dashboard/phase5-e2e-integration-report?date_from={date_from}&date_to={date_to}&knowledge_collection_prefix={TEST_PREFIX}"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["overall_status"] == "passed"
    assert body["seed_fallback_allowed"] is False
    assert body["time_window"] == {"date_from": date_from, "date_to": date_to}
    stage_map = {stage["key"]: stage for stage in body["stages"]}
    expected_stages = {
        "prompt_import",
        "knowledge_publish",
        "embedding_ready",
        "email_import",
        "email_reply_agent",
        "manual_confirm_send",
        "auto_send_blocked",
        "outreach_history",
        "quality_metrics",
        "go_no_go_report",
        "admin_real_api",
    }
    assert set(stage_map) == expected_stages
    assert all(stage["status"] == "passed" for stage in stage_map.values())
    assert stage_map["email_reply_agent"]["evidence"]["writes_core_tables"] is False
    assert stage_map["manual_confirm_send"]["evidence"]["sent_attempt_count"] >= 1
    assert stage_map["auto_send_blocked"]["evidence"]["blocked_draft_count"] >= 1
    assert stage_map["quality_metrics"]["evidence"]["email_reply_draft_count"] >= 2
    assert stage_map["go_no_go_report"]["evidence"]["conclusion"] in {"go", "rerun_small_scope", "pause_auto_send"}
    assert stage_map["admin_real_api"]["evidence"]["checked_contracts"] == [
        "/llm-prompt-templates",
        "/knowledge/items",
        "/email-reply/drafts",
        "/dashboard/email-reply-quality",
        "/dashboard/phase5-go-no-go-report",
    ]
    assert body["summary"]["passed_count"] == body["summary"]["total_count"]
    assert "真实 PostgreSQL" in body["notes"][0]
