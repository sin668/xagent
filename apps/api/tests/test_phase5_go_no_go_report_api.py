import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.db.session import AsyncSessionLocal
from app.main import app
from app.models import (
    Customer,
    EmailMessage,
    EmailReplyDraft,
    EmailSendAttempt,
    EmailThread,
    KnowledgeCollection,
    KnowledgeEmbedding,
    LLMPromptTemplate,
    OutreachRecord,
    RiskEvent,
)
from app.models.enums import (
    ChannelRiskLevel,
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
    RiskEventSeverity,
    RiskEventStatus,
)
from app.models.knowledge import KnowledgeItem
from app.services.knowledge import KnowledgeService


client = TestClient(app)
TEST_PREFIX = "TEST-P5-E9-S3-"
TEST_EMBEDDING = [0.09] * 1536


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
            sync_session.execute(delete(RiskEvent).where(RiskEvent.task_id.like(f"{TEST_PREFIX}%")))
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


async def seed_phase5_go_no_go_records() -> dict[str, tuple[str, str]]:
    base = datetime(2031, 6, 6, tzinfo=UTC)
    windows = {
        "go": (base, base + timedelta(hours=2)),
        "rerun": (base + timedelta(days=1), base + timedelta(days=1, hours=2)),
        "pause": (base + timedelta(days=2), base + timedelta(days=2, hours=2)),
    }
    async with AsyncSessionLocal() as async_session:
        def run(sync_session):
            _seed_prompt_and_knowledge(sync_session)
            _seed_email_quality_window(
                sync_session,
                window_start=windows["go"][0],
                label="go",
                manual_pairs=[("accepted one", "accepted one"), ("accepted two", "accepted two")],
                auto_attempts=[EmailSendAttemptStatus.SENT, EmailSendAttemptStatus.SENT],
                hard_blocked_codes=[
                    "customer_do_not_contact",
                    "customer_de_grade",
                    "reply_language_uncertain",
                    "missing_same_language_knowledge",
                    "missing_knowledge_evidence",
                    "knowledge_retrieval_uncertain",
                ],
            )
            _seed_email_quality_window(
                sync_session,
                window_start=windows["rerun"][0],
                label="rerun",
                manual_pairs=[("short ai", "longer manually rewritten answer"), ("also short", "another human rewrite")],
                auto_attempts=[EmailSendAttemptStatus.SENT, EmailSendAttemptStatus.FAILED],
                hard_blocked_codes=[
                    "customer_do_not_contact",
                    "customer_de_grade",
                    "reply_language_uncertain",
                    "missing_knowledge_evidence",
                ],
            )
            _seed_email_quality_window(
                sync_session,
                window_start=windows["pause"][0],
                label="pause",
                manual_pairs=[("accepted", "accepted"), ("accepted too", "accepted too")],
                auto_attempts=[EmailSendAttemptStatus.SENT],
                hard_blocked_codes=["customer_do_not_contact", "customer_de_grade", "missing_knowledge_evidence"],
            )
            sync_session.add(
                RiskEvent(
                    task_id=f"{TEST_PREFIX}pause-complaint",
                    agent_name="EMAIL_REPLY",
                    action="auto_send",
                    channel="email",
                    risk_level=ChannelRiskLevel.LOW,
                    event_type="complaint",
                    severity=RiskEventSeverity.CRITICAL,
                    resolution_status=RiskEventStatus.OPEN,
                    block_reason="客户投诉自动回复",
                    pause_suggested=True,
                    result="blocked",
                    created_at=windows["pause"][0] + timedelta(minutes=20),
                )
            )
            sync_session.commit()

        await async_session.run_sync(run)
    return {
        key: (start.date().isoformat(), end.date().isoformat())
        for key, (start, end) in windows.items()
    }


def _seed_prompt_and_knowledge(sync_session) -> None:
    prompt_files = ["prompts/lead-extraction.md", "prompts/lead-grading.md"]
    for index, source_file in enumerate(prompt_files, start=1):
        sync_session.add(
            LLMPromptTemplate(
                name=f"{TEST_PREFIX}prompt-{index}",
                task_type=LLMPromptTaskType.LEAD_EXTRACTION if index == 1 else LLMPromptTaskType.LEAD_GRADING,
                provider="file-baseline",
                model="prompt-md",
                system_prompt="system",
                user_prompt_template="user",
                output_schema_json={},
                version=f"v{index}",
                status=LLMPromptTemplateStatus.ACTIVE,
                is_default=True,
                source_file_path=source_file,
                source_file_hash=f"{TEST_PREFIX}hash-{index}",
                migration_batch_id=TEST_PREFIX,
                validation_status="validation_passed",
            )
        )
    service = KnowledgeService(sync_session)
    collection = service.create_collection(
        name=f"{TEST_PREFIX}collection",
        description="第五阶段 Go/No-Go 报告测试集合",
        status=KnowledgeItemStatus.ACTIVE,
        review_status=KnowledgeReviewStatus.APPROVED,
    )
    for index in range(20):
        item = service.create_item(
            collection_id=collection.id,
            title=f"{TEST_PREFIX}knowledge-{index}",
            body="published email reply knowledge",
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
                embedding_status=KnowledgeEmbeddingStatus.READY if index < 19 else KnowledgeEmbeddingStatus.PENDING,
            )
        )


