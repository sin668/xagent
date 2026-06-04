import asyncio
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import delete, or_, select

from app.db.session import AsyncSessionLocal
from app.main import app
from app.models.agent_task_run import AgentTaskRun
from app.models.channel_plan import ChannelPlan
from app.models.enums import (
    AgentTaskRunStatus,
    AgentTaskType,
    ChannelPlanStatus,
    ChannelRiskLevel,
    LeadSourceCandidateExtractionStatus,
    LeadSourceCandidateReviewStatus,
    SourceUsageType,
)
from app.models.lead_source_candidate import LeadSourceCandidate
from app.services.lead_source_candidates import LeadSourceCandidateService


client = TestClient(app)
TEST_PREFIX = "p2e5s3"
TEST_COUNTRY = "Testland"
TEST_CITY = "Test City"
thread_starts: list[str] = []


class FakeThreadRunner:
    @classmethod
    def start(cls, *, name, target):
        thread_starts.append(name)
        return None


def candidate_payload(suffix: str, *, risk_level: str = "Low", channel_name: str = "dealer_directory") -> dict:
    return {
        "source_url": f"https://{TEST_PREFIX}-{suffix}.example.com/source",
        "platform": "official_website",
        "channel_name": channel_name,
        "country": TEST_COUNTRY,
        "city": TEST_CITY,
        "risk_level": risk_level,
        "discovery_method": "keyword_search",
        "discovery_query": "автосалон Москва",
        "discovery_reason": "公开来源页面展示车辆经销相关信息。",
        "evidence_note": "公开页面包含 dealer、auto sales 和 contact 信息。",
        "evidence_links": [f"https://{TEST_PREFIX}-{suffix}.example.com/source"],
        "confidence_score": 0.77,
    }


async def cleanup_records() -> None:
    async with AsyncSessionLocal() as async_session:
        await async_session.execute(
            delete(LeadSourceCandidate).where(
                or_(
                    LeadSourceCandidate.normalized_domain.like(f"{TEST_PREFIX}%"),
                    LeadSourceCandidate.source_url.like(f"%{TEST_PREFIX}%"),
                )
            )
        )
        await async_session.execute(delete(ChannelPlan).where(ChannelPlan.channel_name.like(f"{TEST_PREFIX}%")))
        await async_session.execute(delete(AgentTaskRun).where(AgentTaskRun.trigger_source.like(f"{TEST_PREFIX}%")))
        await async_session.execute(delete(AgentTaskRun).where(AgentTaskRun.trigger_source == "lead_extraction_source_selection_api"))
        await async_session.commit()


async def seed_candidate(
    *,
    risk_level: str = "Low",
    review_status: LeadSourceCandidateReviewStatus | None = None,
    approved_for_extraction: bool | None = None,
    extraction_status: LeadSourceCandidateExtractionStatus = LeadSourceCandidateExtractionStatus.PENDING,
    channel_name: str = "dealer_directory",
) -> str:
    suffix = uuid4().hex[:10]
    async with AsyncSessionLocal() as async_session:
        def run(sync_session):
            task = AgentTaskRun(
                task_type=AgentTaskType.SOURCE_DISCOVERY,
                status=AgentTaskRunStatus.SUCCEEDED,
                trigger_source=f"{TEST_PREFIX}-seed-{suffix}",
                input_json={"country": "Russia"},
                output_summary_json={"created_count": 1},
            )
            sync_session.add(task)
            sync_session.flush()
            candidate = LeadSourceCandidateService(sync_session).upsert_candidate(
                candidate_payload(suffix, risk_level=risk_level, channel_name=channel_name),
                created_by_task_run_id=task.id,
                llm_provider="deepseek",
                llm_model="deepseek-chat",
                llm_output_json={"task_type": "SOURCE_DISCOVERY", "candidates": [], "blocked_candidates": []},
            ).candidate
            if review_status is not None:
                candidate.review_status = review_status
            if approved_for_extraction is not None:
                candidate.approved_for_extraction = approved_for_extraction
            candidate.extraction_status = extraction_status
            sync_session.flush()
            return str(candidate.id)

        candidate_id = await async_session.run_sync(run)
        await async_session.commit()
        return candidate_id


async def seed_paused_channel_plan(channel_name: str) -> None:
    async with AsyncSessionLocal() as async_session:
        def run(sync_session):
            sync_session.add(
                ChannelPlan(
                    country=TEST_COUNTRY,
                    city=TEST_CITY,
                    channel_name=channel_name,
                    channel_type="official_website",
                    risk_level=ChannelRiskLevel.LOW,
                    source_usage_type=SourceUsageType.AUTOMATIC_COLLECTION,
                    keywords=["dealer"],
                    daily_url_limit=20,
                    daily_lead_limit=10,
                    status=ChannelPlanStatus.PAUSED,
                    owner="ops",
                )
            )

        await async_session.run_sync(run)
        await async_session.commit()


async def get_candidate(candidate_id: str) -> LeadSourceCandidate:
    async with AsyncSessionLocal() as async_session:
        def run(sync_session):
            return sync_session.get(LeadSourceCandidate, candidate_id)

        return await async_session.run_sync(run)


async def get_task(task_id: str) -> AgentTaskRun:
    async with AsyncSessionLocal() as async_session:
        def run(sync_session):
            return sync_session.get(AgentTaskRun, task_id)

        return await async_session.run_sync(run)


