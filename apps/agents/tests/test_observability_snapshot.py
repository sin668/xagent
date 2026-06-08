from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.models.agent_service_run import AgentServiceRun
from app.services.agent_service_runs import AgentServiceRunService
from app.services.observability import AgentServiceRunObservabilityService


@pytest.fixture
def session() -> Iterator[Session]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        engine.dispose()


def test_agent_service_run_observability_snapshot_redacts_sensitive_input_and_keeps_trace_summary(session: Session) -> None:
    service = AgentServiceRunService(session)
    run = service.create_run(
        request_id="11111111-1111-1111-1111-111111111111",
        agent_type="lead_extraction_grading",
        agent_mode="shadow",
        trigger_source="shadow_run",
        input_json={
            "api_key": "agents-secret",
            "source_content": "private source text should not leak",
            "source_url": "https://autocity.example",
        },
    )
    service.mark_running(run.id)
    succeeded = service.mark_succeeded(
        run.id,
        output_json={"schema_version": "phase4.agent.lead_extraction_grading.v1"},
        output_summary_json={"hard_rules_applied": False, "risk_flags": ["low_evidence"]},
    )
    succeeded.audit_json = {
        "writes_core_tables": False,
        "executed_nodes": [
            "lead_extraction.load_source_content",
            {"node": "lead_grading.apply_hard_rules", "status": "succeeded"},
        ],
        "failed_node": None,
        "risk_flags": ["low_evidence"],
        "source_urls": ["https://autocity.example"],
        "input_summary": {"token": "secret-token", "raw_text": "private source text should not leak", "lead_count": 1},
    }
    session.add(succeeded)
    session.commit()
    session.refresh(succeeded)

    snapshot = AgentServiceRunObservabilityService.snapshot(succeeded)

    assert snapshot["id"] == str(succeeded.id)
    assert snapshot["agent_type"] == "lead_extraction_grading"
    assert snapshot["agent_mode"] == "shadow"
    assert snapshot["status"] == "succeeded"
    assert snapshot["duration_ms"] is not None
    assert snapshot["retry_count"] == 0
    assert snapshot["executed_nodes"] == [
        "lead_extraction.load_source_content",
        "lead_grading.apply_hard_rules",
    ]
    assert snapshot["executed_node_count"] == 2
    assert snapshot["risk_flags"] == ["low_evidence"]
    assert snapshot["source_url_count"] == 1
    assert snapshot["output_summary_json"] == {"hard_rules_applied": False, "risk_flags": ["low_evidence"]}

    snapshot_text = str(snapshot)
    assert "agents-secret" not in snapshot_text
    assert "secret-token" not in snapshot_text
    assert "private source text should not leak" not in snapshot_text


def test_agent_service_run_observability_snapshot_preserves_error_and_retry_state(session: Session) -> None:
    service = AgentServiceRunService(session)
    run = service.create_run(
        request_id="11111111-1111-1111-1111-111111111111",
        agent_type="source_discovery",
        agent_mode="shadow",
        trigger_source="shadow_run",
        input_json={},
    )
    service.mark_running(run.id)
    retrying = service.mark_retrying(run.id, error_type="timeout_error", error_message="provider timeout")

    snapshot = AgentServiceRunObservabilityService.snapshot(retrying)

    assert snapshot["status"] == "retrying"
    assert snapshot["retry_count"] == 1
    assert snapshot["error_type"] == "timeout_error"
    assert snapshot["error_message"] == "provider timeout"
    assert snapshot["duration_ms"] is None
