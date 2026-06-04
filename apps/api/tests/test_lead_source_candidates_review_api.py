import asyncio
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.db.session import AsyncSessionLocal
from app.main import app
from app.models.agent_task_run import AgentTaskRun
from app.models.enums import AgentTaskRunStatus, AgentTaskType
from app.models.lead_source_candidate import LeadSourceCandidate
from app.services.lead_source_candidates import LeadSourceCandidateService


client = TestClient(app)
TEST_PREFIX = "p2e3s6"


def candidate_payload(suffix: str, *, risk_level: str = "Low", channel_name: str = "dealer_directory") -> dict:
    return {
        "source_url": f"https://{TEST_PREFIX}-{suffix}.example.com/source",
        "platform": "official_website",
        "channel_name": channel_name,
        "country": "Russia",
        "city": "Moscow",
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
            delete(LeadSourceCandidate).where(LeadSourceCandidate.normalized_domain.like(f"{TEST_PREFIX}%"))
        )
        await async_session.execute(delete(AgentTaskRun).where(AgentTaskRun.trigger_source.like(f"{TEST_PREFIX}%")))
        await async_session.execute(delete(AgentTaskRun).where(AgentTaskRun.trigger_source == "lead_source_review_api"))
        await async_session.commit()


async def seed_candidate(*, risk_level: str = "Low", channel_name: str = "dealer_directory") -> str:
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
            sync_session.flush()
            return str(candidate.id)

        candidate_id = await async_session.run_sync(run)
        await async_session.commit()
        return candidate_id


def setup_function():
    asyncio.run(cleanup_records())


def teardown_function():
    asyncio.run(cleanup_records())


def post_action(candidate_id: str, action: str, note: str = "人工审核确认。"):
    return client.post(
        f"/lead-source-candidates/{candidate_id}/review-actions",
        json={"action": action, "reviewer_id": "ops-reviewer-1", "review_note": note},
    )


def test_approve_for_extraction_updates_candidate_and_writes_audit_task() -> None:
    candidate_id = asyncio.run(seed_candidate(risk_level="Medium"))

    response = post_action(candidate_id, "approve_for_extraction", "公开来源可进入只读抽取。")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == candidate_id
    assert body["review_status"] == "approved"
    assert body["approved_for_extraction"] is True
    assert body["reviewer_id"] == "ops-reviewer-1"
    assert body["review_note"] == "公开来源可进入只读抽取。"
    assert body["reviewed_at"]
    assert body["audit_task_run_id"]

    audit_response = client.get(f"/lead-source-candidates/{candidate_id}")
    assert audit_response.status_code == 200


def test_forbidden_candidate_cannot_be_approved_for_extraction_and_is_audited() -> None:
    candidate_id = asyncio.run(seed_candidate(risk_level="Forbidden"))

    response = post_action(candidate_id, "approve_for_extraction", "尝试放行 Forbidden 来源。")

    assert response.status_code == 422
    assert "Forbidden" in response.json()["detail"]

    detail = client.get(f"/lead-source-candidates/{candidate_id}").json()
    assert detail["review_status"] == "rejected"
    assert detail["approved_for_extraction"] is False
    assert detail["extraction_status"] == "blocked"


def test_high_candidate_approval_only_enables_read_only_extraction_not_outreach() -> None:
    candidate_id = asyncio.run(seed_candidate(risk_level="High"))

    response = post_action(candidate_id, "approve_for_extraction", "High 来源人工审核通过，仅允许只读抽取。")

    assert response.status_code == 200
    body = response.json()
    assert body["risk_level"] == "High"
    assert body["review_status"] == "approved"
    assert body["approved_for_extraction"] is True
    assert "只读抽取" in body["review_note"]

    openapi = client.get("/openapi.json").json()
    review_paths = [path for path in openapi["paths"] if path.startswith("/lead-source-candidates")]
    assert all("outreach" not in path for path in review_paths)


def test_reject_mark_high_risk_pause_channel_and_add_review_note_actions() -> None:
    reject_id = asyncio.run(seed_candidate(risk_level="Low"))
    high_id = asyncio.run(seed_candidate(risk_level="Medium"))
    pause_id = asyncio.run(seed_candidate(risk_level="Medium", channel_name="risky_channel"))
    note_id = asyncio.run(seed_candidate(risk_level="Low"))

    rejected = post_action(reject_id, "reject", "来源质量不足。")
    marked_high = post_action(high_id, "mark_high_risk", "公开社媒入口，需要高风险复核。")
    paused = post_action(pause_id, "pause_channel", "该渠道短期暂停。")
    noted = post_action(note_id, "add_review_note", "补充审核备注，不改变准入状态。")

    assert rejected.status_code == 200
    assert rejected.json()["review_status"] == "rejected"
    assert rejected.json()["approved_for_extraction"] is False
    assert rejected.json()["extraction_status"] == "blocked"

    assert marked_high.status_code == 200
    assert marked_high.json()["risk_level"] == "High"
    assert marked_high.json()["review_status"] == "high_risk_review"
    assert marked_high.json()["approved_for_extraction"] is False

    assert paused.status_code == 200
    assert paused.json()["review_status"] == "paused"
    assert paused.json()["approved_for_extraction"] is False
    assert paused.json()["extraction_status"] == "blocked"

    assert noted.status_code == 200
    assert noted.json()["review_note"] == "补充审核备注，不改变准入状态。"
    assert noted.json()["reviewer_id"] == "ops-reviewer-1"
    assert noted.json()["reviewed_at"]


def test_review_action_requires_reviewer_and_note_and_unknown_candidate_returns_404() -> None:
    candidate_id = asyncio.run(seed_candidate(risk_level="Low"))

    missing_reviewer = client.post(
        f"/lead-source-candidates/{candidate_id}/review-actions",
        json={"action": "reject", "review_note": "缺 reviewer。"},
    )
    missing_note = client.post(
        f"/lead-source-candidates/{candidate_id}/review-actions",
        json={"action": "reject", "reviewer_id": "ops-reviewer-1"},
    )
    unknown = post_action(str(uuid4()), "reject", "未知来源。")

    assert missing_reviewer.status_code == 422
    assert missing_note.status_code == 422
    assert unknown.status_code == 404


def test_review_api_writes_agent_task_run_audit_record() -> None:
    candidate_id = asyncio.run(seed_candidate(risk_level="Low"))

    response = post_action(candidate_id, "reject", "审计记录测试。")

    assert response.status_code == 200
    audit_task_run_id = response.json()["audit_task_run_id"]

    async def verify():
        async with AsyncSessionLocal() as async_session:
            def run(sync_session):
                return sync_session.get(AgentTaskRun, audit_task_run_id)

            return await async_session.run_sync(run)

    audit = asyncio.run(verify())
    assert audit.status == AgentTaskRunStatus.SUCCEEDED
    assert audit.trigger_source == "lead_source_review_api"
    assert audit.input_json["action"] == "reject"
    assert audit.input_json["candidate_id"] == candidate_id
    assert audit.input_json["reviewer_id"] == "ops-reviewer-1"
    assert audit.output_summary_json["review_status"] == "rejected"

