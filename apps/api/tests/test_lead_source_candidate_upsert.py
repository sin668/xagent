import asyncio
from uuid import uuid4

import pytest
from sqlalchemy import delete, select

from app.db.session import AsyncSessionLocal
from app.models.agent_task_run import AgentTaskRun
from app.models.enums import (
    AgentTaskRunStatus,
    AgentTaskType,
    ChannelRiskLevel,
    LeadSourceCandidateExtractionStatus,
    LeadSourceCandidateReviewStatus,
    SourcePlatform,
)
from app.models.lead_source_candidate import LeadSourceCandidate
from app.services.lead_source_candidates import LeadSourceCandidateService


TEST_PREFIX = "p2e3s2"


def candidate_payload(*, domain: str, path: str = "/dealers", risk_level: str = "Low") -> dict:
    return {
        "source_url": f"https://{domain}{path}",
        "platform": "official_website",
        "channel_name": "dealer_directory",
        "country": "Russia",
        "city": "Moscow",
        "risk_level": risk_level,
        "discovery_method": "keyword_search",
        "discovery_query": "автосалон импорт авто Москва",
        "discovery_reason": "公开页面展示车辆经销商目录。",
        "evidence_note": "公开页面包含 dealer、auto sales 和 contact 相关信息。",
        "evidence_links": [f"https://{domain}{path}"],
        "confidence_score": 0.72,
    }


async def cleanup_records(domain_prefix: str = TEST_PREFIX) -> None:
    async with AsyncSessionLocal() as async_session:
        await async_session.execute(
            delete(LeadSourceCandidate).where(LeadSourceCandidate.normalized_domain.like(f"{domain_prefix}%"))
        )
        await async_session.execute(delete(AgentTaskRun).where(AgentTaskRun.trigger_source.like(f"{domain_prefix}%")))
        await async_session.commit()


async def create_task_run(trigger_source: str) -> str:
    async with AsyncSessionLocal() as async_session:
        def add(sync_session):
            task = AgentTaskRun(
                task_type=AgentTaskType.SOURCE_DISCOVERY,
                status=AgentTaskRunStatus.SUCCEEDED,
                trigger_source=trigger_source,
                input_json={"country": "Russia"},
                llm_provider="deepseek",
                llm_model="deepseek-chat",
                prompt_version="v1.0",
            )
            sync_session.add(task)
            sync_session.flush()
            return str(task.id)

        task_id = await async_session.run_sync(add)
        await async_session.commit()
        return task_id


@pytest.fixture(autouse=True)
def cleanup_after_test():
    asyncio.run(cleanup_records())
    yield
    asyncio.run(cleanup_records())


@pytest.mark.parametrize(
    ("risk_level", "expected_review_status", "expected_approved", "expected_extraction_status"),
    [
        ("Low", LeadSourceCandidateReviewStatus.AUTO_APPROVED, True, LeadSourceCandidateExtractionStatus.PENDING),
        ("Medium", LeadSourceCandidateReviewStatus.AUTO_APPROVED, True, LeadSourceCandidateExtractionStatus.PENDING),
        ("High", LeadSourceCandidateReviewStatus.HIGH_RISK_REVIEW, False, LeadSourceCandidateExtractionStatus.PENDING),
        ("Forbidden", LeadSourceCandidateReviewStatus.REJECTED, False, LeadSourceCandidateExtractionStatus.BLOCKED),
    ],
)
@pytest.mark.asyncio
async def test_upsert_candidate_applies_risk_defaults(
    risk_level: str,
    expected_review_status: LeadSourceCandidateReviewStatus,
    expected_approved: bool,
    expected_extraction_status: LeadSourceCandidateExtractionStatus,
) -> None:
    suffix = uuid4().hex[:8]
    domain = f"{TEST_PREFIX}-{risk_level.lower()}-{suffix}.example.com"
    task_id = await create_task_run(f"{TEST_PREFIX}-{suffix}")

    async with AsyncSessionLocal() as async_session:
        def run(sync_session):
            return LeadSourceCandidateService(sync_session).upsert_candidate(
                candidate_payload(domain=domain, risk_level=risk_level),
                created_by_task_run_id=task_id,
                llm_provider="deepseek",
                llm_model="deepseek-chat",
                llm_output_json={"task_type": "SOURCE_DISCOVERY", "risk": risk_level},
            )

        result = await async_session.run_sync(run)
        await async_session.commit()

    assert result.created is True
    assert result.candidate.review_status == expected_review_status
    assert result.candidate.approved_for_extraction is expected_approved
    assert result.candidate.extraction_status == expected_extraction_status
    assert str(result.candidate.created_by_task_run_id) == task_id
    assert result.candidate.llm_output_json == {"task_type": "SOURCE_DISCOVERY", "risk": risk_level}
    assert result.candidate.evidence_links == [f"https://{domain}/dealers"]


