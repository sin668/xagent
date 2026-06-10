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


PUBLIC_SOURCE_TEXT = """
Auto City Dubai exports used Toyota Land Cruiser and Lexus LX vehicles to overseas buyers.
Contact: sales@autocity.example, +971 50 123 4567.
Located in Dubai, United Arab Emirates. Website: https://autocity.example.
The company says it can arrange export documentation and shipping.
"""


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
    seed_prompt_templates(db, ("LEAD_EXTRACTION", "LEAD_GRADING"))
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


def lead_extraction_grading_payload(*, agent_mode: str = "shadow", risk_flags: list[str] | None = None) -> dict:
    return {
        "request_id": "11111111-1111-1111-1111-111111111111",
        "agent_task_run_id": "22222222-2222-2222-2222-222222222222",
        "trigger_source": "shadow_run",
        "agent_mode": agent_mode,
        "input": {
            "extraction_run_id": "33333333-3333-3333-3333-333333333333",
            "grading_run_id": "44444444-4444-4444-4444-444444444444",
            "source_url": "https://autocity.example",
            "source_content": PUBLIC_SOURCE_TEXT,
            "risk_flags": risk_flags or [],
            "existing_grade": "B",
        },
        "options": {"max_retries": 2, "timeout_seconds": 120, "shadow_mode": True},
    }


def lead_extraction_grading_batch_payload() -> dict:
    payload = lead_extraction_grading_payload(agent_mode="active")
    payload["trigger_source"] = "scheduler"
    payload["agent_mode"] = "active"
    payload["options"] = {"max_retries": 2, "timeout_seconds": 120, "shadow_mode": False}
    payload["input"] = {
        "combined_run_id": "11111111-1111-1111-1111-111111111111",
        "source_url": "https://autocity.example",
        "source_content": PUBLIC_SOURCE_TEXT,
        "sources": [
            {
                "request_id": "33333333-3333-3333-3333-333333333331",
                "source_candidate_id": "candidate-1",
                "candidate_url_id": "candidate-url-1",
                "source_url": "https://autocity.example",
                "source_content": PUBLIC_SOURCE_TEXT,
                "risk_flags": [],
                "expected_contacts": {},
            },
            {
                "request_id": "33333333-3333-3333-3333-333333333332",
                "source_candidate_id": "candidate-2",
                "candidate_url_id": "candidate-url-2",
                "source_url": "https://autocity-second.example",
                "source_content": PUBLIC_SOURCE_TEXT.replace("sales@autocity.example", "sales@autocity-second.example"),
                "risk_flags": [],
                "expected_contacts": {},
            },
        ],
    }
    return payload


def test_lead_extraction_grading_api_requires_internal_api_key(client: TestClient) -> None:
    response = client.post("/agent-runs/lead-extraction-grading", json=lead_extraction_grading_payload())

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or missing agents API key"}


