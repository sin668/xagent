import asyncio

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.db.session import AsyncSessionLocal
from app.main import app
from app.models import AIAuditLog, ChannelRiskRule


TEST_PREFIX = "TEST-E8S2-"
TEST_MODEL = "test-admin-risk-config"


async def cleanup_records() -> None:
    async with AsyncSessionLocal() as async_session:
        await async_session.execute(delete(AIAuditLog).where(AIAuditLog.model_name == TEST_MODEL))
        await async_session.execute(delete(ChannelRiskRule).where(ChannelRiskRule.channel_name.like(f"{TEST_PREFIX}%")))
        await async_session.commit()


@pytest.fixture(autouse=True)
def isolated_records():
    asyncio.run(cleanup_records())
    yield
    asyncio.run(cleanup_records())


def test_admin_channel_risk_config_records_operator_time_and_editable_policy_fields() -> None:
    client = TestClient(app)

    response = client.put(
        f"/channel-risks/{TEST_PREFIX}Official",
        json={
            "channel_type": "官网",
            "risk_level": "Low",
            "allowed_actions": "人工查看公开页面；AI 处理人工提供文本",
            "forbidden_actions": "自动表单轰炸；高频访问",
            "policy_source_url": "https://example.com/terms",
            "notes": "后台配置测试",
            "external_id": f"{TEST_PREFIX}RULE-001",
            "collection_allowed": True,
            "updated_by": "Compliance Anna",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["channel_name"] == f"{TEST_PREFIX}Official"
    assert payload["allowed_actions"] == "人工查看公开页面；AI 处理人工提供文本"
    assert payload["forbidden_actions"] == "自动表单轰炸；高频访问"
    assert payload["policy_source_url"] == "https://example.com/terms"
    assert payload["updated_by"] == "Compliance Anna"
    assert payload["updated_at"]


def test_forbidden_channel_cannot_be_made_collectable_by_frontend_payload() -> None:
    client = TestClient(app)

    response = client.put(
        f"/channel-risks/{TEST_PREFIX}Forbidden",
        json={
            "channel_type": "社交平台",
            "risk_level": "Forbidden",
            "allowed_actions": "无",
            "forbidden_actions": "所有动作；自动采集；自动私信；登录后批量采集",
            "policy_source_url": "https://example.com/forbidden-policy",
            "notes": "前端绕过测试",
            "external_id": f"{TEST_PREFIX}RULE-002",
            "collection_allowed": True,
            "updated_by": "Compliance Boris",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["risk_level"] == "Forbidden"
    assert payload["collection_allowed"] is False
    assert payload["ai_processing_allowed"] is False
    assert payload["updated_by"] == "Compliance Boris"

    decision_response = client.post(
        "/channel-risks/evaluate-ai-task",
        json={
            "channel_name": f"{TEST_PREFIX}Forbidden",
            "task_type": "lead_extraction",
            "requested_action": "AI 自动采集",
            "source_url": "https://example.com/blocked",
            "model_name": TEST_MODEL,
            "prompt_version": "admin-risk-config-test",
        },
    )
    decision = decision_response.json()
    assert decision_response.status_code == 200
    assert decision["allowed"] is False
    assert decision["risk_level"] == "Forbidden"
    assert decision["block_reason"]
