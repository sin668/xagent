from datetime import datetime
from types import SimpleNamespace
import asyncio
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.api.staging_leads import serialize_staging_lead_detail
from app.db.session import AsyncSessionLocal
from app.main import app
from app.models.ai_audit_log import AIAuditLog
from app.models.candidate_url import CandidateUrl
from app.models.collection_task import CollectionTask
from app.models.enums import (
    AITaskType,
    CandidateUrlStatus,
    ChannelRiskLevel,
    CollectionTaskStatus,
    CustomerGrade,
    CustomerType,
    PageSnapshotReadStatus,
    SourcePlatform,
    SourceUsageType,
    StagingQueueStatus,
    StagingReviewStatus,
)
from app.models.staging_lead import StagingLead
from app.services.staging_leads import StagingLeadService


TEST_PREFIX = "staging-detail-json-contains"
client = TestClient(app)


def _candidate(**overrides):
    payload = {
        "id": uuid4(),
        "url": "https://dealer.example.ru",
        "source_platform": SourcePlatform.OFFICIAL_WEBSITE,
        "source_risk_level": ChannelRiskLevel.LOW,
        "source_usage_type": SourceUsageType.AUTOMATIC_COLLECTION,
        "requires_secondary_verification": False,
        "queue_eligible": True,
        "discovery_reason": "官网公开展示进口二手车库存。",
        "status": CandidateUrlStatus.STAGED,
    }
    payload.update(overrides)
    return SimpleNamespace(**payload)


def _lead(**overrides):
    now = datetime(2026, 5, 29, 9, 0, 0)
    candidate = overrides.pop("candidate_url", _candidate())
    payload = {
        "id": uuid4(),
        "candidate_url_id": candidate.id,
        "candidate_url": candidate,
        "customer_name": "Auto City Moscow",
        "country": "Russia",
        "city": "Moscow",
        "customer_type": CustomerType.LOCAL_DEALER_SECONDARY_DEALER,
        "contacts_json": [{"type": "email", "value": "sales@dealer.example.ru"}],
        "activity_level": "active",
        "scale_signal": "公开页面展示多台库存。",
        "import_used_car_relevance": "high",
        "source_evidence": "官网公开页面展示进口二手车库存与邮箱。",
        "recommended_grade": CustomerGrade.B,
        "recommended_reason": "经营类型、城市、公开联系方式和进口二手相关性清晰。",
        "missing_fields": ["月采购量"],
        "review_status": StagingReviewStatus.PENDING_REVIEW,
        "queue_status": StagingQueueStatus.PENDING_REVIEW,
        "dedupe_key": "auto city moscow::moscow::sales@dealer.example.ru",
        "requires_compliance_review": False,
        "created_at": now,
        "updated_at": now,
    }
    payload.update(overrides)
    return SimpleNamespace(**payload)


def _snapshot(**overrides):
    payload = {
        "id": uuid4(),
        "page_title": "Auto City Moscow",
        "text_excerpt": "完整网页正文不得暴露在详情响应。",
        "evidence_note": "页面包含库存、地址和公开邮箱。",
        "read_status": PageSnapshotReadStatus.SUCCESS,
        "captured_at": datetime(2026, 5, 29, 10, 0, 0),
        "robots_or_policy_note": "公开官网页面。",
    }
    payload.update(overrides)
    return SimpleNamespace(**payload)


def _audit(**overrides):
    payload = {
        "id": uuid4(),
        "task_type": AITaskType.LEAD_GRADING,
        "model_name": "gpt-test",
        "prompt_version": "lead-grading-v1",
        "output_payload": {
            "recommended_grade": "B",
            "recommended_reason": "公开证据完整，适合客服复核。",
            "missing_fields": ["月采购量"],
        },
        "output_json": None,
        "risk_blocked": False,
        "risk_block_reason": None,
        "executed_at": datetime(2026, 5, 29, 10, 5, 0),
    }
    payload.update(overrides)
    return SimpleNamespace(**payload)


def test_core_gate_blocks_missing_source_or_evidence() -> None:
    missing_source = StagingLeadService.core_gate_status(
        source_url=None,
        has_evidence=True,
        source_risk_level=ChannelRiskLevel.LOW,
        recommended_grade=CustomerGrade.B,
        review_status=StagingReviewStatus.PENDING_REVIEW,
        queue_status=StagingQueueStatus.PENDING_REVIEW,
    )
    missing_evidence = StagingLeadService.core_gate_status(
        source_url="https://dealer.example.ru",
        has_evidence=False,
        source_risk_level=ChannelRiskLevel.LOW,
        recommended_grade=CustomerGrade.B,
        review_status=StagingReviewStatus.PENDING_REVIEW,
        queue_status=StagingQueueStatus.PENDING_REVIEW,
    )

    assert missing_source["can_promote_to_core"] is False
    assert "缺少来源链接" in missing_source["reasons"]
    assert missing_evidence["can_promote_to_core"] is False
    assert "缺少来源证据" in missing_evidence["reasons"]


