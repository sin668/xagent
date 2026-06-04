import pytest
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.enums import LLMPromptTaskType, LLMPromptTemplateStatus
from app.models.llm_prompt_template import LLMPromptTemplate
from app.services.default_prompt_seed import (
    SOURCE_DISCOVERY_DEFAULT_NAME,
    SOURCE_DISCOVERY_DEFAULT_VERSION,
    SourceDiscoveryDefaultPromptSeed,
)


def test_source_discovery_default_prompt_payload_contract() -> None:
    payload = SourceDiscoveryDefaultPromptSeed.build_payload(provider="deepseek", model="deepseek-chat")

    assert payload["name"] == SOURCE_DISCOVERY_DEFAULT_NAME
    assert payload["task_type"] == LLMPromptTaskType.SOURCE_DISCOVERY
    assert payload["version"] == SOURCE_DISCOVERY_DEFAULT_VERSION
    assert payload["status"] == LLMPromptTemplateStatus.ACTIVE
    assert payload["is_default"] is True
    assert payload["provider"] == "deepseek"
    assert payload["model"] == "deepseek-chat"


def test_source_discovery_default_prompt_contains_compliance_boundaries() -> None:
    payload = SourceDiscoveryDefaultPromptSeed.build_payload(provider="deepseek", model="deepseek-chat")
    prompt_text = f"{payload['system_prompt']}\n{payload['user_prompt_template']}"

    for required_boundary in (
        "不抽取客户",
        "不自动触达",
        "不生成私信",
        "不绕过登录",
        "不绕过验证码",
        "不绕过反爬",
        "不绕过平台限制",
        "High",
        "Forbidden",
    ):
        assert required_boundary in prompt_text


def test_source_discovery_output_schema_requires_candidates_and_blocked_candidates() -> None:
    payload = SourceDiscoveryDefaultPromptSeed.build_payload(provider="deepseek", model="deepseek-chat")
    schema = payload["output_schema_json"]

    assert schema["type"] == "object"
    assert "candidates" in schema["required"]
    assert "blocked_candidates" in schema["required"]

    candidate_schema = schema["properties"]["candidates"]["items"]
    assert candidate_schema["type"] == "object"
    for field_name in (
        "source_url",
        "platform",
        "risk_level",
        "discovery_reason",
        "evidence_note",
    ):
        assert field_name in candidate_schema["required"]


@pytest.mark.asyncio
async def test_seed_source_discovery_default_prompt_is_persisted_and_idempotent() -> None:
    async with AsyncSessionLocal() as async_session:
        def run(sync_session):
            first = SourceDiscoveryDefaultPromptSeed.seed(sync_session, provider="deepseek", model="deepseek-chat")
            second = SourceDiscoveryDefaultPromptSeed.seed(sync_session, provider="deepseek", model="deepseek-chat")
            sync_session.flush()

            persisted = sync_session.scalar(
                select(LLMPromptTemplate).where(
                    LLMPromptTemplate.task_type == LLMPromptTaskType.SOURCE_DISCOVERY,
                    LLMPromptTemplate.status == LLMPromptTemplateStatus.ACTIVE,
                    LLMPromptTemplate.is_default.is_(True),
                )
            )
            active_default_count = len(
                sync_session.scalars(
                    select(LLMPromptTemplate).where(
                        LLMPromptTemplate.task_type == LLMPromptTaskType.SOURCE_DISCOVERY,
                        LLMPromptTemplate.status == LLMPromptTemplateStatus.ACTIVE,
                        LLMPromptTemplate.is_default.is_(True),
                    )
                ).all()
            )
            return first, second, persisted, active_default_count

        first, second, persisted, active_default_count = await async_session.run_sync(run)
        await async_session.commit()

    assert first.id == second.id
    assert persisted is not None
    assert persisted.name == SOURCE_DISCOVERY_DEFAULT_NAME
    assert persisted.version == SOURCE_DISCOVERY_DEFAULT_VERSION
    assert persisted.output_schema_json["properties"]["candidates"]["type"] == "array"
    assert active_default_count == 1
