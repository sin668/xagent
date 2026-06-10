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


VALID_SOURCE_TEXT = """
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


def payload(
    *,
    source_content: str = VALID_SOURCE_TEXT,
    risk_flags: list[str] | None = None,
    expected_contacts: dict | None = None,
) -> dict:
    return {
        "request_id": "11111111-1111-1111-1111-111111111111",
        "agent_task_run_id": "22222222-2222-2222-2222-222222222222",
        "trigger_source": "shadow_run",
        "agent_mode": "shadow",
        "input": {
            "combined_run_id": "33333333-3333-3333-3333-333333333333",
            "extraction_run_id": "44444444-4444-4444-4444-444444444444",
            "grading_run_id": "55555555-5555-5555-5555-555555555555",
            "source_url": "https://autocity.example",
            "source_content": source_content,
            "risk_flags": risk_flags or [],
            "existing_grade": "B",
            "expected_contacts": expected_contacts or {},
        },
        "options": {"max_retries": 2, "timeout_seconds": 120, "shadow_mode": True},
    }


def test_extraction_grading_validation_summary_is_written_to_output_and_audit_json(
    client: TestClient,
    session: Session,
) -> None:
    response = client.post(
        "/agent-runs/lead-extraction-grading",
        json=payload(),
        headers={"X-Agents-Api-Key": "phase4-secret"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "succeeded"

    validation_summary = body["output"]["validation_summary"]
    assert validation_summary == {
        "schema_passed": True,
        "schema_pass_rate": 1.0,
        "evidence_hit_rate": 1.0,
        "contact_anti_fabrication_passed": True,
        "contact_anti_fabrication_pass_rate": 1.0,
        "hard_rule_consistency_rate": 1.0,
        "invalid_contacts": [],
        "validation_errors": [],
    }
    assert body["output"]["audit"]["validation_summary"] == validation_summary

    persisted = session.get(AgentServiceRun, UUID(body["agent_service_run_id"]))
    assert persisted is not None
    assert persisted.audit_json["validation_summary"] == validation_summary


def test_extraction_grading_marks_fabricated_expected_contacts_invalid(
    client: TestClient,
    session: Session,
) -> None:
    response = client.post(
        "/agent-runs/lead-extraction-grading",
        json=payload(expected_contacts={"email": "fake@autocity.example", "phone": "+971 50 000 0000"}),
        headers={"X-Agents-Api-Key": "phase4-secret"},
    )

    assert response.status_code == 200
    body = response.json()
    validation_summary = body["output"]["validation_summary"]

    assert validation_summary["schema_passed"] is True
    assert validation_summary["contact_anti_fabrication_passed"] is False
    assert validation_summary["contact_anti_fabrication_pass_rate"] == 0.0
    assert validation_summary["invalid_contacts"] == [
        {"field_name": "email", "value": "fake@autocity.example", "reason": "contact_not_found_in_source_content"},
        {"field_name": "phone", "value": "+971 50 000 0000", "reason": "contact_not_found_in_source_content"},
    ]
    assert "联系方式反编造校验失败" in validation_summary["validation_errors"]

    persisted = session.get(AgentServiceRun, UUID(body["agent_service_run_id"]))
    assert persisted is not None
    assert persisted.audit_json["validation_summary"]["contact_anti_fabrication_passed"] is False


@pytest.mark.parametrize(
    ("risk_flags", "expected_grade", "expected_route"),
    [
        (["forbidden_source"], "Invalid", "risk_blocked"),
        (["high_risk_source"], "Watch", "needs_manual_risk_review"),
        (["do_not_contact"], "Invalid", "risk_blocked"),
        (["c_level_compliance_review"], "C", "needs_compliance_review"),
        (["existing_invalid"], "Invalid", "risk_blocked"),
        (["existing_watch"], "Watch", "needs_manual_risk_review"),
    ],
)
def test_extraction_grading_hard_rule_consistency_is_100_percent(
    client: TestClient,
    risk_flags: list[str],
    expected_grade: str,
    expected_route: str,
) -> None:
    response = client.post(
        "/agent-runs/lead-extraction-grading",
        json=payload(risk_flags=risk_flags),
        headers={"X-Agents-Api-Key": "phase4-secret"},
    )

    assert response.status_code == 200
    body = response.json()
    suggestion = body["output"]["grading"]["suggestions"][0]
    validation_summary = body["output"]["validation_summary"]

    assert suggestion["recommended_grade"] == expected_grade
    assert suggestion["status_route"] == expected_route
    assert validation_summary["hard_rule_consistency_rate"] == 1.0
    assert validation_summary["validation_errors"] == []


def test_extraction_grading_evidence_summary_fails_when_contacts_are_missing_from_source(
    client: TestClient,
) -> None:
    source_content = "Minimal Motors sells used vehicles. Website: https://minimal.example."

    response = client.post(
        "/agent-runs/lead-extraction-grading",
        json=payload(source_content=source_content),
        headers={"X-Agents-Api-Key": "phase4-secret"},
    )

    assert response.status_code == 200
    body = response.json()
    validation_summary = body["output"]["validation_summary"]

    assert validation_summary["schema_passed"] is True
    assert validation_summary["evidence_hit_rate"] < 1.0
    assert validation_summary["contact_anti_fabrication_passed"] is True
    assert body["output"]["grading"]["suggestions"][0]["recommended_grade"] == "C"
