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
TEST_PREFIX = "p2e3s5"


def discovery_candidate(
    *,
    source_url: str,
    platform: str,
    channel_name: str,
    country: str,
    city: str,
    risk_level: str,
    query: str,
) -> dict:
    return {
        "source_url": source_url,
        "platform": platform,
        "channel_name": channel_name,
        "country": country,
        "city": city,
        "risk_level": risk_level,
        "discovery_method": "keyword_search",
        "discovery_query": query,
        "discovery_reason": "公开来源页面展示车辆经销相关信息。",
        "evidence_note": "公开页面包含 dealer、auto sales 和 contact 信息。",
        "evidence_links": [source_url, f"{source_url}/contacts"],
        "confidence_score": 0.81,
    }


async def cleanup_records() -> None:
    async with AsyncSessionLocal() as async_session:
        await async_session.execute(
            delete(LeadSourceCandidate).where(LeadSourceCandidate.normalized_domain.like(f"{TEST_PREFIX}%"))
        )
        await async_session.execute(delete(AgentTaskRun).where(AgentTaskRun.trigger_source.like(f"{TEST_PREFIX}%")))
        await async_session.commit()


async def seed_candidates() -> dict[str, str]:
    async with AsyncSessionLocal() as async_session:
        def run(sync_session):
            task = AgentTaskRun(
                task_type=AgentTaskType.SOURCE_DISCOVERY,
                status=AgentTaskRunStatus.SUCCEEDED,
                trigger_source=f"{TEST_PREFIX}-manual",
                input_json={"country": "Russia"},
                output_summary_json={"created_count": 3},
            )
            sync_session.add(task)
            sync_session.flush()
            service = LeadSourceCandidateService(sync_session)
            first = service.upsert_candidate(
                discovery_candidate(
                    source_url=f"https://{TEST_PREFIX}-moscow.example.com/dealers",
                    platform="official_website",
                    channel_name="dealer_directory",
                    country="Russia",
                    city="Moscow",
                    risk_level="Low",
                    query="автосалон Москва",
                ),
                created_by_task_run_id=task.id,
                llm_provider="deepseek",
                llm_model="deepseek-chat",
                llm_output_json={
                    "task_type": "SOURCE_DISCOVERY",
                    "candidates": [{"source_url": f"https://{TEST_PREFIX}-moscow.example.com/dealers"}],
                    "blocked_candidates": [],
                },
            ).candidate
            second = service.upsert_candidate(
                discovery_candidate(
                    source_url=f"https://{TEST_PREFIX}-spb.example.com/map",
                    platform="yandex_maps",
                    channel_name="map_results",
                    country="Russia",
                    city="Saint Petersburg",
                    risk_level="Medium",
                    query="автосалон Санкт-Петербург",
                ),
                created_by_task_run_id=task.id,
                llm_provider="deepseek",
                llm_model="deepseek-chat",
                llm_output_json={"task_type": "SOURCE_DISCOVERY", "candidates": [], "blocked_candidates": []},
            ).candidate
            third = service.upsert_candidate(
                discovery_candidate(
                    source_url=f"https://{TEST_PREFIX}-blocked.example.com/private",
                    platform="other",
                    channel_name="blocked_candidate",
                    country="Russia",
                    city="Moscow",
                    risk_level="Forbidden",
                    query="форум private",
                ),
                created_by_task_run_id=task.id,
                llm_provider="deepseek",
                llm_model="deepseek-chat",
                llm_output_json={"task_type": "SOURCE_DISCOVERY", "candidates": [], "blocked_candidates": []},
            ).candidate
            sync_session.flush()
            return {"task_id": str(task.id), "first_id": str(first.id), "second_id": str(second.id), "third_id": str(third.id)}

        ids = await async_session.run_sync(run)
        await async_session.commit()
        return ids


async def get_candidate_count() -> int:
    async with AsyncSessionLocal() as async_session:
        def run(sync_session):
            return len(
                sync_session.scalars(
                    select(LeadSourceCandidate).where(
                        LeadSourceCandidate.normalized_domain.like(f"{TEST_PREFIX}%")
                    )
                ).all()
            )

        return await async_session.run_sync(run)


def setup_function():
    asyncio.run(cleanup_records())


def teardown_function():
    asyncio.run(cleanup_records())


def test_list_lead_source_candidates_supports_filters_and_queue_fields() -> None:
    asyncio.run(seed_candidates())

    response = client.get(
        "/lead-source-candidates",
        params={
            "risk_level": "Low",
            "review_status": "auto_approved",
            "country": "Russia",
            "city": "Moscow",
            "platform": "official_website",
            "channel_name": "dealer_directory",
            "extraction_status": "pending",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    item = body["items"][0]
    assert item["source_url"] == f"https://{TEST_PREFIX}-moscow.example.com/dealers"
    assert item["normalized_domain"] == f"{TEST_PREFIX}-moscow.example.com"
    assert item["risk_level"] == "Low"
    assert item["review_status"] == "auto_approved"
    assert item["evidence_note"].startswith("公开页面包含")
    assert item["llm_output_json"] is None
    assert item["approved_for_extraction"] is True
    assert item["created_at"]


def test_get_lead_source_candidate_detail_returns_evidence_and_llm_summary() -> None:
    ids = asyncio.run(seed_candidates())

    response = client.get(f"/lead-source-candidates/{ids['first_id']}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == ids["first_id"]
    assert body["created_by_task_run_id"] == ids["task_id"]
    assert body["evidence_links"] == [
        f"https://{TEST_PREFIX}-moscow.example.com/dealers",
        f"https://{TEST_PREFIX}-moscow.example.com/dealers/contacts",
    ]
    assert body["llm_provider"] == "deepseek"
    assert body["llm_model"] == "deepseek-chat"
    assert body["llm_output_summary"]["task_type"] == "SOURCE_DISCOVERY"
    assert body["llm_output_summary"]["candidate_count"] == 1
    assert body["llm_output_summary"]["blocked_count"] == 0


def test_list_lead_source_candidates_supports_limit_and_offset() -> None:
    asyncio.run(seed_candidates())

    first_page = client.get("/lead-source-candidates", params={"country": "Russia", "limit": 2, "offset": 0})
    second_page = client.get("/lead-source-candidates", params={"country": "Russia", "limit": 2, "offset": 2})

    assert first_page.status_code == 200
    assert second_page.status_code == 200
    assert first_page.json()["total"] >= 3
    assert len(first_page.json()["items"]) == 2
    assert len(second_page.json()["items"]) == 2


def test_get_lead_source_candidate_detail_returns_404_for_unknown_id() -> None:
    response = client.get(f"/lead-source-candidates/{uuid4()}")

    assert response.status_code == 404


def test_query_api_is_read_only_and_does_not_mutate_candidates() -> None:
    asyncio.run(seed_candidates())
    before = asyncio.run(get_candidate_count())

    openapi = client.get("/openapi.json").json()
    client.get("/lead-source-candidates", params={"country": "Russia"})

    after = asyncio.run(get_candidate_count())
    assert before == after
    assert set(openapi["paths"]["/lead-source-candidates"].keys()) == {"get"}
    assert set(openapi["paths"]["/lead-source-candidates/{candidate_id}"].keys()) == {"get"}
