import asyncio
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.db.session import AsyncSessionLocal
from app.main import app
from app.models import AIAuditLog, ChannelRiskRule, Customer, LeadSource, OutreachRecord
from app.models.enums import (
    AITaskType,
    ChannelRiskLevel,
    ContactMethodType,
    CustomerGrade,
    CustomerStatus,
    CustomerType,
    OutreachStatus,
    SourcePlatform,
)


TEST_PREFIX = "TEST-E8S1-"


async def cleanup_records() -> None:
    async with AsyncSessionLocal() as async_session:
        customer_ids = (
            await async_session.execute(select(Customer.id).where(Customer.external_id.like(f"{TEST_PREFIX}%")))
        ).scalars().all()
        if customer_ids:
            await async_session.execute(delete(AIAuditLog).where(AIAuditLog.customer_id.in_(customer_ids)))
            await async_session.execute(delete(OutreachRecord).where(OutreachRecord.customer_id.in_(customer_ids)))
            await async_session.execute(delete(LeadSource).where(LeadSource.customer_id.in_(customer_ids)))
        await async_session.execute(delete(AIAuditLog).where(AIAuditLog.model_name.like(f"{TEST_PREFIX}%")))
        await async_session.execute(delete(Customer).where(Customer.external_id.like(f"{TEST_PREFIX}%")))
        await async_session.execute(delete(ChannelRiskRule).where(ChannelRiskRule.external_id.like(f"{TEST_PREFIX}%")))
        await async_session.commit()


async def seed_admin_overview_records() -> None:
    async with AsyncSessionLocal() as async_session:
        def add(sync_session):
            now = datetime.utcnow()
            sync_session.add_all(
                [
                    ChannelRiskRule(
                        external_id=f"{TEST_PREFIX}RULE-OFFICIAL",
                        channel_name="official_website",
                        channel_type="官网",
                        risk_level=ChannelRiskLevel.LOW,
                        collection_allowed=True,
                        ai_processing_allowed=True,
                        allowed_actions="人工查看公开页面；AI处理人工提供文本",
                        forbidden_actions="不得高频访问；不得自动表单轰炸",
                        policy_source_url="https://example.com/official-policy",
                    ),
                    ChannelRiskRule(
                        external_id=f"{TEST_PREFIX}RULE-VK",
                        channel_name="vkontakte",
                        channel_type="社交平台",
                        risk_level=ChannelRiskLevel.HIGH,
                        collection_allowed=False,
                        ai_processing_allowed=False,
                        allowed_actions="政策研究；人工小样本",
                        forbidden_actions="不得登录后批量采集；不得自动私信",
                        policy_source_url="https://example.com/vk-policy",
                    ),
                ]
            )

            def customer(suffix, grade, status, owner, *, do_not_contact=False, hours_old=1):
                item = Customer(
                    external_id=f"{TEST_PREFIX}{suffix}",
                    name=f"{TEST_PREFIX}{suffix} Dealer",
                    country="Russia",
                    city="Moscow",
                    customer_type=CustomerType.LOCAL_DEALER_SECONDARY_DEALER,
                    grade=grade,
                    status=status,
                    owner=owner,
                    do_not_contact=do_not_contact,
                    updated_at=now - timedelta(hours=hours_old),
                )
                sync_session.add(item)
                sync_session.flush()
                sync_session.add(
                    LeadSource(
                        external_id=f"{TEST_PREFIX}SRC-{suffix}",
                        customer_id=item.id,
                        platform=SourcePlatform.OFFICIAL_WEBSITE,
                        source_url=f"https://example.com/{suffix}",
                        source_title=f"Source {suffix}",
                        evidence_note="公开来源证据",
                        channel_risk_level=ChannelRiskLevel.LOW,
                        collected_at=now,
                    )
                )
                return item

            operations = customer("OPS", CustomerGrade.B, CustomerStatus.PENDING_REVIEW, "Ops Anna")
            service = customer("CS", CustomerGrade.B, CustomerStatus.READY_FOR_CUSTOMER_SERVICE, "CS Boris")
            sales = customer("SALES", CustomerGrade.C, CustomerStatus.READY_FOR_SALES, "Sales Chen", hours_old=30)
            customer("DNC", CustomerGrade.B, CustomerStatus.DO_NOT_CONTACT, "CS Boris", do_not_contact=True)

            sync_session.add_all(
                [
                    OutreachRecord(
                        external_id=f"{TEST_PREFIX}OUT-SENT",
                        customer_id=service.id,
                        channel=ContactMethodType.EMAIL,
                        status=OutreachStatus.SENT,
                        owner="CS Boris",
                        sent_by="CS Boris",
                        sent_at=now - timedelta(hours=8),
                    ),
                    OutreachRecord(
                        external_id=f"{TEST_PREFIX}OUT-REPLIED",
                        customer_id=sales.id,
                        channel=ContactMethodType.EMAIL,
                        status=OutreachStatus.REPLIED,
                        owner="Sales Chen",
                        sent_by="Sales Chen",
                        sent_at=now - timedelta(hours=3),
                    ),
                    AIAuditLog(
                        customer_id=operations.id,
                        task_type=AITaskType.RISK_BLOCK,
                        model_name=f"{TEST_PREFIX}risk-model",
                        prompt_version="risk-v1",
                        source_url="https://vk.com/example",
                        input_payload={"channel": "vkontakte"},
                        output_payload={"action": "blocked"},
                        risk_blocked=True,
                        risk_block_reason="High 风险社媒禁止进入自动化触达。",
                        executed_at=now,
                    ),
                ]
            )

        await async_session.run_sync(add)
        await async_session.commit()


@pytest.fixture(autouse=True)
def isolated_admin_overview_records():
    asyncio.run(cleanup_records())
    asyncio.run(seed_admin_overview_records())
    yield
    asyncio.run(cleanup_records())


def test_admin_overview_exposes_global_metrics_queues_and_blocked_reasons() -> None:
    client = TestClient(app)

    response = client.get("/dashboard/admin-overview")

    assert response.status_code == 200
    payload = response.json()

    assert payload["summary"]["candidate_count"] == 4
    assert payload["summary"]["b_grade_count"] == 3
    assert payload["summary"]["c_grade_count"] == 1
    assert payload["summary"]["bc_grade_count"] == 4
    assert payload["summary"]["response_rate"] == pytest.approx(0.5)
    assert payload["summary"]["sla_risk_count"] >= 1

    queues = payload["team_queues"]
    assert queues["operations"]["count"] == 1
    assert queues["customer_service"]["count"] == 1
    assert queues["sales"]["count"] == 1
    assert all(item["customer_name"] != f"{TEST_PREFIX}DNC Dealer" for queue in queues.values() for item in queue["items"])

    risk_events = payload["risk_events"]
    assert len(risk_events) == 1
    assert risk_events[0]["task_type"] == "risk_block"
    assert risk_events[0]["risk_blocked"] is True
    assert "High 风险社媒" in risk_events[0]["risk_block_reason"]

    assert len(payload["blocked_tasks"]) == 1
    assert payload["blocked_tasks"][0]["risk_block_reason"] == "High 风险社媒禁止进入自动化触达。"

    blocked_channel = next(item for item in payload["channel_outputs"] if item["channel_name"] == "vkontakte")
    assert blocked_channel["risk_status"] == "researching"
    assert blocked_channel["investment_recommendation"] == "blocked"
