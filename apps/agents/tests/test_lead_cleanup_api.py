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
    seed_prompt_templates(db, ("LEAD_CLEANUP",))
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


def lead_cleanup_payload() -> dict:
    return {
        "request_id": "11111111-1111-1111-1111-111111111111",
        "agent_task_run_id": "22222222-2222-2222-2222-222222222222",
        "trigger_source": "manual_api",
        "agent_mode": "active",
        "input": {
            "cleanup_run_id": "11111111-1111-1111-1111-111111111111",
            "leads": [
                {
                    "staging_lead_id": "33333333-3333-3333-3333-333333333333",
                    "customer_name": "Auto City",
                    "city": "Moscow",
                    "recommended_grade": "Watch",
                    "contacts_json": [{"type": "email", "value": "sales@example.ru"}],
                },
                {
                    "staging_lead_id": "44444444-4444-4444-4444-444444444444",
                    "customer_name": " Auto City ",
                    "city": "Moscow",
                    "recommended_grade": "Invalid",
                    "contacts_json": [{"type": "email", "value": "sales@example.ru"}],
                    "invalid_reason": "重复线索。",
                },
            ],
        },
        "options": {"max_retries": 2, "timeout_seconds": 120},
    }


def test_lead_cleanup_api_requires_internal_api_key(client: TestClient) -> None:
    response = client.post("/agent-runs/lead-cleanup", json=lead_cleanup_payload())

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or missing agents API key"}


def test_lead_cleanup_api_returns_unified_envelope_and_records_run(
    client: TestClient,
    session: Session,
) -> None:
    response = client.post(
        "/agent-runs/lead-cleanup",
        json=lead_cleanup_payload(),
        headers={"X-Agents-Api-Key": "phase4-secret"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["schema_version"] == "phase4.agent.run.v1"
    assert body["request_id"] == "11111111-1111-1111-1111-111111111111"
    assert body["status"] == "succeeded"
    assert body["agent_type"] == "lead_cleanup"
    assert body["agent_mode"] == "active"
    assert body["error"] is None
    assert body["audit"]["writes_core_tables"] is False
    assert body["audit"]["executed_nodes"] == [
        "load_watch_invalid",
        "detect_duplicates",
        "classify_invalid_reason",
        "find_restore_candidates",
        "review_cleanup_with_llm",
        "write_cleanup_suggestions",
        "wait_human_review",
    ]

    output = body["output"]
    assert output["schema_version"] == "phase3.agent.lead_cleanup.v1"
    assert output["cleanup_run_id"] == "11111111-1111-1111-1111-111111111111"
    assert set(output) == {"schema_version", "cleanup_run_id", "suggestions", "blocked_items", "audit"}
    assert output["audit"]["writes_core_tables"] is False
    assert output["audit"]["auto_execute_cleanup"] is False
    assert output["audit"]["auto_restore_invalid"] is False

    strong_duplicate = next(item for item in output["suggestions"] if item["suggestion_type"] == "strong_duplicate")
    assert strong_duplicate["staging_lead_id"] == "44444444-4444-4444-4444-444444444444"
    assert strong_duplicate["target_lead_id"] == "33333333-3333-3333-3333-333333333333"
    assert strong_duplicate["review_status"] == "pending"
    assert strong_duplicate["confidence_score"] >= 0.8
    assert "matched_fields" in strong_duplicate["evidence_json"]

    persisted = session.get(AgentServiceRun, UUID(body["agent_service_run_id"]))
    assert persisted is not None
    assert persisted.status == "succeeded"
    assert persisted.agent_type == "lead_cleanup"
    assert persisted.agent_mode == "active"
    assert persisted.input_json["leads"][0]["staging_lead_id"] == "33333333-3333-3333-3333-333333333333"
    assert persisted.output_json == output
    assert persisted.output_summary_json == {"suggestion_count": len(output["suggestions"]), "blocked_item_count": 0, "risk_flags": []}
    assert persisted.audit_json["writes_core_tables"] is False


def test_lead_cleanup_api_records_failure_type_and_message(
    client: TestClient,
    session: Session,
) -> None:
    payload = lead_cleanup_payload()
    payload["input"]["requested_actions"] = ["auto_execute_cleanup"]

    response = client.post(
        "/agent-runs/lead-cleanup",
        json=payload,
        headers={"X-Agents-Api-Key": "phase4-secret"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "failed"
    assert body["output"] is None
    assert body["error"]["error_type"] == "risk_blocked"
    assert "不允许自动执行" in body["error"]["message"]
    assert body["error"]["retryable"] is False

    persisted = session.get(AgentServiceRun, UUID(body["agent_service_run_id"]))
    assert persisted is not None
    assert persisted.status == "failed"
    assert persisted.error_type == "risk_blocked"
    assert "不允许自动执行" in persisted.error_message