def _seed_email_quality_window(
    sync_session,
    *,
    window_start: datetime,
    label: str,
    manual_pairs: list[tuple[str, str]],
    auto_attempts: list[EmailSendAttemptStatus],
    hard_blocked_codes: list[str],
) -> None:
    customer = Customer(
        external_id=f"{TEST_PREFIX}{label}-{uuid4()}",
        name=f"{label} Dealer",
        country="Russia",
        city="Moscow",
        customer_type=CustomerType.LOCAL_DEALER_SECONDARY_DEALER,
        grade=CustomerGrade.B,
        status=CustomerStatus.READY_FOR_SALES,
    )
    sync_session.add(customer)
    sync_session.flush()
    index = 0
    for ai_body, final_body in manual_pairs:
        index += 1
        _make_draft(
            sync_session,
            customer=customer,
            index=index,
            created_at=window_start + timedelta(minutes=index),
            ai_body=ai_body,
            final_body=final_body,
            manual_review_required=True,
            auto_send_allowed=False,
            decision_json={"route": "manual_review", "business_scene": "first_outreach"},
            attempt_status=EmailSendAttemptStatus.SENT,
        )
    for status in auto_attempts:
        index += 1
        _make_draft(
            sync_session,
            customer=customer,
            index=index,
            created_at=window_start + timedelta(minutes=index),
            ai_body="auto body",
            final_body="auto body",
            manual_review_required=False,
            auto_send_allowed=True,
            decision_json={
                "route": "auto_send_candidate",
                "auto_send_allowed": True,
                "business_scene": "first_outreach",
                "reasons": ["whitelisted_customer", "fixed_faq", "first_touch", "low_risk_scene"],
            },
            attempt_status=status,
        )
    for code in hard_blocked_codes:
        index += 1
        _make_draft(
            sync_session,
            customer=customer,
            index=index,
            created_at=window_start + timedelta(minutes=index),
            ai_body="blocked body",
            final_body="blocked body",
            manual_review_required=True,
            auto_send_allowed=False,
            decision_json={
                "route": "blocked",
                "hard_blocked": True,
                "auto_send_allowed": False,
                "business_scene": "first_outreach",
                "block_reasons": [{"code": code, "message": code, "severity": "critical"}],
            },
            attempt_status=None,
        )


def _make_draft(
    sync_session,
    *,
    customer: Customer,
    index: int,
    created_at: datetime,
    ai_body: str,
    final_body: str | None,
    manual_review_required: bool,
    auto_send_allowed: bool,
    decision_json: dict,
    attempt_status: EmailSendAttemptStatus | None,
) -> None:
    thread = EmailThread(
        customer_id=customer.id,
        subject=f"Go No-Go thread {index}",
        status=EmailThreadStatus.OPEN,
        channel_account="sales@example.com",
        created_at=created_at,
    )
    sync_session.add(thread)
    sync_session.flush()
    inbound = EmailMessage(
        thread_id=thread.id,
        customer_id=customer.id,
        direction=EmailMessageDirection.INBOUND,
        from_email=f"buyer-{index}@example.ru",
        to_emails=["sales@example.com"],
        cc_emails=[],
        subject=f"Question {index}",
        body_text="Need vehicles",
        language="ru",
        status=EmailMessageStatus.PENDING_REPLY,
        source_type=EmailMessageSourceType.MAILBOX_SYNC,
        created_at=created_at,
    )
    sync_session.add(inbound)
    sync_session.flush()
    draft = EmailReplyDraft(
        thread_id=thread.id,
        message_id=inbound.id,
        customer_id=customer.id,
        prompt_version="phase5-go-no-go-v1",
        model="test-model",
        detected_language="ru",
        reply_language="ru",
        language_confidence=0.96,
        ai_suggested_subject=f"AI subject {index}",
        ai_suggested_body=ai_body,
        final_subject=f"Final subject {index}" if final_body is not None else None,
        final_body=final_body,
        knowledge_hits_json=[{"title": "FAQ", "version": "v1", "evidence_note": "published evidence"}],
        auto_send_allowed=auto_send_allowed,
        auto_send_decision_json=decision_json,
        manual_review_required=manual_review_required,
        status=EmailReplyDraftStatus.SENT if attempt_status == EmailSendAttemptStatus.SENT else EmailReplyDraftStatus.DRAFTED,
        reviewed_by="operator" if manual_review_required and final_body is not None else None,
        reviewed_at=created_at + timedelta(minutes=1) if manual_review_required and final_body is not None else None,
        created_at=created_at,
        updated_at=created_at,
    )
    sync_session.add(draft)
    sync_session.flush()
    if attempt_status is not None:
        outreach = OutreachRecord(
            customer_id=customer.id,
            channel=ContactMethodType.EMAIL,
            status=OutreachStatus.SENT if attempt_status == EmailSendAttemptStatus.SENT else OutreachStatus.BAD_CONTACT,
            sent_by="AUTO_SEND" if auto_send_allowed else "operator",
            sent_at=created_at + timedelta(minutes=2),
            response_summary="sent",
            next_action="等待客户回复",
        )
        sync_session.add(outreach)
        sync_session.flush()
        sync_session.add(
            EmailSendAttempt(
                reply_draft_id=draft.id,
                outreach_record_id=outreach.id,
                provider="fake",
                from_email="sales@example.com",
                to_emails=["buyer@example.ru"],
                cc_emails=[],
                bcc_emails=[],
                subject_snapshot=draft.final_subject or draft.ai_suggested_subject or "",
                body_text_snapshot=draft.final_body or draft.ai_suggested_body,
                status=attempt_status,
                attempt_count=1,
                sent_at=created_at + timedelta(minutes=2) if attempt_status == EmailSendAttemptStatus.SENT else None,
                error_code="smtp_error" if attempt_status == EmailSendAttemptStatus.FAILED else None,
                error_message="smtp failed" if attempt_status == EmailSendAttemptStatus.FAILED else None,
            )
        )


