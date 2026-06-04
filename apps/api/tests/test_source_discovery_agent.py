import asyncio
from uuid import uuid4

import pytest
from sqlalchemy import delete, select

from app.db.session import AsyncSessionLocal
from app.models.agent_task_run import AgentTaskRun
from app.models.enums import AgentTaskRunStatus, AgentTaskType, LLMPromptTaskType, LLMPromptTemplateStatus
from app.models.lead_source_candidate import LeadSourceCandidate
from app.models.llm_prompt_template import LLMPromptTemplate
from app.services.default_prompt_seed import SourceDiscoveryDefaultPromptSeed
from app.services.llm_client import LLMClientResult
from app.services.source_discovery_agent import SourceDiscoveryAgentRequest, SourceDiscoveryAgentService


TEST_PREFIX = "p2e3s3"


def discovery_output(domain: str) -> dict:
    return {
        "task_type": "SOURCE_DISCOVERY",
        "country": "Russia",
        "city": "Moscow",
        "channel_strategy": "official_website_public_directory_search_engine",
        "candidates": [
            {
                "source_url": f"https://{domain}/dealers",
                "platform": "official_website",
                "channel_name": "dealer_directory",
                "country": "Russia",
                "city": "Moscow",
                "risk_level": "Low",
                "discovery_method": "keyword_search",
                "discovery_query": "автосалон импорт авто Москва",
                "discovery_reason": "公开页面展示车辆经销商目录。",
                "evidence_note": "公开页面包含 dealer、auto sales 和 contact 相关信息。",
                "evidence_links": [f"https://{domain}/dealers"],
                "confidence_score": 0.72,
                "recommended_review_status": "auto_approved",
                "approved_for_extraction": True,
            }
        ],
        "blocked_candidates": [],
    }


class MockLLMClient:
    def __init__(self, result: LLMClientResult) -> None:
        self.result = result
        self.calls: list[dict] = []

    async def generate_json(self, task_type: str, system_prompt: str, user_prompt: str, output_schema: dict):
        self.calls.append(
            {
                "task_type": task_type,
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "output_schema": output_schema,
            }
        )
        return self.result


def llm_success(output_json: dict) -> LLMClientResult:
    return LLMClientResult(
        provider="deepseek",
        model="deepseek-chat",
        base_url="https://api.deepseek.com/v1",
        latency_ms=123,
        token_usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
        output_json=output_json,
        raw_response={"id": "mock-chat-completion"},
        error=None,
    )


def llm_error(error_type: str) -> LLMClientResult:
    return LLMClientResult(
        provider="deepseek",
        model="deepseek-chat",
        base_url="https://api.deepseek.com/v1",
        latency_ms=99,
        token_usage=None,
        output_json=None,
        raw_response=None,
        error={"type": error_type, "message": f"{error_type} happened"},
    )


async def cleanup_records() -> None:
    async with AsyncSessionLocal() as async_session:
        await async_session.execute(
            delete(LeadSourceCandidate).where(LeadSourceCandidate.normalized_domain.like(f"{TEST_PREFIX}%"))
        )
        await async_session.execute(delete(AgentTaskRun).where(AgentTaskRun.trigger_source.like(f"{TEST_PREFIX}%")))
        await async_session.commit()


async def seed_prompt() -> None:
    async with AsyncSessionLocal() as async_session:
        def run(sync_session):
            SourceDiscoveryDefaultPromptSeed.seed(sync_session, provider="deepseek", model="deepseek-chat")

        await async_session.run_sync(run)
        await async_session.commit()


@pytest.fixture(autouse=True)
def clean_database_records():
    asyncio.run(cleanup_records())
    asyncio.run(seed_prompt())
    yield
    asyncio.run(cleanup_records())


