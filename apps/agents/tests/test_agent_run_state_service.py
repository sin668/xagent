from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.models.agent_service_run import AgentServiceRun
from app.services.agent_service_runs import AgentServiceRunService, InvalidAgentRunTransition


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


def test_create_pending_run(session: Session) -> None:
    service = AgentServiceRunService(session)

    run = service.create_run(
        request_id="11111111-1111-1111-1111-111111111111",
        agent_type="deep_enrichment",
        agent_mode="active",
        trigger_source="manual_api",
        input_json={"staging_lead_id": "22222222-2222-2222-2222-222222222222"},
        max_retries=2,
    )

    assert run.id is not None
    assert run.status == "pending"
    assert run.retry_count == 0
    assert run.max_retries == 2
    assert run.input_json["staging_lead_id"] == "22222222-2222-2222-2222-222222222222"
    assert run.started_at is None
    assert run.finished_at is None
    assert session.get(AgentServiceRun, run.id) is not None


def test_mark_running_then_succeeded_updates_timestamps_and_output(session: Session) -> None:
    service = AgentServiceRunService(session)
    run = service.create_run(
        request_id="11111111-1111-1111-1111-111111111111",
        agent_type="deep_enrichment",
        agent_mode="active",
        trigger_source="manual_api",
        input_json={},
    )

    running = service.mark_running(run.id)
    running_started_at = running.started_at
    running_updated_at = running.updated_at
    succeeded = service.mark_succeeded(run.id, output_json={"field_candidates": []}, output_summary_json={"count": 0})

    assert running_started_at is not None
    assert succeeded.status == "succeeded"
    assert succeeded.output_json == {"field_candidates": []}
    assert succeeded.output_summary_json == {"count": 0}
    assert succeeded.started_at == running_started_at
    assert succeeded.finished_at is not None
    assert succeeded.updated_at >= running_updated_at


def test_mark_failed_records_error_type_and_message(session: Session) -> None:
    service = AgentServiceRunService(session)
    run = service.create_run(
        request_id="11111111-1111-1111-1111-111111111111",
        agent_type="lead_cleanup",
        agent_mode="active",
        trigger_source="manual_api",
        input_json={},
    )

    service.mark_running(run.id)
    failed = service.mark_failed(run.id, error_type="schema_validation_error", error_message="missing evidence")

    assert failed.status == "failed"
    assert failed.error_type == "schema_validation_error"
    assert failed.error_message == "missing evidence"
    assert failed.finished_at is not None


def test_retrying_blocked_and_cancelled_transitions(session: Session) -> None:
    service = AgentServiceRunService(session)
    retry_run = service.create_run(
        request_id="11111111-1111-1111-1111-111111111111",
        agent_type="source_discovery",
        agent_mode="shadow",
        trigger_source="shadow_run",
        input_json={},
    )
    blocked_run = service.create_run(
        request_id="22222222-2222-2222-2222-222222222222",
        agent_type="source_discovery",
        agent_mode="shadow",
        trigger_source="shadow_run",
        input_json={},
    )
    cancelled_run = service.create_run(
        request_id="33333333-3333-3333-3333-333333333333",
        agent_type="source_discovery",
        agent_mode="shadow",
        trigger_source="shadow_run",
        input_json={},
    )

    service.mark_running(retry_run.id)
    retrying = service.mark_retrying(retry_run.id, error_type="timeout_error", error_message="provider timeout")
    blocked = service.mark_blocked(blocked_run.id, error_type="risk_blocked", error_message="Forbidden source")
    cancelled = service.mark_cancelled(cancelled_run.id)

    assert retrying.status == "retrying"
    assert retrying.retry_count == 1
    assert retrying.error_type == "timeout_error"
    assert retrying.finished_at is None
    assert blocked.status == "blocked"
    assert blocked.finished_at is not None
    assert cancelled.status == "cancelled"
    assert cancelled.finished_at is not None


def test_terminal_status_rejects_further_transitions(session: Session) -> None:
    service = AgentServiceRunService(session)
    run = service.create_run(
        request_id="11111111-1111-1111-1111-111111111111",
        agent_type="lead_extraction_grading",
        agent_mode="shadow",
        trigger_source="shadow_run",
        input_json={},
    )

    service.mark_running(run.id)
    service.mark_succeeded(run.id, output_json={"accepted": True})

    with pytest.raises(InvalidAgentRunTransition):
        service.mark_failed(run.id, error_type="timeout_error", error_message="late failure")


def test_get_run_returns_existing_run(session: Session) -> None:
    service = AgentServiceRunService(session)
    run = service.create_run(
        request_id="11111111-1111-1111-1111-111111111111",
        agent_type="deep_enrichment",
        agent_mode="active",
        trigger_source="manual_api",
        input_json={},
    )

    found = service.get_run(run.id)

    assert found.id == run.id
