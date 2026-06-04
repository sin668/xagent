import pytest
import pytest_asyncio
from sqlalchemy import delete, func, select

from app.db.session import AsyncSessionLocal
from app.models import AIAuditLog, ChannelRiskRule
from app.models.enums import AITaskType, ChannelRiskLevel
from app.services.channel_risk import ChannelRiskService


TEST_PREFIX = "TEST-E6S1-"
TEST_MODEL = "test-risk-gate"


async def cleanup_test_records() -> None:
    async with AsyncSessionLocal() as async_session:
        await async_session.execute(delete(AIAuditLog).where(AIAuditLog.model_name == TEST_MODEL))
        await async_session.execute(delete(ChannelRiskRule).where(ChannelRiskRule.channel_name.like(f"{TEST_PREFIX}%")))
        await async_session.commit()


async def run_with_session(callback):
    async with AsyncSessionLocal() as async_session:
        result = await async_session.run_sync(callback)
        await async_session.commit()
        return result


@pytest_asyncio.fixture(autouse=True)
async def isolated_channel_risk_records():
    await cleanup_test_records()
    yield
    await cleanup_test_records()


@pytest.mark.asyncio
async def test_upsert_channel_risk_rule_persists_policy_actions_and_notes() -> None:
    def act(session):
        service = ChannelRiskService(session)
        rule = service.upsert_rule(
            channel_name=f"{TEST_PREFIX}Website",
            channel_type="公开网页",
            risk_level="Low",
            allowed_actions="人工查看公开页面；AI 处理人工提供的公开文本",
            forbidden_actions="自动表单轰炸；高频访问；登录后采集",
            policy_source_url="https://example.com/terms",
            notes="官网公开联系方式可作为 Low 风险来源",
            external_id=f"{TEST_PREFIX}CH-001",
            collection_allowed=True,
        )
        session.flush()
        persisted = session.scalar(select(ChannelRiskRule).where(ChannelRiskRule.channel_name == f"{TEST_PREFIX}Website"))
        return rule, persisted

    rule, persisted = await run_with_session(act)

    assert rule.risk_level == ChannelRiskLevel.LOW
    assert rule.ai_processing_allowed is True
    assert persisted is not None
    assert persisted.allowed_actions.startswith("人工查看公开页面")
    assert persisted.forbidden_actions.startswith("自动表单轰炸")
    assert persisted.policy_source_url == "https://example.com/terms"
    assert persisted.notes == "官网公开联系方式可作为 Low 风险来源"


@pytest.mark.asyncio
async def test_low_and_medium_rules_are_allowed_for_ai_task_selection() -> None:
    def act(session):
        service = ChannelRiskService(session)
        service.upsert_rule(
            channel_name=f"{TEST_PREFIX}Maps",
            channel_type="地图标注",
            risk_level="Medium",
            allowed_actions="人工小规模核验；AI 处理人工提供的公开文本",
            forbidden_actions="批量抓取地图内容；离线复制地图内容",
            policy_source_url="https://example.com/maps-policy",
            notes="地图渠道仅人工小样本",
            external_id=f"{TEST_PREFIX}CH-002",
        )
        decision = service.evaluate_ai_task(
            channel_name=f"{TEST_PREFIX}Maps",
            task_type=AITaskType.LEAD_EXTRACTION.value,
            requested_action="AI 处理人工提供的公开文本",
            source_url="https://maps.example.com/dealer",
            model_name=TEST_MODEL,
            prompt_version="risk-gate-test",
        )
        audit_count = session.scalar(select(func.count()).select_from(AIAuditLog).where(AIAuditLog.model_name == TEST_MODEL))
        return decision, audit_count

    decision, audit_count = await run_with_session(act)

    assert decision.allowed is True
    assert decision.risk_level == "Medium"
    assert decision.block_reason is None
    assert audit_count == 0


