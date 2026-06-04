from dataclasses import dataclass
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.models.agent_task_run import AgentTaskRun
from app.models.enums import AgentTaskRunStatus, AgentTaskType
from app.services.source_discovery_agent import SourceDiscoveryAgentResult


client = TestClient(app)


@dataclass
class MockSourceDiscoveryAgentService:
    calls: list

    async def run(self, request):
        self.calls.append(request)
        task_run = AgentTaskRun(
            id=uuid4(),
            task_type=AgentTaskType.SOURCE_DISCOVERY,
            status=AgentTaskRunStatus.SUCCEEDED,
            trigger_source=request.trigger_source,
            input_json=request.model_dump(),
            output_summary_json={"created_count": 3, "blocked_count": 2, "duplicate_count": 1},
        )
        return SourceDiscoveryAgentResult(
            task_run=task_run,
            created_count=3,
            updated_count=0,
            blocked_count=2,
            duplicate_count=1,
        )

    async def create_pending_task(self, request):
        self.calls.append(request)
        return AgentTaskRun(
            id=uuid4(),
            task_type=AgentTaskType.SOURCE_DISCOVERY,
            status=AgentTaskRunStatus.PENDING,
            trigger_source=request.trigger_source,
            input_json=request.model_dump(),
            output_summary_json={"created_count": 0, "blocked_count": 0, "duplicate_count": 0},
        )


def override_source_discovery_service():
    return mock_service


mock_service = MockSourceDiscoveryAgentService(calls=[])
thread_starts: list[str] = []


class FakeThreadRunner:
    @classmethod
    def start(cls, *, name, target):
        thread_starts.append(name)
        return None


def setup_function():
    mock_service.calls.clear()
    thread_starts.clear()
    from app.api.source_discovery_agent import get_source_discovery_service
    import app.api.source_discovery_agent as source_discovery_api

    app.dependency_overrides[get_source_discovery_service] = override_source_discovery_service
    source_discovery_api.AgentThreadRunner = FakeThreadRunner


def teardown_function():
    app.dependency_overrides.clear()


def test_source_discovery_run_api_starts_manual_task_without_waiting_for_agent_completion() -> None:
    response = client.post(
        "/agent-tasks/source-discovery/run",
        json={
            "country": "Russia",
            "cities": ["Moscow", "Saint Petersburg"],
            "channel_strategy": "official_website_public_directory_search_engine",
            "keywords": ["автосалон", "импорт авто"],
            "limit": 20,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["agent_task_run_id"]
    assert body["status"] == "pending"
    assert body["created_count"] == 0
    assert body["blocked_count"] == 0
    assert body["duplicate_count"] == 0
    assert thread_starts

    assert len(mock_service.calls) == 1
    request = mock_service.calls[0]
    assert request.country == "Russia"
    assert request.city == "Moscow, Saint Petersburg"
    assert request.channel_strategy == "official_website_public_directory_search_engine"
    assert request.keywords == ["автосалон", "импорт авто"]
    assert request.max_candidates == 20
    assert request.trigger_source == "manual_api"


def test_source_discovery_run_api_defaults_limit_to_20() -> None:
    response = client.post(
        "/agent-tasks/source-discovery/run",
        json={
            "country": "Russia",
            "cities": ["Moscow"],
            "channel_strategy": "official_website_public_directory_search_engine",
            "keywords": ["автосалон"],
        },
    )

    assert response.status_code == 200
    assert mock_service.calls[0].max_candidates == 20


def test_source_discovery_run_api_rejects_limit_outside_phase_two_quota() -> None:
    too_low = client.post(
        "/agent-tasks/source-discovery/run",
        json={
            "country": "Russia",
            "cities": ["Moscow"],
            "channel_strategy": "official_website_public_directory_search_engine",
            "keywords": ["автосалон"],
            "limit": 19,
        },
    )
    too_high = client.post(
        "/agent-tasks/source-discovery/run",
        json={
            "country": "Russia",
            "cities": ["Moscow"],
            "channel_strategy": "official_website_public_directory_search_engine",
            "keywords": ["автосалон"],
            "limit": 51,
        },
    )

    assert too_low.status_code == 422
    assert too_high.status_code == 422
    assert mock_service.calls == []


def test_source_discovery_run_api_is_registered_without_outreach_entrypoint() -> None:
    openapi = client.get("/openapi.json").json()

    assert "/agent-tasks/source-discovery/run" in openapi["paths"]
    assert set(openapi["paths"]["/agent-tasks/source-discovery/run"].keys()) == {"post"}
    assert all("outreach" not in path for path in openapi["paths"] if path.startswith("/agent-tasks/source-discovery"))