@pytest.mark.asyncio
async def test_same_source_url_is_idempotent_upsert_not_duplicate_insert() -> None:
    suffix = uuid4().hex[:8]
    domain = f"{TEST_PREFIX}-same-{suffix}.example.com"

    async with AsyncSessionLocal() as async_session:
        def run(sync_session):
            service = LeadSourceCandidateService(sync_session)
            first = service.upsert_candidate(candidate_payload(domain=domain, risk_level="Low"))
            second_payload = candidate_payload(domain=domain, risk_level="Medium")
            second_payload["evidence_note"] = "更新后的证据说明。"
            second = service.upsert_candidate(second_payload)
            sync_session.flush()
            count = len(
                sync_session.scalars(
                    select(LeadSourceCandidate).where(LeadSourceCandidate.normalized_domain == domain)
                ).all()
            )
            return first, second, count

        first, second, count = await async_session.run_sync(run)
        await async_session.commit()

    assert first.created is True
    assert second.created is False
    assert first.candidate.id == second.candidate.id
    assert second.candidate.is_duplicate is False
    assert second.candidate.duplicate_of_id is None
    assert second.candidate.evidence_note == "更新后的证据说明。"
    assert count == 1


@pytest.mark.asyncio
async def test_same_domain_and_platform_different_url_is_marked_duplicate_without_deletion() -> None:
    suffix = uuid4().hex[:8]
    domain = f"{TEST_PREFIX}-domain-{suffix}.example.com"

    async with AsyncSessionLocal() as async_session:
        def run(sync_session):
            service = LeadSourceCandidateService(sync_session)
            first = service.upsert_candidate(candidate_payload(domain=domain, path="/dealers", risk_level="Low"))
            second = service.upsert_candidate(candidate_payload(domain=domain, path="/contacts", risk_level="Low"))
            sync_session.flush()
            rows = sync_session.scalars(
                select(LeadSourceCandidate)
                .where(LeadSourceCandidate.normalized_domain == domain)
                .order_by(LeadSourceCandidate.created_at)
            ).all()
            return first, second, rows

        first, second, rows = await async_session.run_sync(run)
        await async_session.commit()

    assert first.created is True
    assert second.created is True
    assert second.candidate.is_duplicate is True
    assert second.candidate.duplicate_of_id == first.candidate.id
    assert len(rows) == 2


@pytest.mark.asyncio
async def test_upsert_from_source_discovery_output_persists_candidates_and_blocked_candidates() -> None:
    suffix = uuid4().hex[:8]
    domain = f"{TEST_PREFIX}-batch-{suffix}.example.com"

    source_discovery_output = {
        "task_type": "SOURCE_DISCOVERY",
        "country": "Russia",
        "city": "Moscow",
        "channel_strategy": "official_website_public_directory_search_engine",
        "candidates": [candidate_payload(domain=domain, path="/dealers", risk_level="Low")],
        "blocked_candidates": [
            {
                "source_url": f"https://{domain}/private",
                "platform": "official_website",
                "risk_level": "Forbidden",
                "blocked_reason": "需要登录。",
            }
        ],
    }

    async with AsyncSessionLocal() as async_session:
        def run(sync_session):
            result = LeadSourceCandidateService(sync_session).upsert_from_source_discovery_output(
                source_discovery_output,
                llm_output_json=source_discovery_output,
                llm_provider="deepseek",
                llm_model="deepseek-chat",
            )
            sync_session.flush()
            return result

        result = await async_session.run_sync(run)
        await async_session.commit()

    assert result.created_count == 2
    assert result.updated_count == 0
    assert result.duplicate_count == 1
    assert len(result.items) == 2
    blocked = next(item.candidate for item in result.items if item.candidate.risk_level == ChannelRiskLevel.FORBIDDEN)
    assert blocked.review_status == LeadSourceCandidateReviewStatus.REJECTED
    assert blocked.approved_for_extraction is False
    assert blocked.extraction_status == LeadSourceCandidateExtractionStatus.BLOCKED
    assert blocked.evidence_links == [f"https://{domain}/private"]
