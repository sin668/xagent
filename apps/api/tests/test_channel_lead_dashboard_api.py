import asyncio
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.db.session import AsyncSessionLocal
from app.main import app
from app.models import ChannelRiskRule, Customer, LeadSource
from app.models.enums import ChannelRiskLevel, CustomerGrade, CustomerStatus, CustomerType, SourcePlatform


TEST_PREFIX = "TEST-E7S1-"


async def cleanup_records() -> None:
    async with AsyncSessionLocal() as async_session:
        customer_ids = (
            await async_session.execute(select(Customer.id).where(Customer.external_id.like(f"{TEST_PREFIX}%")))
        ).scalars().all()
        if customer_ids:
            await async_session.execute(delete(LeadSource).where(LeadSource.customer_id.in_(customer_ids)))
        await async_session.execute(delete(Customer).where(Customer.external_id.like(f"{TEST_PREFIX}%")))
        await async_session.execute(delete(ChannelRiskRule).where(ChannelRiskRule.external_id.like(f"{TEST_PREFIX}%")))
        await async_session.commit()


async def seed_dashboard_records() -> None:
    async with AsyncSessionLocal() as async_session:
        def add(sync_session):
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
                        external_id=f"{TEST_PREFIX}RULE-TELEGRAM",
                        channel_name="youtube",
                        channel_type="公开内容平台",
                        risk_level=ChannelRiskLevel.MEDIUM,
                        collection_allowed=True,
                        ai_processing_allowed=True,
                        allowed_actions="人工小样本；AI处理人工提供文本",
                        forbidden_actions="不得自动私信；不得自动加好友",
                        policy_source_url="https://example.com/youtube-policy",
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
                    ChannelRiskRule(
                        external_id=f"{TEST_PREFIX}RULE-FORBIDDEN",
                        channel_name="facebook",
                        channel_type="社交平台",
                        risk_level=ChannelRiskLevel.FORBIDDEN,
                        collection_allowed=False,
                        ai_processing_allowed=False,
                        allowed_actions="不进入自动化任务",
                        forbidden_actions="不得自动采集；不得自动触达",
                        policy_source_url="https://example.com/facebook-policy",
                    ),
                ]
            )

            now = datetime.utcnow()
            records = [
                ("001", SourcePlatform.OFFICIAL_WEBSITE, ChannelRiskLevel.LOW, CustomerGrade.B, now),
                ("002", SourcePlatform.OFFICIAL_WEBSITE, ChannelRiskLevel.LOW, CustomerGrade.C, now),
                ("003", SourcePlatform.OFFICIAL_WEBSITE, ChannelRiskLevel.LOW, CustomerGrade.INVALID, now),
                ("004", SourcePlatform.YOUTUBE, ChannelRiskLevel.MEDIUM, CustomerGrade.C, now),
                ("005", SourcePlatform.YOUTUBE, ChannelRiskLevel.MEDIUM, CustomerGrade.WATCH, now),
                ("OLD", SourcePlatform.OFFICIAL_WEBSITE, ChannelRiskLevel.LOW, CustomerGrade.B, now - timedelta(days=20)),
            ]

            for suffix, platform, risk_level, grade, collected_at in records:
                customer = Customer(
                    external_id=f"{TEST_PREFIX}{suffix}",
                    name=f"{TEST_PREFIX}{suffix} Dealer",
                    country="Russia",
                    city="Moscow",
                    customer_type=CustomerType.LOCAL_DEALER_SECONDARY_DEALER,
                    grade=grade,
                    status=CustomerStatus.PENDING_REVIEW,
                )
                sync_session.add(customer)
                sync_session.flush()
                sync_session.add(
                    LeadSource(
                        external_id=f"{TEST_PREFIX}SRC-{suffix}",
                        customer_id=customer.id,
                        platform=platform,
                        source_url=f"https://example.com/{suffix}",
                        source_title=f"Source {suffix}",
                        evidence_note="公开来源证据",
                        channel_risk_level=risk_level,
                        collected_at=collected_at,
                    )
                )

        await async_session.run_sync(add)
        await async_session.commit()


@pytest.fixture(autouse=True)
def isolated_dashboard_records():
    asyncio.run(cleanup_records())
    asyncio.run(seed_dashboard_records())
    yield
    asyncio.run(cleanup_records())


def test_channel_lead_dashboard_counts_bc_invalid_rate_and_date_filter() -> None:
    client = TestClient(app)
    date_from = (datetime.utcnow() - timedelta(days=2)).date().isoformat()

    response = client.get(f"/dashboard/channel-leads?date_from={date_from}")

    assert response.status_code == 200
    payload = response.json()
    official = next(item for item in payload["channels"] if item["channel_name"] == "official_website")

    assert official["candidate_count"] == 3
    assert official["b_grade_count"] == 1
    assert official["c_grade_count"] == 1
    assert official["bc_grade_count"] == 2
    assert official["invalid_count"] == 1
    assert official["invalid_rate"] == pytest.approx(1 / 3)
    assert official["risk_level"] == "Low"
    assert official["risk_status"] == "active"
    assert official["investment_recommendation"] == "candidate"

    assert payload["summary"]["candidate_count"] == 5
    assert payload["summary"]["bc_grade_count"] == 3
    assert payload["summary"]["invalid_rate"] == pytest.approx(2 / 5)


def test_channel_lead_dashboard_marks_high_and_forbidden_as_not_investable() -> None:
    client = TestClient(app)

    response = client.get("/dashboard/channel-leads")

    assert response.status_code == 200
    channels = {item["channel_name"]: item for item in response.json()["channels"]}

    assert channels["vkontakte"]["candidate_count"] == 0
    assert channels["vkontakte"]["risk_level"] == "High"
    assert channels["vkontakte"]["risk_status"] == "researching"
    assert channels["vkontakte"]["investment_recommendation"] == "blocked"

    assert channels["facebook"]["risk_level"] == "Forbidden"
    assert channels["facebook"]["risk_status"] == "blocked"
    assert channels["facebook"]["investment_recommendation"] == "blocked"