def test_core_gate_blocks_high_secondary_and_watch_invalid() -> None:
    gate = StagingLeadService.core_gate_status(
        source_url="https://vk.example/dealer",
        has_evidence=True,
        source_risk_level=ChannelRiskLevel.HIGH,
        recommended_grade=CustomerGrade.WATCH,
        review_status=StagingReviewStatus.NEEDS_SECONDARY_VERIFICATION,
        queue_status=StagingQueueStatus.NOT_ELIGIBLE,
    )

    assert gate["can_promote_to_core"] is False
    assert "High 来源需完成 Low/Medium 二次复核" in gate["reasons"]
    assert "Watch 不得进入 core 或触达队列" in gate["reasons"]
    assert "当前队列状态不可晋级" in gate["reasons"]


def test_staging_lead_detail_response_includes_sanitized_evidence_audit_and_gate() -> None:
    do_not_contact_customer_id = uuid4()
    detail = serialize_staging_lead_detail(
        _lead(),
        _snapshot(),
        _audit(),
        do_not_contact_customer_id=do_not_contact_customer_id,
    )

    assert detail.staging_lead.customer_name == "Auto City Moscow"
    assert detail.candidate_url.url == "https://dealer.example.ru"
    assert detail.latest_page_snapshot.evidence_note == "页面包含库存、地址和公开邮箱。"
    assert not hasattr(detail.latest_page_snapshot, "text_excerpt")
    assert detail.ai_audit_summary.model_name == "gpt-test"
    assert detail.ai_audit_summary.recommended_grade == "B"
    assert detail.core_gate.can_promote_to_core is True
    assert detail.core_gate.status == "ready"
    assert detail.has_do_not_contact_match is True
    assert detail.do_not_contact_customer_id == do_not_contact_customer_id


async def cleanup_db_records() -> None:
    async with AsyncSessionLocal() as async_session:
        await async_session.execute(delete(AIAuditLog).where(AIAuditLog.model_name.like(f"{TEST_PREFIX}%")))
        await async_session.execute(delete(StagingLead).where(StagingLead.customer_name.like(f"{TEST_PREFIX}%")))
        await async_session.execute(delete(CandidateUrl).where(CandidateUrl.url.like(f"https://{TEST_PREFIX}%")))
        await async_session.execute(delete(CollectionTask).where(CollectionTask.channel_name.like(f"{TEST_PREFIX}%")))
        await async_session.commit()


async def seed_staging_lead_with_audit_source_urls() -> str:
    suffix = uuid4().hex[:10]
    source_url = f"https://{TEST_PREFIX}-{suffix}.example.ru/dealer"
    async with AsyncSessionLocal() as async_session:
        def run(sync_session):
            task = CollectionTask(
                task_type="staging_detail_regression",
                channel_name=f"{TEST_PREFIX}-{suffix}",
                risk_level=ChannelRiskLevel.LOW,
                source_usage_type=SourceUsageType.AUTOMATIC_COLLECTION,
                max_sample_size=1,
                allowed_actions="公开页面读取；AI审计查询。",
                forbidden_actions="不登录；不自动触达；不反爬规避。",
                status=CollectionTaskStatus.COMPLETED,
            )
            sync_session.add(task)
            sync_session.flush()
            candidate = CandidateUrl(
                task_id=task.id,
                url=source_url,
                url_hash=StagingLeadService.source_url_hash(source_url),
                source_platform=SourcePlatform.OFFICIAL_WEBSITE,
                source_risk_level=ChannelRiskLevel.LOW,
                source_usage_type=SourceUsageType.AUTOMATIC_COLLECTION,
                requires_secondary_verification=False,
                queue_eligible=True,
                discovery_reason="公开官网页面。",
                status=CandidateUrlStatus.STAGED,
            )
            sync_session.add(candidate)
            sync_session.flush()
            lead = StagingLead(
                candidate_url_id=candidate.id,
                customer_name=f"{TEST_PREFIX} Auto City",
                country="Russia",
                city="Moscow",
                customer_type=CustomerType.LOCAL_DEALER_SECONDARY_DEALER,
                contacts_json=[{"type": "email", "value": "sales@example.ru"}],
                source_evidence="公开官网证据。",
                recommended_grade=CustomerGrade.B,
                recommended_reason="公开联系方式和经营信号完整。",
                missing_fields=[],
                review_status=StagingReviewStatus.PENDING_REVIEW,
                queue_status=StagingQueueStatus.PENDING_REVIEW,
                requires_compliance_review=False,
            )
            sync_session.add(lead)
            sync_session.add(
                AIAuditLog(
                    task_type=AITaskType.LEAD_GRADING,
                    model_name=f"{TEST_PREFIX}-model",
                    prompt_version="lead-grading-v1",
                    source_url=None,
                    source_urls=[source_url],
                    output_payload={
                        "recommended_grade": "B",
                        "recommended_reason": "公开证据完整。",
                        "missing_fields": [],
                    },
                    risk_blocked=False,
                )
            )
            sync_session.flush()
            return str(lead.id)

        lead_id = await async_session.run_sync(run)
        await async_session.commit()
        return lead_id


def test_get_staging_lead_detail_matches_json_source_urls_without_invalid_json_like() -> None:
    asyncio.run(cleanup_db_records())
    lead_id = asyncio.run(seed_staging_lead_with_audit_source_urls())

    try:
        response = client.get(f"/staging-leads/{lead_id}")
        assert response.status_code == 200
        payload = response.json()
        assert payload["staging_lead"]["id"] == lead_id
        assert payload["ai_audit_summary"]["model_name"] == f"{TEST_PREFIX}-model"
    finally:
        asyncio.run(cleanup_db_records())