def test_lead_extraction_grading_api_runs_shadow_combined_flow_and_records_run(
    client: TestClient,
    session: Session,
) -> None:
    response = client.post(
        "/agent-runs/lead-extraction-grading",
        json=lead_extraction_grading_payload(),
        headers={"X-Agents-Api-Key": "phase4-secret"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["schema_version"] == "phase4.agent.run.v1"
    assert body["request_id"] == "11111111-1111-1111-1111-111111111111"
    assert body["status"] == "succeeded"
    assert body["agent_type"] == "lead_extraction_grading"
    assert body["agent_mode"] == "shadow"
    assert body["error"] is None
    assert body["audit"]["writes_core_tables"] is False
    assert body["audit"]["executed_nodes"] == [
        "lead_extraction.load_source_content",
        "lead_extraction.extract_candidate_fields",
        "lead_extraction.map_field_evidence",
        "lead_extraction.validate_required_evidence",
        "lead_extraction.output_shadow_staging_lead",
        "lead_grading.load_extracted_lead",
        "lead_grading.score_lead_signals",
        "lead_grading.apply_hard_rules",
        "lead_grading.explain_grade_delta",
        "lead_grading.output_shadow_grading",
    ]

    output = body["output"]
    assert output["schema_version"] == "phase4.agent.lead_extraction_grading.v1"
    assert output["agent_mode"] == "shadow"
    assert output["extraction"]["schema_version"] == "phase4.agent.lead_extraction.v1"
    assert output["grading"]["schema_version"] == "phase4.agent.lead_grading.v1"
    assert output["extraction"]["candidates"][0]["company_name"]["value"] == "Auto City Dubai"
    grading_suggestion = output["grading"]["suggestions"][0]
    assert grading_suggestion["recommended_grade"] == "A"
    assert grading_suggestion["status_route"] == "ready_for_manual_review"
    assert output["hard_rule_summary"]["hard_rules_applied"] is False
    assert "grade_delta_from_existing" in output["grade_delta_explanations"]
    assert output["audit"]["writes_core_tables"] is False
    assert "staging_leads" not in output["audit"].get("written_tables", [])
    assert "customers" not in output["audit"].get("written_tables", [])

    persisted = session.get(AgentServiceRun, UUID(body["agent_service_run_id"]))
    assert persisted is not None
    assert persisted.status == "succeeded"
    assert persisted.agent_type == "lead_extraction_grading"
    assert persisted.agent_mode == "shadow"
    assert persisted.input_json["source_url"] == "https://autocity.example"
    assert persisted.output_json == output
    assert persisted.output_summary_json == {
        "extracted_candidate_count": 1,
        "grading_suggestion_count": 1,
        "hard_rules_applied": False,
        "risk_flags": [],
    }
    assert persisted.audit_json["writes_core_tables"] is False


def test_lead_extraction_grading_api_processes_sources_in_one_batch_agent_run(
    client: TestClient,
    session: Session,
) -> None:
    response = client.post(
        "/agent-runs/lead-extraction-grading",
        json=lead_extraction_grading_batch_payload(),
        headers={"X-Agents-Api-Key": "phase4-secret"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "succeeded"
    assert body["agent_type"] == "lead_extraction_grading"
    assert body["agent_mode"] == "active"
    output = body["output"]
    assert len(output["batch_results"]) == 2
    assert [item["source_candidate_id"] for item in output["batch_results"]] == ["candidate-1", "candidate-2"]
    assert all(item["status"] == "succeeded" for item in output["batch_results"])
    assert body["audit"]["source_urls"] == ["https://autocity.example", "https://autocity-second.example"]

    persisted = session.get(AgentServiceRun, UUID(body["agent_service_run_id"]))
    assert persisted is not None
    assert persisted.output_summary_json["batch_source_count"] == 2
    assert persisted.output_summary_json["batch_succeeded_count"] == 2


def test_lead_extraction_grading_api_preserves_hard_rule_summary(client: TestClient) -> None:
    response = client.post(
        "/agent-runs/lead-extraction-grading",
        json=lead_extraction_grading_payload(risk_flags=["forbidden_source"]),
        headers={"X-Agents-Api-Key": "phase4-secret"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "succeeded"
    suggestion = body["output"]["grading"]["suggestions"][0]
    assert suggestion["recommended_grade"] == "Invalid"
    assert suggestion["status_route"] == "risk_blocked"
    assert "forbidden_source" in suggestion["triggered_rules"]
    assert body["output"]["hard_rule_summary"] == {
        "hard_rules_applied": True,
        "triggered_rules": suggestion["triggered_rules"],
        "risk_flags": ["forbidden_source"],
    }


def test_lead_extraction_grading_api_blocks_dry_run_mode(client: TestClient, session: Session) -> None:
    response = client.post(
        "/agent-runs/lead-extraction-grading",
        json=lead_extraction_grading_payload(agent_mode="dry_run"),
        headers={"X-Agents-Api-Key": "phase4-secret"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "failed"
    assert body["agent_type"] == "lead_extraction_grading"
    assert body["agent_mode"] == "dry_run"
    assert body["output"] is None
    assert body["error"]["error_type"] == "risk_blocked"
    assert "Lead Extraction/Grading agent_mode 只允许 active 或 shadow" in body["error"]["message"]

    persisted = session.get(AgentServiceRun, UUID(body["agent_service_run_id"]))
    assert persisted is not None
    assert persisted.status == "failed"
    assert persisted.error_type == "risk_blocked"
