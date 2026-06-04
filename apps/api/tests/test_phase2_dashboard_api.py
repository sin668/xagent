import asyncio
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.db.session import AsyncSessionLocal
from app.main import app
from app.models.agent_task_run import AgentTaskRun
from app.models.enums import (
    AgentTaskRunStatus,
    AgentTaskType,
    ChannelRiskLevel,
    LeadSourceCandidateExtractionStatus,
    LeadSourceCandidateReviewStatus,
    RiskEventSeverity,
    RiskEventStatus,
    SourcePlatform,
)
from app.models.lead_source_candidate import LeadSourceCandidate
from app.models.risk_event import RiskEvent


TEST_PREFIX = "TEST-P2E6S1"
TEST_DOMAIN_PREFIX = TEST_PREFIX.lower()


client = TestClient(app)


async def cleanup_records() -> None:
    async with AsyncSessionLocal() as async_session:
        await async_session.execute(delete(RiskEvent).where(RiskEvent.channel.like(f"{TEST_PREFIX}%")))
        await async_session.execute(delete(LeadSourceCandidate).where(LeadSourceCandidate.normalized_domain.like(f"{TEST_DOMAIN_PREFIX}%")))
        await async_session.execute(delete(AgentTaskRun).where(AgentTaskRun.trigger_source.like(f"{TEST_PREFIX}%")))
        await async_session.commit()


async def seed_records() -> None:
    now = datetime.now(UTC)
    async with AsyncSessionLocal() as async_session:
        def add(sync_session):
            task_success = AgentTaskRun(
                task_type=AgentTaskType.LEAD_EXTRACTION,
                status=AgentTaskRunStatus.SUCCEEDED,
                trigger_source=f"{TEST_PREFIX}-lead-extraction",
                input_json={"candidate_ids": ["candidate-low"]},
                output_summary_json={"succeeded_count": 1, "failed_count": 0, "cost_amount": 1.25, "cost_currency": "USD"},
                token_usage_json={"total_tokens": 1000},
                llm_provider="fake-provider",
                llm_model="fake-extraction",
                prompt_version="lead-extraction-v1",
                created_at=now - timedelta(minutes=10),
                updated_at=now - timedelta(minutes=9),
            )
            task_failed = AgentTaskRun(
                task_type=AgentTaskType.SOURCE_DISCOVERY,
                status=AgentTaskRunStatus.FAILED,
                trigger_source=f"{TEST_PREFIX}-source-discovery",
                input_json={"country": "Russia"},
                output_summary_json={
                    "error": {"type": "schema_validation_error", "message": "missing evidence"},
                    "cost_amount": 0.75,
                    "cost_currency": "USD",
                },
                token_usage_json={"total_tokens": 500},
                llm_provider="fake-provider",
                llm_model="fake-discovery",
                prompt_version="source-discovery-v1",
                error_message="missing evidence",
                created_at=now - timedelta(minutes=8),
                updated_at=now - timedelta(minutes=7),
            )
            sync_session.add_all([task_success, task_failed])
            sync_session.flush()

            candidates = [
                LeadSourceCandidate(
                    source_url=f"https://{TEST_PREFIX.lower()}-low.example.com",
                    normalized_domain=f"{TEST_PREFIX.lower()}-low.example.com",
                    platform=SourcePlatform.OFFICIAL_WEBSITE,
                    channel_name=f"{TEST_PREFIX}-official",
                    country="Russia",
                    city="Moscow",
                    risk_level=ChannelRiskLevel.LOW,
                    review_status=LeadSourceCandidateReviewStatus.AUTO_APPROVED,
                    approved_for_extraction=True,
                    discovery_method="keyword_search",
                    discovery_query="автосалон Москва",
                    discovery_reason="公开官网来源。",
                    evidence_note="公开页面包含经销商信息。",
                    evidence_links=[f"https://{TEST_PREFIX.lower()}-low.example.com"],
                    extraction_status=LeadSourceCandidateExtractionStatus.SUCCEEDED,
                    created_by_task_run_id=task_success.id,
                    created_at=now - timedelta(minutes=6),
                    updated_at=now - timedelta(minutes=5),
                    last_extracted_at=now - timedelta(minutes=4),
                    dedupe_key=f"{TEST_PREFIX}-low",
                ),
                LeadSourceCandidate(
                    source_url=f"https://{TEST_PREFIX.lower()}-medium.example.com",
                    normalized_domain=f"{TEST_PREFIX.lower()}-medium.example.com",
                    platform=SourcePlatform.PUBLIC_DIRECTORY,
                    channel_name=f"{TEST_PREFIX}-directory",
                    country="Russia",
                    city="Kazan",
                    risk_level=ChannelRiskLevel.MEDIUM,
                    review_status=LeadSourceCandidateReviewStatus.PENDING,
                    approved_for_extraction=False,
                    discovery_method="directory_search",
                    discovery_query="used cars Kazan",
                    discovery_reason="公开目录来源。",
                    evidence_note="待人工复核。",
                    evidence_links=[f"https://{TEST_PREFIX.lower()}-medium.example.com"],
                    extraction_status=LeadSourceCandidateExtractionStatus.PENDING,
                    created_at=now - timedelta(minutes=5),
                    updated_at=now - timedelta(minutes=5),
                    dedupe_key=f"{TEST_PREFIX}-medium",
                ),
                LeadSourceCandidate(
                    source_url=f"https://{TEST_PREFIX.lower()}-high.example.com",
                    normalized_domain=f"{TEST_PREFIX.lower()}-high.example.com",
                    platform=SourcePlatform.OTHER,
                    channel_name=f"{TEST_PREFIX}-social",
                    country="Russia",
                    city="Saint Petersburg",
                    risk_level=ChannelRiskLevel.HIGH,
                    review_status=LeadSourceCandidateReviewStatus.HIGH_RISK_REVIEW,
                    approved_for_extraction=False,
                    discovery_method="policy_research",
                    discovery_query="vk dealers",
                    discovery_reason="High 风险来源待复核。",
                    evidence_note="仅政策研究。",
                    evidence_links=[f"https://{TEST_PREFIX.lower()}-high.example.com"],
                    extraction_status=LeadSourceCandidateExtractionStatus.PENDING,
                    created_at=now - timedelta(minutes=4),
                    updated_at=now - timedelta(minutes=4),
                    dedupe_key=f"{TEST_PREFIX}-high",
                ),
                LeadSourceCandidate(
                    source_url=f"https://{TEST_PREFIX.lower()}-forbidden.example.com",
                    normalized_domain=f"{TEST_PREFIX.lower()}-forbidden.example.com",
                    platform=SourcePlatform.OTHER,
                    channel_name=f"{TEST_PREFIX}-forbidden",
                    country="Russia",
                    city=None,
                    risk_level=ChannelRiskLevel.FORBIDDEN,
                    review_status=LeadSourceCandidateReviewStatus.REJECTED,
                    approved_for_extraction=False,
                    discovery_method="blocked_policy",
                    discovery_query=None,
                    discovery_reason="Forbidden 来源。",
                    evidence_note="Forbidden 来源不得进入自动任务。",
                    evidence_links=[f"https://{TEST_PREFIX.lower()}-forbidden.example.com"],
                    extraction_status=LeadSourceCandidateExtractionStatus.BLOCKED,
                    created_at=now - timedelta(minutes=3),
                    updated_at=now - timedelta(minutes=3),
                    dedupe_key=f"{TEST_PREFIX}-forbidden",
                ),
            ]
            sync_session.add_all(candidates)
            sync_session.add_all(
                [
                    RiskEvent(
                        task_id=str(task_failed.id),
                        agent_name="source_discovery_agent",
                        action="schema_validate",
                        channel=f"{TEST_PREFIX}-social",
                        risk_level=ChannelRiskLevel.HIGH,
                        event_type="platform_policy_risk",
                        severity=RiskEventSeverity.HIGH,
                        resolution_status=RiskEventStatus.OPEN,
                        block_reason="High 风险来源必须人工复核。",
                        pause_suggested=True,
                        result="blocked",
                        created_at=now - timedelta(minutes=2),
                    ),
                    RiskEvent(
                        task_id=str(task_failed.id),
                        agent_name="source_discovery_agent",
                        action="risk_gate",
                        channel=f"{TEST_PREFIX}-forbidden",
                        risk_level=ChannelRiskLevel.FORBIDDEN,
                        event_type="forbidden_source_blocked",
                        severity=RiskEventSeverity.CRITICAL,
                        resolution_status=RiskEventStatus.OPEN,
                        block_reason="Forbidden 来源不得进入自动任务。",
                        pause_suggested=True,
                        result="blocked",
                        created_at=now - timedelta(minutes=1),
                    ),
                ]
            )

        await async_session.run_sync(add)
        await async_session.commit()