@pytest.mark.asyncio
async def test_source_discovery_agent_success_creates_candidates_and_succeeded_task() -> None:
    suffix = uuid4().hex[:8]
    domain = f"{TEST_PREFIX}-success-{suffix}.example.com"
    llm_client = MockLLMClient(llm_success(discovery_output(domain)))

    async with AsyncSessionLocal() as async_session:
        result = await SourceDiscoveryAgentService(async_session=async_session, llm_client=llm_client).run(
            SourceDiscoveryAgentRequest(
                country="Russia",
                city="Moscow",
                channel_strategy="official_website_public_directory_search_engine",
                keywords=["автосалон", "импорт авто"],
                max_candidates=20,
                trigger_source=f"{TEST_PREFIX}-manual-{suffix}",
            )
        )

    assert result.task_run.status == AgentTaskRunStatus.SUCCEEDED
    assert result.created_count == 1
    assert result.updated_count == 0
    assert result.duplicate_count == 0
    assert len(llm_client.calls) == 1
    assert llm_client.calls[0]["task_type"] == "SOURCE_DISCOVERY"
    assert "不抽取客户" in llm_client.calls[0]["system_prompt"]
    assert "автосалон" in llm_client.calls[0]["user_prompt"]

    async with AsyncSessionLocal() as verify_session:
        def verify(sync_session):
            task = sync_session.get(AgentTaskRun, result.task_run.id)
            candidate = sync_session.scalar(
                select(LeadSourceCandidate).where(LeadSourceCandidate.normalized_domain == domain)
            )
            template = sync_session.scalar(
                select(LLMPromptTemplate).where(
                    LLMPromptTemplate.task_type == LLMPromptTaskType.SOURCE_DISCOVERY,
                    LLMPromptTemplate.status == LLMPromptTemplateStatus.ACTIVE,
                    LLMPromptTemplate.is_default.is_(True),
                )
            )
            return task, candidate, template

        task, candidate, template = await verify_session.run_sync(verify)

    assert task.status == AgentTaskRunStatus.SUCCEEDED
    assert task.prompt_template_id == template.id
    assert task.prompt_version == "v1.0"
    assert task.llm_provider == "deepseek"
    assert task.llm_model == "deepseek-chat"
    assert task.token_usage_json == {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}
    assert task.latency_ms == 123
    assert task.output_summary_json["created_count"] == 1
    assert candidate.created_by_task_run_id == task.id
    assert candidate.llm_output_json == discovery_output(domain)


@pytest.mark.asyncio
async def test_source_discovery_agent_schema_failure_marks_manual_review_and_writes_no_candidates() -> None:
    suffix = uuid4().hex[:8]
    invalid_output = discovery_output(f"{TEST_PREFIX}-invalid-{suffix}.example.com")
    invalid_output["candidates"][0].pop("evidence_note")
    llm_client = MockLLMClient(llm_success(invalid_output))

    async with AsyncSessionLocal() as async_session:
        result = await SourceDiscoveryAgentService(async_session=async_session, llm_client=llm_client).run(
            SourceDiscoveryAgentRequest(
                country="Russia",
                city="Moscow",
                channel_strategy="official_website_public_directory_search_engine",
                keywords=["автосалон"],
                max_candidates=20,
                trigger_source=f"{TEST_PREFIX}-schema-{suffix}",
            )
        )

    assert result.task_run.status == AgentTaskRunStatus.MANUAL_REVIEW_REQUIRED
    assert result.created_count == 0
    assert result.error is not None
    assert result.error["type"] == "schema_validation_error"

    async with AsyncSessionLocal() as verify_session:
        def verify(sync_session):
            task = sync_session.get(AgentTaskRun, result.task_run.id)
            candidates = sync_session.scalars(
                select(LeadSourceCandidate).where(
                    LeadSourceCandidate.normalized_domain.like(f"{TEST_PREFIX}-invalid-{suffix}%")
                )
            ).all()
            return task, candidates

        task, candidates = await verify_session.run_sync(verify)

    assert task.status == AgentTaskRunStatus.MANUAL_REVIEW_REQUIRED
    assert "evidence_note" in task.error_message
    assert task.output_summary_json["error"]["type"] == "schema_validation_error"
    assert candidates == []


@pytest.mark.asyncio
async def test_source_discovery_agent_llm_error_marks_failed_without_upsert() -> None:
    suffix = uuid4().hex[:8]
    llm_client = MockLLMClient(llm_error("network_error"))

    async with AsyncSessionLocal() as async_session:
        result = await SourceDiscoveryAgentService(async_session=async_session, llm_client=llm_client).run(
            SourceDiscoveryAgentRequest(
                country="Russia",
                city="Moscow",
                channel_strategy="official_website_public_directory_search_engine",
                keywords=["автосалон"],
                max_candidates=20,
                trigger_source=f"{TEST_PREFIX}-failed-{suffix}",
            )
        )

    assert result.task_run.status == AgentTaskRunStatus.FAILED
    assert result.created_count == 0
    assert result.error == {"type": "network_error", "message": "network_error happened"}

    async with AsyncSessionLocal() as verify_session:
        def verify(sync_session):
            return sync_session.get(AgentTaskRun, result.task_run.id)

        task = await verify_session.run_sync(verify)

    assert task.status == AgentTaskRunStatus.FAILED
    assert "network_error happened" in task.error_message
    assert task.output_summary_json["error"]["type"] == "network_error"
