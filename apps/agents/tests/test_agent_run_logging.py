import logging
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db_session
from app.main import app
from app.settings import get_settings


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


def test_agent_run_logs_start_nodes_and_result(client: TestClient, caplog: pytest.LogCaptureFixture) -> None:
    payload = {
        "request_id": "11111111-1111-1111-1111-111111111111",
        "agent_task_run_id": "22222222-2222-2222-2222-222222222222",
        "trigger_source": "manual_api",
        "agent_mode": "active",
        "input": {
            "agent_run_id": "11111111-1111-1111-1111-111111111111",
            "staging_lead_id": "33333333-3333-3333-3333-333333333333",
            "lead_snapshot": {"customer_name": "Auto City", "country": "Russia", "city": "Moscow"},
            "missing_fields": ["contacts_json"],
        },
        "options": {"max_retries": 2, "timeout_seconds": 120},
    }

    with caplog.at_level(logging.INFO, logger="app.agent_run"):
        response = client.post(
            "/agent-runs/deep-enrichment",
            json=payload,
            headers={"X-Agents-Api-Key": "phase4-secret"},
        )

    assert response.status_code == 200
    messages = [record.getMessage() for record in caplog.records]

    assert any("agent_run_start agent_type=deep_enrichment" in message for message in messages)
    assert any("agent_node_start agent_type=deep_enrichment node=load_lead" in message for message in messages)
    assert any("agent_node_finish agent_type=deep_enrichment node=recommend_action" in message for message in messages)
    assert any("agent_run_succeeded agent_type=deep_enrichment" in message for message in messages)
    assert any("status=succeeded" in message for message in messages)


def test_service_startup_logs_runtime_mode(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO, logger="app.agent_run"):
        with TestClient(app) as client:
            response = client.get("/health")

    assert response.status_code == 200
    messages = [record.getMessage() for record in caplog.records]
    assert any("agent_service_start service=vehicle-leads-agents version=0.1.0" in message for message in messages)
    assert any("agent_auto_start_disabled" in message for message in messages)
    assert any("source_discovery_and_lead_extraction_require_explicit_api_call" in message for message in messages)
