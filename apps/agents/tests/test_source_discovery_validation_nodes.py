from collections.abc import Iterator
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db_session
from app.graphs.source_discovery import SourceDiscoveryGraphRunner, SourceDiscoveryGraphState
from app.main import app
from app.models.agent_service_run import AgentServiceRun
from app.settings import get_settings


def test_source_discovery_validation_nodes_normalize_dedupe_and_block_invalid_sources() -> None:
    runner = SourceDiscoveryGraphRunner()
    state = SourceDiscoveryGraphState(
        discovery_run_id="11111111-1111-1111-1111-111111111111",
        market="Russia",
        channel_strategy={"keywords": ["used cars"]},
        search_results=[
            {
                "url": "HTTPS://WWW.Dealer.Example.RU/?utm_source=ad#contact",
                "title": "Auto City",
                "snippet": "Official dealer page with public used car stock.",
                "source_type": "official_website",
            },
            {
                "url": "https://dealer.example.ru",
                "title": "Auto City duplicate",
                "snippet": "Equivalent URL should be marked duplicate.",
                "source_type": "official_website",
            },
            {
                "url": "https://directory.example.ru/autocity",
                "title": "Auto City directory",
                "snippet": "Public business directory lists dealer address.",
                "source_type": "public_directory",
            },
            {
                "url": "https://social.example.ru/autocity",
                "title": "Auto City social",
                "snippet": "Public social profile with used car posts.",
                "source_type": "public_social",
            },
            {
                "url": "https://empty.example.ru",
                "title": "",
                "snippet": "",
                "source_type": "official_website",
            },
            {
                "url": "https://login.example.ru/private",
                "title": "Login required",
                "snippet": "captcha login required",
                "source_type": "private_platform",
            },
        ],
    )

    result = runner.run(state)

    assert [candidate.normalized_url for candidate in result.output.candidates] == [
        "https://dealer.example.ru",
        "https://directory.example.ru/autocity",
        "https://social.example.ru/autocity",
    ]
    assert [candidate.risk_level for candidate in result.output.candidates] == ["low", "medium", "high"]
    assert result.output.candidates[2].review_status == "needs_manual_review"

    blocked_reasons = {item["reason"] for item in result.output.blocked_items}
    assert {"duplicate_source", "missing_evidence_summary", "forbidden_source"} <= blocked_reasons
    assert all(candidate.risk_level != "forbidden" for candidate in result.output.candidates)

    summaries = result.output.audit["node_summaries"]
    assert summaries["normalize_source_candidates"]["normalized_count"] == 6
    assert summaries["dedupe_candidates"]["duplicate_count"] == 1
    assert summaries["validate_source_evidence"]["valid_candidate_count"] == 3
    assert summaries["validate_source_evidence"]["blocked_item_count"] == 3


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


def test_source_discovery_api_persists_node_execution_summaries_in_audit_json(client: TestClient, session: Session) -> None:
    payload = {
        "request_id": "11111111-1111-1111-1111-111111111111",
        "trigger_source": "shadow_run",
        "agent_mode": "shadow",
        "input": {
            "discovery_run_id": "33333333-3333-3333-3333-333333333333",
            "market": "Russia",
            "channel_strategy": {"keywords": ["used cars"]},
            "search_results": [
                {
                    "url": "https://dealer.example.ru",
                    "title": "Auto City",
                    "snippet": "Official dealer page with public used car stock.",
                    "source_type": "official_website",
                }
            ],
        },
        "options": {"shadow_mode": True},
    }

    response = client.post(
        "/agent-runs/source-discovery",
        json=payload,
        headers={"X-Agents-Api-Key": "phase4-secret"},
    )

    assert response.status_code == 200
    body = response.json()
    persisted = session.get(AgentServiceRun, UUID(body["agent_service_run_id"]))
    assert persisted is not None
    assert persisted.audit_json["executed_nodes"] == [
        {"node": "load_channel_strategy", "status": "succeeded", "summary": {"agent_mode": "shadow"}},
        {"node": "build_discovery_queries", "status": "succeeded", "summary": {"query_count": 1}},
        {"node": "search_public_sources", "status": "succeeded", "summary": {"raw_candidate_count": 1}},
        {"node": "normalize_source_candidates", "status": "succeeded", "summary": {"normalized_count": 1}},
        {"node": "classify_channel_risk", "status": "succeeded", "summary": {"risk_counts": {"low": 1}}},
        {"node": "dedupe_candidates", "status": "succeeded", "summary": {"duplicate_count": 0, "deduped_count": 1}},
        {"node": "validate_source_evidence", "status": "succeeded", "summary": {"valid_candidate_count": 1, "blocked_item_count": 0}},
        {"node": "output_shadow_candidates", "status": "succeeded", "summary": {"candidate_count": 1, "blocked_item_count": 0}},
    ]