@pytest.mark.asyncio
async def test_high_risk_rule_blocks_ai_task_and_writes_audit_log() -> None:
    def act(session):
        service = ChannelRiskService(session)
        service.upsert_rule(
            channel_name=f"{TEST_PREFIX}VK",
            channel_type="公开社媒",
            risk_level="High",
            allowed_actions="政策研究；人工查看公开主页；优先记录官网",
            forbidden_actions="自动私信；自动加好友；登录后批量采集",
            policy_source_url="https://example.com/vk-policy",
            notes="High 风险渠道不进入自动任务",
            external_id=f"{TEST_PREFIX}CH-003",
        )
        decision = service.evaluate_ai_task(
            channel_name=f"{TEST_PREFIX}VK",
            task_type=AITaskType.LEAD_EXTRACTION.value,
            requested_action="AI 自动抽取公开主页内容",
            source_url="https://vk.example.com/dealer",
            model_name=TEST_MODEL,
            prompt_version="risk-gate-test",
        )
        audit = session.scalar(select(AIAuditLog).where(AIAuditLog.model_name == TEST_MODEL))
        return decision, audit

    decision, audit = await run_with_session(act)

    assert decision.allowed is False
    assert decision.risk_level == "High"
    assert "High 风险渠道" in (decision.block_reason or "")
    assert audit is not None
    assert audit.risk_blocked is True
    assert audit.task_type == AITaskType.LEAD_EXTRACTION
    assert audit.source_url == "https://vk.example.com/dealer"
    assert "High 风险渠道" in (audit.risk_block_reason or "")


@pytest.mark.asyncio
async def test_forbidden_rule_blocks_every_action_and_writes_audit_log() -> None:
    def act(session):
        service = ChannelRiskService(session)
        service.upsert_rule(
            channel_name=f"{TEST_PREFIX}ForbiddenScrape",
            channel_type="禁止行为",
            risk_level="Forbidden",
            allowed_actions="无",
            forbidden_actions="绕过反爬；盗用账号；抓取非公开数据",
            policy_source_url="https://example.com/forbidden",
            notes="禁止执行",
            external_id=f"{TEST_PREFIX}CH-004",
        )
        decision = service.evaluate_ai_task(
            channel_name=f"{TEST_PREFIX}ForbiddenScrape",
            task_type=AITaskType.LEAD_GRADING.value,
            requested_action="抓取非公开数据",
            source_url="https://forbidden.example.com",
            model_name=TEST_MODEL,
            prompt_version="risk-gate-test",
        )
        audit = session.scalar(select(AIAuditLog).where(AIAuditLog.model_name == TEST_MODEL))
        return decision, audit

    decision, audit = await run_with_session(act)

    assert decision.allowed is False
    assert decision.risk_level == "Forbidden"
    assert "Forbidden" in (decision.block_reason or "")
    assert audit is not None
    assert audit.risk_blocked is True


@pytest.mark.asyncio
async def test_requested_forbidden_action_blocks_even_on_low_risk_channel() -> None:
    def act(session):
        service = ChannelRiskService(session)
        service.upsert_rule(
            channel_name=f"{TEST_PREFIX}Directory",
            channel_type="公开目录",
            risk_level="Low",
            allowed_actions="人工查看公开目录；AI 处理人工提供的公开文本",
            forbidden_actions="批量抓取目录；采集非公开会员信息",
            policy_source_url="https://example.com/directory-policy",
            notes="公开目录 Low 风险，但禁止批量抓取",
            external_id=f"{TEST_PREFIX}CH-005",
        )
        decision = service.evaluate_ai_task(
            channel_name=f"{TEST_PREFIX}Directory",
            task_type=AITaskType.LEAD_EXTRACTION.value,
            requested_action="批量抓取目录",
            source_url="https://directory.example.com",
            model_name=TEST_MODEL,
            prompt_version="risk-gate-test",
        )
        audit = session.scalar(select(AIAuditLog).where(AIAuditLog.model_name == TEST_MODEL))
        return decision, audit

    decision, audit = await run_with_session(act)

    assert decision.allowed is False
    assert decision.risk_level == "Low"
    assert "禁止动作" in (decision.block_reason or "")
    assert audit is not None
    assert audit.risk_blocked is True
