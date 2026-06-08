from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.services.agent_service_runs import AgentServiceRunService
from app.services.retry_policy import (
    DEFAULT_MAX_RETRIES,
    NON_RETRYABLE_ERROR_TYPES,
    RETRYABLE_ERROR_TYPES,
    RetryPolicy,
    is_retryable_error,
)


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


def test_retryable_error_type_classification() -> None:
    assert RETRYABLE_ERROR_TYPES == {
        "timeout_error",
        "provider_rate_limited",
        "transient_network_error",
    }
    assert NON_RETRYABLE_ERROR_TYPES == {
        "schema_validation_error",
        "evidence_validation_error",
        "risk_blocked",
        "contract_mismatch",
    }

    for error_type in RETRYABLE_ERROR_TYPES:
        assert is_retryable_error(error_type) is True

    for error_type in NON_RETRYABLE_ERROR_TYPES:
        assert is_retryable_error(error_type) is False

    assert is_retryable_error("unknown_provider_error") is False


def test_retry_policy_defaults_to_two_attempts() -> None:
    policy = RetryPolicy()

    assert DEFAULT_MAX_RETRIES == 2
    assert policy.max_retries == 2


def test_retryable_failure_schedules_next_retry_and_updates_counter(session: Session) -> None:
    service = AgentServiceRunService(session)
    run = service.create_run(
        request_id="11111111-1111-1111-1111-111111111111",
        agent_type="deep_enrichment",
        agent_mode="active",
        trigger_source="manual_api",
        input_json={},
    )
    service.mark_running(run.id)

    before = datetime.now(UTC)
    retrying = service.record_failure_with_retry_policy(
        run.id,
        error_type="timeout_error",
        error_message="provider timeout",
    )

    assert retrying.status == "retrying"
    assert retrying.retry_count == 1
    assert retrying.max_retries == DEFAULT_MAX_RETRIES
    assert retrying.next_retry_at is not None
    assert retrying.next_retry_at.replace(tzinfo=UTC) > before
    assert retrying.error_type == "timeout_error"
    assert retrying.error_message == "provider timeout"
    assert retrying.finished_at is None


def test_retryable_failure_fails_after_max_retries(session: Session) -> None:
    service = AgentServiceRunService(session)
    run = service.create_run(
        request_id="11111111-1111-1111-1111-111111111111",
        agent_type="lead_cleanup",
        agent_mode="active",
        trigger_source="manual_api",
        input_json={},
        max_retries=2,
    )

    service.mark_running(run.id)
    first_retry = service.record_failure_with_retry_policy(
        run.id,
        error_type="provider_rate_limited",
        error_message="rate limited",
    )
    first_retry_count = first_retry.retry_count
    first_retry_status = first_retry.status
    second_retry = service.record_failure_with_retry_policy(
        run.id,
        error_type="provider_rate_limited",
        error_message="rate limited again",
    )
    second_retry_count = second_retry.retry_count
    second_retry_status = second_retry.status
    second_next_retry_at = second_retry.next_retry_at
    failed = service.record_failure_with_retry_policy(
        run.id,
        error_type="provider_rate_limited",
        error_message="rate limited final",
    )

    assert first_retry_status == "retrying"
    assert first_retry_count == 1
    assert second_retry_status == "retrying"
    assert second_retry_count == 2
    assert second_next_retry_at is not None
    assert failed.status == "failed"
    assert failed.retry_count == 2
    assert failed.next_retry_at is None
    assert failed.error_type == "provider_rate_limited"
    assert failed.error_message == "rate limited final"
    assert failed.finished_at is not None


def test_non_retryable_failure_fails_without_incrementing_retry(session: Session) -> None:
    service = AgentServiceRunService(session)
    run = service.create_run(
        request_id="11111111-1111-1111-1111-111111111111",
        agent_type="source_discovery",
        agent_mode="shadow",
        trigger_source="shadow_run",
        input_json={},
    )
    service.mark_running(run.id)

    failed = service.record_failure_with_retry_policy(
        run.id,
        error_type="schema_validation_error",
        error_message="missing required evidence",
    )

    assert failed.status == "failed"
    assert failed.retry_count == 0
    assert failed.next_retry_at is None
    assert failed.error_type == "schema_validation_error"
    assert failed.finished_at is not None