def test_phase5_go_no_go_report_returns_go_when_all_product_thresholds_pass() -> None:
    windows = asyncio.run(seed_phase5_go_no_go_records())
    date_from, date_to = windows["go"]

    response = client.get(
        f"/dashboard/phase5-go-no-go-report?knowledge_collection_prefix={TEST_PREFIX}&date_from={date_from}&date_to={date_to}"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["conclusion"] == "go"
    assert body["summary"]["go_ready"] is True
    assert body["time_window"]["date_from"] == date_from
    assert body["time_window"]["date_to"] == date_to
    assert body["thresholds"]["prompt_coverage_rate"] == 1.0
    assert body["metrics"]["prompt_coverage_rate"] == 1.0
    assert body["metrics"]["embedding_ready_rate"] == pytest.approx(0.95)
    assert body["metrics"]["ai_generation_success_rate"] == 1.0
    assert body["metrics"]["manual_adoption_rate"] == 1.0
    assert body["metrics"]["hard_block_accuracy_rate"] == 1.0
    assert body["metrics"]["dnc_no_auto_send_rate"] == 1.0
    assert body["metrics"]["de_grade_no_auto_send_rate"] == 1.0
    assert body["metrics"]["knowledge_guardrail_no_auto_send_rate"] == 1.0
    assert body["metrics"]["complaint_block_violation_count"] == 0
    assert body["data_sources"] == [
        "llm_prompt_templates",
        "knowledge_items",
        "knowledge_embeddings",
        "email_reply_drafts",
        "email_send_attempts",
        "risk_events",
    ]
    assert all(item["passed"] is True for item in body["criteria"])


def test_phase5_go_no_go_report_returns_rerun_for_quality_degradation_without_risk_events() -> None:
    windows = asyncio.run(seed_phase5_go_no_go_records())
    date_from, date_to = windows["rerun"]

    response = client.get(
        f"/dashboard/phase5-go-no-go-report?knowledge_collection_prefix={TEST_PREFIX}&date_from={date_from}&date_to={date_to}"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["conclusion"] == "rerun_small_scope"
    assert body["summary"]["go_ready"] is False
    assert body["metrics"]["manual_adoption_rate"] == 0.0
    assert body["metrics"]["average_edit_distance_ratio"] > 0.5
    assert body["metrics"]["send_failure_rate"] == pytest.approx(1 / 4)
    assert any("人工采纳率低于 50%" in reason for reason in body["reasons"])
    assert "邮件发送失败率偏高但无风险事件，建议重跑小范围。" in body["recommended_actions"]


def test_phase5_go_no_go_report_returns_pause_when_hard_risk_event_exists() -> None:
    windows = asyncio.run(seed_phase5_go_no_go_records())
    date_from, date_to = windows["pause"]

    response = client.get(
        f"/dashboard/phase5-go-no-go-report?knowledge_collection_prefix={TEST_PREFIX}&date_from={date_from}&date_to={date_to}"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["conclusion"] == "pause_auto_send"
    assert body["summary"]["go_ready"] is False
    assert body["metrics"]["complaint_block_violation_count"] == 1
    assert any(item["key"] == "complaint_violation_zero" and item["passed"] is False for item in body["criteria"])
    assert "存在投诉、封禁、违规或建议暂停风险事件，必须暂停自动发送。" in body["recommended_actions"]
