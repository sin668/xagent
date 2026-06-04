import asyncio
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.db.session import AsyncSessionLocal
from app.main import app
from app.models import AIAuditLog, SyncLog
from app.models.enums import AITaskType, SyncStatus


TEST_PREFIX = "TEST-E8S3-"
TEST_MODEL = "test-sync-ai-audit"


async def cleanup_records() -> None:
    async with AsyncSessionLocal() as async_session:
        await async_session.execute(delete(AIAuditLog).where(AIAuditLog.model_name == TEST_MODEL))
        await async_session.execute(delete(SyncLog).where(SyncLog.source_name == TEST_PREFIX))
        await async_session.commit()


async def seed_records() -> None:
    async with AsyncSessionLocal() as async_session:
        def add(sync_session):
            now = datetime.utcnow()
            sync_session.add_all(
                [
                    SyncLog(
                        source_name=TEST_PREFIX,
                        object_name="客户线索",
                        status=SyncStatus.SUCCESS,
                        success_count=10,
                        failure_count=0,
                        started_at=now - timedelta(minutes=12),
                        finished_at=now - timedelta(minutes=11),
                    ),
                    SyncLog(
                        source_name=TEST_PREFIX,
                        object_name="渠道来源",
                        status=SyncStatus.FAILED,
                        success_count=0,
                        failure_count=2,
                        error_summary="字段 渠道风险等级 缺失",
                        started_at=now - timedelta(minutes=5),
                        finished_at=now - timedelta(minutes=4),
                    ),
                ]
            )
            sync_session.add_all(
                [
                    AIAuditLog(
                        task_type=AITaskType.LEAD_EXTRACTION,
                        model_name=TEST_MODEL,
                        prompt_version="extract-v1",
                        source_url="https://example.com/lead",
                        input_payload={"channel_name": "official_website"},
                        output_payload={"status": "stored"},
                        risk_blocked=False,
                        executed_at=now - timedelta(minutes=3),
                    ),
                    AIAuditLog(
                        task_type=AITaskType.OUTREACH_DRAFT,
                        model_name=TEST_MODEL,
                        prompt_version="draft-v1",
                        source_url="https://vk.com/example",
                        input_payload={"channel_name": "vkontakte", "risk_level": "High"},
                        output_payload={"allowed": False},
                        risk_blocked=True,
                        risk_block_reason="High 风险渠道只允许政策研究和人工小样本，不进入自动任务。",
                        executed_at=now - timedelta(minutes=2),
                    ),
                    AIAuditLog(
                        task_type=AITaskType.LEAD_GRADING,
                        model_name=TEST_MODEL,
                        prompt_version="grade-v1",
                        source_url="https://example.com/grade",
                        input_payload={"channel_name": "official_website"},
                        output_payload={"grade": "B"},
                        risk_blocked=False,
                        executed_at=now - timedelta(minutes=1),
                    ),
                ]
            )

        await async_session.run_sync(add)
        await async_session.commit()


@pytest.fixture(autouse=True)
def isolated_records():
    asyncio.run(cleanup_records())
    asyncio.run(seed_records())
    yield
    asyncio.run(cleanup_records())


def test_sync_ai_audit_dashboard_exposes_sync_counts_failures_and_ai_risk() -> None:
    client = TestClient(app)

    response = client.get(f"/sync/audit-dashboard?source_name={TEST_PREFIX}&model_name={TEST_MODEL}")

    assert response.status_code == 200
    payload = response.json()
    summary = payload["summary"]

    assert summary["latest_sync_at"]
    assert summary["sync_success_count"] == 10
    assert summary["sync_failure_count"] == 2
    assert summary["ai_task_count"] == 3
    assert summary["ai_blocked_count"] == 1

    failed_sync = next(item for item in payload["sync_logs"] if item["object_name"] == "渠道来源")
    assert failed_sync["status"] == "failed"
    assert failed_sync["failure_count"] == 2
    assert failed_sync["error_summary"] == "字段 渠道风险等级 缺失"

    blocked = next(item for item in payload["ai_audit_logs"] if item["risk_blocked"] is True)
    assert blocked["task_type"] == "outreach_draft"
    assert blocked["status"] == "blocked"
    assert blocked["risk"] == "blocked"
    assert "High 风险渠道" in blocked["risk_block_reason"]


def test_sync_ai_audit_dashboard_filters_by_task_type_and_status() -> None:
    client = TestClient(app)

    response = client.get(
        f"/sync/audit-dashboard?source_name={TEST_PREFIX}&model_name={TEST_MODEL}&task_type=outreach_draft&status=blocked"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["ai_task_count"] == 1
    assert payload["summary"]["ai_blocked_count"] == 1
    assert len(payload["ai_audit_logs"]) == 1
    assert payload["ai_audit_logs"][0]["task_type"] == "outreach_draft"
    assert payload["ai_audit_logs"][0]["status"] == "blocked"
