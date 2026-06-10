from collections.abc import Iterator
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db_session
from app.main import app
from app.models.agent_service_run import AgentServiceRun
from app.settings import get_settings
from tests.prompt_helpers import seed_prompt_templates


@pytest.fixture
def session() -> Iterator[Session]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    seed_prompt_templates(db, ("SOURCE_DISCOVERY",))
    try:
        yield db
    finally:
        db.close()
        engine.dispose()


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch, session: Session) -> Iterator[TestClient]:
    monkeypatch.setenv("AGENTS_API_KEY", "phase4-secret")
    get_settings.cache_clear()

    def override_session() -> Iterator[Session]:
        yield session

    app.dependency_overrides[get_db_session] = override_session
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()


def source_discovery_payload(*, agent_mode: str = "shadow") -> dict:
    return {
        "request_id": "11111111-1111-1111-1111-111111111111",
        "agent_task_run_id": "22222222-2222-2222-2222-222222222222",
        "trigger_source": "shadow_run",
        "agent_mode": agent_mode,
        "input": {
            "discovery_run_id": "33333333-3333-3333-3333-333333333333",
            "market": "Russia",
            "channel_strategy": {
                "target_segments": ["local_dealer"],
                "keywords": ["used cars", "Toyota dealer"],
                "allowed_source_types": ["official_website", "public_directory", "public_social"],
            },
            "seed_urls": ["https://dealer.example.ru"],
            "search_results": [
                {
                    "url": "https://dealer.example.ru",
                    "title": "Auto City",
                    "snippet": "Auto City sells used cars and posts public contact information.",
                    "source_type": "official_website",
                },
                {
                    "url": "https://login.example.ru/private",
                    "title": "Login required",
                    "snippet": "login required captcha",
                    "source_type": "private_platform",
                },
            ],
        },
        "options": {"max_retries": 2, "timeout_seconds": 120, "shadow_mode": True},
    }


def test_source_discovery_api_requires_internal_api_key(client: TestClient) -> None:
    response = client.post("/agent-runs/source-discovery", json=source_discovery_payload())

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or missing agents API key"}


def test_source_discovery_api_returns_shadow_envelope_and_records_run(client: TestClient, session: Session) -> None:
    response = client.post(
        "/agent-runs/source-discovery",
        json=source_discovery_payload(),
        headers={"X-Agents-Api-Key": "phase4-secret"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["schema_version"] == "phase4.agent.run.v1"
    assert body["request_id"] == "11111111-1111-1111-1111-111111111111"
    assert body["status"] == "succeeded"
    assert body["agent_type"] == "source_discovery"
    assert body["agent_mode"] == "shadow"
    assert body["audit"]["writes_core_tables"] is False
    assert body["audit"]["executed_nodes"] == [
        "load_channel_strategy",
        "build_discovery_queries",
        "search_public_sources",
        "normalize_source_candidates",
        "classify_channel_risk",
        "dedupe_candidates",
        "validate_source_evidence",
        "output_shadow_candidates",
    ]

    output = body["output"]
    assert output["schema_version"] == "phase4.agent.source_discovery.v1"
    assert output["agent_mode"] == "shadow"
    assert output["discovery_run_id"] == "33333333-3333-3333-3333-333333333333"
    assert output["audit"]["writes_core_tables"] is False
    assert output["audit"]["output_table"] == "shadow_source_candidates"
    assert "lead_source_candidates" not in output["audit"]["written_tables"]
    assert len(output["candidates"]) == 1
    assert output["candidates"][0]["url"] == "https://dealer.example.ru"
    assert output["candidates"][0]["risk_level"] == "low"
    assert any(item["risk_level"] == "forbidden" for item in output["blocked_items"])

    persisted = session.get(AgentServiceRun, UUID(body["agent_service_run_id"]))
    assert persisted is not None
    assert persisted.status == "succeeded"
    assert persisted.agent_type == "source_discovery"
    assert persisted.agent_mode == "shadow"
    assert persisted.input_json["market"] == "Russia"
    assert persisted.output_json == output
    assert persisted.output_summary_json == {"candidate_count": 1, "blocked_item_count": 2, "risk_flags": []}
    assert persisted.audit_json["writes_core_tables"] is False


def test_source_discovery_api_blocks_dry_run_mode(client: TestClient, session: Session) -> None:
    response = client.post(
        "/agent-runs/source-discovery",
        json=source_discovery_payload(agent_mode="dry_run"),
        headers={"X-Agents-Api-Key": "phase4-secret"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "failed"
    assert body["agent_type"] == "source_discovery"
    assert body["agent_mode"] == "dry_run"
    assert body["output"] is None
    assert body["error"]["error_type"] == "risk_blocked"
    assert "Source Discovery agent_mode 只允许 active 或 shadow" in body["error"]["message"]

    persisted = session.get(AgentServiceRun, UUID(body["agent_service_run_id"]))
    assert persisted is not None
    assert persisted.status == "failed"
    assert persisted.error_type == "risk_blocked"
