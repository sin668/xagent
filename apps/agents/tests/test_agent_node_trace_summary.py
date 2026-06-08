from collections.abc import Iterator

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.schemas.trace import AgentNodeTrace, AgentRunTraceAudit
from app.services.agent_service_runs import AgentServiceRunService


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


def test_node_trace_summary_schema_is_stable_and_redacted() -> None:
    trace = AgentNodeTrace(
        node="validate_evidence",
        status="succeeded",
        duration_ms=123,
        input_summary={"field_count": 2, "api_key": "sk-secret"},
        output_summary={"candidate_count": 1, "token": "secret-token"},
        error=None,
    )

    assert trace.model_dump() == {
        "node": "validate_evidence",
        "status": "succeeded",
        "duration_ms": 123,
        "input_summary": {"field_count": 2, "api_key": "[REDACTED]"},
        "output_summary": {"candidate_count": 1, "token": "[REDACTED]"},
        "error": None,
    }


def test_run_trace_audit_rejects_core_table_writes() -> None:
    with pytest.raises(ValidationError):
        AgentRunTraceAudit(writes_core_tables=True)


def test_append_node_trace_updates_audit_json_executed_nodes(session: Session) -> None:
    service = AgentServiceRunService(session)
    run = service.create_run(
        request_id="11111111-1111-1111-1111-111111111111",
        agent_type="deep_enrichment",
        agent_mode="active",
        trigger_source="manual_api",
        input_json={},
    )

    updated = service.append_node_trace(
        run.id,
        AgentNodeTrace(
            node="load_lead",
            status="succeeded",
            duration_ms=25,
            input_summary={"staging_lead_id": "22222222-2222-2222-2222-222222222222"},
            output_summary={"loaded": True},
        ),
    )

    assert updated.audit_json["writes_core_tables"] is False
    assert updated.audit_json["executed_nodes"] == [
        {
            "node": "load_lead",
            "status": "succeeded",
            "duration_ms": 25,
            "input_summary": {"staging_lead_id": "22222222-2222-2222-2222-222222222222"},
            "output_summary": {"loaded": True},
            "error": None,
        }
    ]
    assert updated.audit_json["failed_node"] is None
    assert updated.audit_json["risk_flags"] == []
    assert updated.audit_json["source_urls"] == []


def test_update_run_trace_summary_merges_risk_flags_and_source_urls(session: Session) -> None:
    service = AgentServiceRunService(session)
    run = service.create_run(
        request_id="11111111-1111-1111-1111-111111111111",
        agent_type="source_discovery",
        agent_mode="shadow",
        trigger_source="shadow_run",
        input_json={},
    )

    updated = service.update_trace_summary(
        run.id,
        risk_flags=["blocked_domain", "blocked_domain", "low_evidence"],
        source_urls=["https://dealer.example.ru", "https://dealer.example.ru/contact"],
    )

    assert updated.audit_json["writes_core_tables"] is False
    assert updated.audit_json["risk_flags"] == ["blocked_domain", "low_evidence"]
    assert updated.audit_json["source_urls"] == [
        "https://dealer.example.ru",
        "https://dealer.example.ru/contact",
    ]


def test_trace_updates_preserve_existing_audit_metadata(session: Session) -> None:
    service = AgentServiceRunService(session)
    run = service.create_run(
        request_id="11111111-1111-1111-1111-111111111111",
        agent_type="deep_enrichment",
        agent_mode="active",
        trigger_source="manual_api",
        input_json={},
    )
    run.audit_json = {
        "output_table": "lead_enrichment_field_candidates",
        "llm_provider": "deepseek",
    }
    session.add(run)
    session.commit()

    updated = service.append_node_trace(
        run.id,
        AgentNodeTrace(node="extract_candidates", status="succeeded", duration_ms=88),
    )

    assert updated.audit_json["output_table"] == "lead_enrichment_field_candidates"
    assert updated.audit_json["llm_provider"] == "deepseek"
    assert updated.audit_json["executed_nodes"][0]["node"] == "extract_candidates"


def test_failed_trace_records_failed_node_error_type_and_retryable(session: Session) -> None:
    service = AgentServiceRunService(session)
    run = service.create_run(
        request_id="11111111-1111-1111-1111-111111111111",
        agent_type="lead_cleanup",
        agent_mode="active",
        trigger_source="manual_api",
        input_json={},
    )

    traced = service.record_failed_node_trace(
        run.id,
        node="validate_evidence",
        duration_ms=70,
        error_type="evidence_validation_error",
        error_message="missing public evidence",
        retryable=False,
        input_summary={"source_text": "very long non-public content", "password": "secret"},
    )

    assert traced.audit_json["failed_node"] == "validate_evidence"
    assert traced.audit_json["executed_nodes"] == [
        {
            "node": "validate_evidence",
            "status": "failed",
            "duration_ms": 70,
            "input_summary": {"source_text": "very long non-public content", "password": "[REDACTED]"},
            "output_summary": {},
            "error": {
                "error_type": "evidence_validation_error",
                "message": "missing public evidence",
                "retryable": False,
            },
        }
    ]