def setup_function():
    asyncio.run(cleanup_records())
    asyncio.run(seed_records())


def teardown_function():
    asyncio.run(cleanup_records())


def test_phase2_dashboard_returns_source_task_cost_failure_and_risk_metrics() -> None:
    response = client.get(f"/dashboard/phase2?channel_prefix={TEST_PREFIX}")

    assert response.status_code == 200
    payload = response.json()
    summary = payload["summary"]

    assert summary["source_candidate_count"] == 4
    assert summary["review_backlog_count"] == 2
    assert summary["auto_extraction_count"] == 1
    assert summary["agent_task_count"] == 2
    assert summary["failed_task_count"] == 1
    assert summary["llm_cost_total"] == 2.0
    assert summary["risk_event_count"] == 2
    assert summary["high_forbidden_risk_event_count"] == 2

    assert payload["risk_distribution"] == {"Low": 1, "Medium": 1, "High": 1, "Forbidden": 1}
    assert payload["review_backlog"]["pending"] == 1
    assert payload["review_backlog"]["high_risk_review"] == 1
    assert payload["extraction_status_distribution"]["succeeded"] == 1
    assert payload["extraction_status_distribution"]["blocked"] == 1

    failure = payload["failure_reasons"][0]
    assert failure["reason"] == "schema_validation_error"
    assert failure["count"] == 1
    assert failure["agent_task_run_ids"]

    assert payload["llm_costs"]["total_cost"] == 2.0
    assert len(payload["llm_costs"]["items"]) == 2
    assert all(item["agent_task_run_id"] for item in payload["llm_costs"]["items"])
    assert all(item["cost_amount"] > 0 for item in payload["llm_costs"]["items"])

    assert len(payload["high_forbidden_risk_events"]) == 2
    assert {item["risk_level"] for item in payload["high_forbidden_risk_events"]} == {"High", "Forbidden"}
    assert "不自动社交私信" in payload["guardrail"]


def test_phase2_dashboard_api_contract_is_registered() -> None:
    openapi = client.get("/openapi.json").json()

    assert "/dashboard/phase2" in openapi["paths"]