def setup_function():
    thread_starts.clear()
    import app.api.lead_extraction_from_sources as lead_extraction_api

    lead_extraction_api.AgentThreadRunner = FakeThreadRunner
    asyncio.run(cleanup_records())


def teardown_function():
    asyncio.run(cleanup_records())


def test_selects_only_approved_sources_and_creates_lead_extraction_task() -> None:
    allowed_low = asyncio.run(seed_candidate(risk_level="Low"))
    allowed_medium = asyncio.run(seed_candidate(risk_level="Medium", extraction_status=LeadSourceCandidateExtractionStatus.RETRY))
    auto_approved_pending = asyncio.run(
        seed_candidate(risk_level="Low", review_status=LeadSourceCandidateReviewStatus.PENDING, approved_for_extraction=True)
    )
    auto_approved_unapproved_flag = asyncio.run(seed_candidate(risk_level="Low", approved_for_extraction=False))
    asyncio.run(seed_candidate(risk_level="Low", extraction_status=LeadSourceCandidateExtractionStatus.SUCCEEDED))

    response = client.post(
        "/agent-tasks/lead-extraction/from-sources/run",
        json={"limit": 10, "trigger_source": TEST_PREFIX, "country": TEST_COUNTRY, "city": TEST_CITY},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "pending"
    assert body["selected_count"] == 4
    assert thread_starts
    assert set(body["candidate_ids"]) == {
        allowed_low,
        allowed_medium,
        auto_approved_pending,
        auto_approved_unapproved_flag,
    }
    assert body["blocked_count"] == 1
    assert {item["block_reason"] for item in body["blocked_candidates"]} == {
        "extraction_status_not_pending_or_retry",
    }

    task = asyncio.run(get_task(body["agent_task_run_id"]))
    assert task.task_type == AgentTaskType.LEAD_EXTRACTION
    assert task.status == AgentTaskRunStatus.PENDING
    assert task.trigger_source == TEST_PREFIX
    assert set(task.input_json["candidate_ids"]) == {
        allowed_low,
        allowed_medium,
        auto_approved_pending,
        auto_approved_unapproved_flag,
    }
    assert task.input_json["source_selection_rule"] == "approved_pending_or_retry_only"

    for candidate_id in (allowed_low, allowed_medium, auto_approved_pending, auto_approved_unapproved_flag):
        candidate = asyncio.run(get_candidate(candidate_id))
        assert candidate.extraction_status == LeadSourceCandidateExtractionStatus.QUEUED
        assert candidate.review_status == LeadSourceCandidateReviewStatus.AUTO_APPROVED
        assert candidate.approved_for_extraction is True


def test_blocks_forbidden_and_unreviewed_high_sources_from_selection() -> None:
    high_unreviewed = asyncio.run(seed_candidate(risk_level="High"))
    forbidden = asyncio.run(seed_candidate(risk_level="Forbidden"))
    approved_high = asyncio.run(
        seed_candidate(
            risk_level="High",
            review_status=LeadSourceCandidateReviewStatus.APPROVED,
            approved_for_extraction=True,
        )
    )

    response = client.post(
        "/agent-tasks/lead-extraction/from-sources/run",
        json={"limit": 10, "trigger_source": TEST_PREFIX, "country": TEST_COUNTRY, "city": TEST_CITY},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["selected_count"] == 1
    assert body["candidate_ids"] == [approved_high]
    assert body["blocked_count"] == 2
    assert {item["candidate_id"] for item in body["blocked_candidates"]} == {high_unreviewed, forbidden}
    assert {item["block_reason"] for item in body["blocked_candidates"]} == {
        "high_risk_requires_manual_approval",
        "forbidden_risk_blocked",
    }


def test_paused_channel_and_blocked_extraction_status_are_not_consumed() -> None:
    paused_channel = f"{TEST_PREFIX}-paused-channel"
    paused_candidate = asyncio.run(seed_candidate(risk_level="Low", channel_name=paused_channel))
    blocked_candidate = asyncio.run(
        seed_candidate(risk_level="Low", extraction_status=LeadSourceCandidateExtractionStatus.BLOCKED)
    )
    eligible_candidate = asyncio.run(seed_candidate(risk_level="Low"))
    asyncio.run(seed_paused_channel_plan(paused_channel))

    response = client.post(
        "/agent-tasks/lead-extraction/from-sources/run",
        json={"limit": 10, "trigger_source": TEST_PREFIX, "country": TEST_COUNTRY, "city": TEST_CITY},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["selected_count"] == 1
    assert body["candidate_ids"] == [eligible_candidate]
    assert body["blocked_count"] == 2
    assert {item["candidate_id"] for item in body["blocked_candidates"]} == {paused_candidate, blocked_candidate}
    assert {item["block_reason"] for item in body["blocked_candidates"]} == {
        "channel_paused_or_archived",
        "extraction_status_not_pending_or_retry",
    }


def test_returns_422_when_no_sources_are_eligible() -> None:
    asyncio.run(seed_candidate(risk_level="Forbidden"))

    response = client.post(
        "/agent-tasks/lead-extraction/from-sources/run",
        json={"limit": 10, "trigger_source": TEST_PREFIX, "country": TEST_COUNTRY, "city": TEST_CITY},
    )

    assert response.status_code == 422
    assert "没有符合准入条件" in response.json()["detail"]
