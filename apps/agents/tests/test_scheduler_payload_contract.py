from collections.abc import Iterator

import sys
from pathlib import Path
import importlib.util

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db_session
from app.main import app
from app.settings import get_settings


PAYLOADS_PATH = Path(__file__).resolve().parents[2] / "api" / "app" / "agents" / "scheduler_payloads.py"
spec = importlib.util.spec_from_file_location("api_scheduler_payloads", PAYLOADS_PATH)
assert spec is not None
api_scheduler_payloads = importlib.util.module_from_spec(spec)
sys.modules["api_scheduler_payloads"] = api_scheduler_payloads
assert spec.loader is not None
spec.loader.exec_module(api_scheduler_payloads)


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


def test_apps_api_scheduler_source_discovery_payload_matches_apps_agents_contract(client: TestClient) -> None:
    request_id = "11111111-1111-1111-1111-111111111111"

    response = client.post(
        "/agent-runs/source-discovery",
        headers={"X-Agents-Api-Key": "phase4-secret"},
        json={
            "request_id": request_id,
            "trigger_source": "scheduler",
            "agent_mode": "shadow",
            "input": api_scheduler_payloads.build_external_source_discovery_input(request_id=request_id),
            "options": {"timeout_seconds": 120, "shadow_mode": True},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "succeeded"
    assert body["agent_type"] == "source_discovery"


def test_apps_api_scheduler_lead_extraction_grading_payload_matches_apps_agents_contract(client: TestClient) -> None:
    request_id = "11111111-1111-1111-1111-111111111111"

    response = client.post(
        "/agent-runs/lead-extraction-grading",
        headers={"X-Agents-Api-Key": "phase4-secret"},
        json={
            "request_id": request_id,
            "trigger_source": "scheduler",
            "agent_mode": "shadow",
            "input": api_scheduler_payloads.build_external_lead_extraction_grading_input(request_id=request_id),
            "options": {"timeout_seconds": 120, "shadow_mode": True},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "succeeded"
    assert body["agent_type"] == "lead_extraction_grading"
