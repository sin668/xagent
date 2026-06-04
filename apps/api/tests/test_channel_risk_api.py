import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select

from app.db.session import AsyncSessionLocal
from app.main import app
from app.models import AIAuditLog, ChannelRiskRule


TEST_PREFIX = "TEST-E6S1-API-"
TEST_MODEL = "test-risk-api"


async def cleanup_test_records() -> None:
    async with AsyncSessionLocal() as async_session:
        await async_session.execute(delete(AIAuditLog).where(AIAuditLog.model_name == TEST_MODEL))
        await async_session.execute(delete(ChannelRiskRule).where(ChannelRiskRule.channel_name.like(f"{TEST_PREFIX}%")))
        await async_session.commit()


async def count_test_audit_logs() -> int:
    async with AsyncSessionLocal() as async_session:
        return int(
            await async_session.scalar(
                select(func.count()).select_from(AIAuditLog).where(AIAuditLog.model_name == TEST_MODEL)
            )
            or 0
        )


@pytest.fixture(autouse=True)
def isolated_api_records():
    import asyncio

    asyncio.run(cleanup_test_records())
    yield
    asyncio.run(cleanup_test_records())


def test_channel_risk_api_can_create_and_list_rules() -> None:
    client = TestClient(app)
    response = client.put(
        f"/channel-risks/{TEST_PREFIX}Website",
        json={
            "channel_type": "公开网页",
            "risk_level": "Low",
            "allowed_actions": "人工查看公开页面；AI 处理人工提供的公开文本",
            "forbidden_actions": "自动表单轰炸；高频访问；登录后采集",
            "policy_source_url": "https://example.com/terms",
            "notes": "官网 Low 风险",
            "external_id": f"{TEST_PREFIX}CH-001",
            "collection_allowed": True,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["channel_name"] == f"{TEST_PREFIX}Website"
    assert payload["risk_level"] == "Low"
    assert payload["ai_processing_allowed"] is True
    assert payload["policy_source_url"] == "https://example.com/terms"

    list_response = client.get("/channel-risks")
    assert list_response.status_code == 200
    names = {item["channel_name"] for item in list_response.json()["items"]}
    assert f"{TEST_PREFIX}Website" in names


def test_channel_risk_api_blocks_high_and_forbidden_ai_task_selection() -> None:
    import asyncio

    client = TestClient(app)
    for channel_name, risk_level in [(f"{TEST_PREFIX}VK", "High"), (f"{TEST_PREFIX}Forbidden", "Forbidden")]:
        create_response = client.put(
            f"/channel-risks/{channel_name}",
            json={
                "channel_type": "公开社媒",
                "risk_level": risk_level,
                "allowed_actions": "政策研究；人工小样本",
                "forbidden_actions": "自动私信；自动加好友；登录后批量采集",
                "policy_source_url": "https://example.com/policy",
                "notes": "后端阻断测试",
                "external_id": f"{TEST_PREFIX}{risk_level}",
            },
        )
        assert create_response.status_code == 200

        decision_response = client.post(
            "/channel-risks/evaluate-ai-task",
            json={
                "channel_name": channel_name,
                "task_type": "lead_extraction",
                "requested_action": "AI 自动采集",
                "source_url": "https://example.com/source",
                "model_name": TEST_MODEL,
                "prompt_version": "risk-api-test",
            },
        )
        assert decision_response.status_code == 200
        decision = decision_response.json()
        assert decision["allowed"] is False
        assert decision["risk_level"] == risk_level
        assert decision["audit_logged"] is True

    assert asyncio.run(count_test_audit_logs()) == 2


def test_channel_risk_api_allows_medium_ai_task_selection_without_block_audit() -> None:
    client = TestClient(app)
    create_response = client.put(
        f"/channel-risks/{TEST_PREFIX}Maps",
        json={
            "channel_type": "地图标注",
            "risk_level": "Medium",
            "allowed_actions": "人工小规模核验；AI 处理人工提供的公开文本",
            "forbidden_actions": "批量抓取地图内容；离线复制地图内容",
            "policy_source_url": "https://example.com/maps-policy",
            "notes": "Medium 可处理人工提供文本",
            "external_id": f"{TEST_PREFIX}CH-002",
        },
    )
    assert create_response.status_code == 200

    decision_response = client.post(
        "/channel-risks/evaluate-ai-task",
        json={
            "channel_name": f"{TEST_PREFIX}Maps",
            "task_type": "lead_extraction",
            "requested_action": "AI 处理人工提供的公开文本",
            "source_url": "https://example.com/maps",
            "model_name": TEST_MODEL,
            "prompt_version": "risk-api-test",
        },
    )

    assert decision_response.status_code == 200
    decision = decision_response.json()
    assert decision["allowed"] is True
    assert decision["risk_level"] == "Medium"
    assert decision["audit_logged"] is False
