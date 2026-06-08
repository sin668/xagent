from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.schemas.agent_run import (
    AGENT_RUN_SCHEMA_VERSION,
    AgentRunAudit,
    AgentRunError,
    AgentRunOptions,
    AgentRunRequest,
    AgentRunResponse,
)


def test_agent_run_request_accepts_phase4_envelope() -> None:
    request = AgentRunRequest(
        request_id="11111111-1111-1111-1111-111111111111",
        agent_task_run_id="22222222-2222-2222-2222-222222222222",
        trigger_source="manual_api",
        agent_mode="active",
        input={"staging_lead_id": "33333333-3333-3333-3333-333333333333"},
        options=AgentRunOptions(max_retries=2, timeout_seconds=120),
    )

    assert isinstance(request.request_id, UUID)
    assert isinstance(request.agent_task_run_id, UUID)
    assert request.trigger_source == "manual_api"
    assert request.agent_mode == "active"
    assert request.input["staging_lead_id"] == "33333333-3333-3333-3333-333333333333"
    assert request.options.max_retries == 2
    assert request.options.timeout_seconds == 120
    assert request.options.dry_run is False
    assert request.options.shadow_mode is False


def test_agent_run_response_accepts_phase4_envelope_and_audit_defaults() -> None:
    response = AgentRunResponse(
        agent_service_run_id="44444444-4444-4444-4444-444444444444",
        request_id="11111111-1111-1111-1111-111111111111",
        status="running",
        agent_type="deep_enrichment",
        agent_mode="active",
        output=None,
    )

    assert response.schema_version == AGENT_RUN_SCHEMA_VERSION
    assert isinstance(response.agent_service_run_id, UUID)
    assert isinstance(response.request_id, UUID)
    assert response.status == "running"
    assert response.audit.writes_core_tables is False
    assert response.audit.executed_nodes == []
    assert response.audit.failed_node is None
    assert response.error is None


def test_agent_run_response_supports_required_statuses_and_error_payload() -> None:
    for status in ("succeeded", "failed", "blocked", "running", "retrying"):
        response = AgentRunResponse(
            agent_service_run_id="44444444-4444-4444-4444-444444444444",
            request_id="11111111-1111-1111-1111-111111111111",
            status=status,
            agent_type="lead_cleanup",
            agent_mode="active",
            output={"accepted": status == "succeeded"},
            audit=AgentRunAudit(executed_nodes=["load_cleanup_scope"]),
            error=AgentRunError(error_type="timeout_error", message="LLM timeout") if status == "failed" else None,
        )

        assert response.status == status


def test_agent_run_envelope_rejects_unknown_status_and_core_table_writes() -> None:
    with pytest.raises(ValidationError):
        AgentRunResponse(
            agent_service_run_id="44444444-4444-4444-4444-444444444444",
            request_id="11111111-1111-1111-1111-111111111111",
            status="completed",
            agent_type="deep_enrichment",
            agent_mode="active",
        )

    with pytest.raises(ValidationError):
        AgentRunResponse(
            agent_service_run_id="44444444-4444-4444-4444-444444444444",
            request_id="11111111-1111-1111-1111-111111111111",
            status="succeeded",
            agent_type="deep_enrichment",
            agent_mode="active",
            audit=AgentRunAudit(writes_core_tables=True),
        )


def test_agent_run_schema_is_visible_in_openapi() -> None:
    app = FastAPI()

    @app.post("/agent-runs/example", response_model=AgentRunResponse)
    def run_agent(request: AgentRunRequest) -> AgentRunResponse:
        return AgentRunResponse(
            agent_service_run_id="44444444-4444-4444-4444-444444444444",
            request_id=request.request_id,
            status="running",
            agent_type="source_discovery",
            agent_mode="shadow",
        )

    client = TestClient(app)
    openapi = client.get("/openapi.json").json()

    assert "AgentRunRequest" in openapi["components"]["schemas"]
    assert "AgentRunResponse" in openapi["components"]["schemas"]
    assert "/agent-runs/example" in openapi["paths"]
