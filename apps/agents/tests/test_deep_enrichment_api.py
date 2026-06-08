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


def deep_enrichment_payload() -> dict:
    return {
        "request_id": "11111111-1111-1111-1111-111111111111",
        "agent_task_run_id": "22222222-2222-2222-2222-222222222222",
        "trigger_source": "manual_api",
        "agent_mode": "active",
        "input": {
            "agent_run_id": "11111111-1111-1111-1111-111111111111",
            "staging_lead_id": "33333333-3333-3333-3333-333333333333",
            "lead_snapshot": {
                "customer_name": "Auto City",
                "country": "Russia",
                "city": "Moscow",
                "contacts_json": [],
            },
            "missing_fields": ["contacts_json"],
        },
        "options": {"max_retries": 2, "timeout_seconds": 120},
    }


def test_deep_enrichment_api_requires_internal_api_key(client: TestClient) -> None:
    response = client.post("/agent-runs/deep-enrichment", json=deep_enrichment_payload())

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or missing agents API key"}


def test_deep_enrichment_api_returns_unified_envelope_and_records_run(
    client: TestClient,
    session: Session,
) -> None:
    response = client.post(
        "/agent-runs/deep-enrichment",
        json=deep_enrichment_payload(),
        headers={"X-Agents-Api-Key": "phase4-secret"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["schema_version"] == "phase4.agent.run.v1"
    assert body["request_id"] == "11111111-1111-1111-1111-111111111111"
    assert body["status"] == "succeeded"
    assert body["agent_type"] == "deep_enrichment"
    assert body["agent_mode"] == "active"
    assert body["error"] is None
    assert body["audit"]["writes_core_tables"] is False
    assert "customers" not in body["audit"].get("written_tables", [])
    assert "contact_methods" not in body["audit"].get("written_tables", [])
    assert body["audit"]["executed_nodes"] == [
        "load_lead",
        "build_keywords",
        "search_public_sources",
        "read_public_pages",
        "extract_candidates",
        "validate_evidence",
        "write_enrichment_candidates",
        "recommend_action",
    ]

    output = body["output"]
    assert output["schema_version"] == "phase3.agent.deep_enrichment.v1"
    assert output["agent_run_id"] == "11111111-1111-1111-1111-111111111111"
    assert output["staging_lead_id"] == "33333333-3333-3333-3333-333333333333"
    assert set(output) == {
        "schema_version",
        "agent_run_id",
        "staging_lead_id",
        "field_candidates",
        "missing_fields",
        "recommended_next_action",
        "audit",
    }
    assert output["field_candidates"] == []
    assert output["audit"]["writes_core_tables"] is False

    persisted = session.get(AgentServiceRun, UUID(body["agent_service_run_id"]))
    assert persisted is not None
    assert persisted.status == "succeeded"
    assert persisted.agent_type == "deep_enrichment"
    assert persisted.agent_mode == "active"
    assert persisted.input_json["staging_lead_id"] == "33333333-3333-3333-3333-333333333333"
    assert persisted.output_json == output
    assert persisted.output_summary_json == {"field_candidate_count": 0, "risk_flags": []}
    assert persisted.audit_json["writes_core_tables"] is False


def test_deep_enrichment_api_records_failure_type_and_message(
    client: TestClient,
    session: Session,
) -> None:
    payload = deep_enrichment_payload()
    payload["input"]["requested_actions"] = ["auto_dm"]

    response = client.post(
        "/agent-runs/deep-enrichment",
        json=payload,
        headers={"X-Agents-Api-Key": "phase4-secret"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "failed"
    assert body["output"] is None
    assert body["error"]["error_type"] == "risk_blocked"
    assert "不允许自动私信" in body["error"]["message"]
    assert body["error"]["retryable"] is False

    persisted = session.get(AgentServiceRun, UUID(body["agent_service_run_id"]))
    assert persisted is not None
    assert persisted.status == "failed"
    assert persisted.error_type == "risk_blocked"
    assert "不允许自动私信" in persisted.error_message
