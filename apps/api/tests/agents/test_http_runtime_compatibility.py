import httpx
import pytest

from app.agents.http_runtime import HttpAgentRuntime, HttpAgentRuntimeValidationError
from app.settings import Settings


def build_settings() -> Settings:
    return Settings(
        _env_file=None,
        AGENTS_BASE_URL="http://agents.local:8010",
        AGENTS_API_KEY="agents-test-key",
        AGENTS_TIMEOUT_SECONDS="15",
    )


def phase4_response(*, agent_type: str, agent_mode: str, output: dict | None, status: str = "succeeded") -> dict:
    return {
        "schema_version": "phase4.agent.run.v1",
        "agent_service_run_id": "44444444-4444-4444-4444-444444444444",
        "request_id": "11111111-1111-1111-1111-111111111111",
        "status": status,
        "agent_type": agent_type,
        "agent_mode": agent_mode,
        "output": output,
        "audit": {"writes_core_tables": False, "executed_nodes": []},
        "error": None,
    }


def test_run_deep_enrichment_converts_existing_call_to_http_agent_request() -> None:
    captured_request: dict[str, object] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured_request["url"] = str(request.url)
        captured_request["api_key"] = request.headers.get("X-Agents-Api-Key")
        captured_request["payload"] = httpx.Response(200, request=request, content=request.content).json()
        return httpx.Response(
            200,
            json=phase4_response(
                agent_type="deep_enrichment",
                agent_mode="active",
                output={
                    "schema_version": "phase3.agent.deep_enrichment.v1",
                    "agent_run_id": "22222222-2222-2222-2222-222222222222",
                    "staging_lead_id": "33333333-3333-3333-3333-333333333333",
                    "field_candidates": [],
                    "missing_fields": ["contacts_json"],
                    "recommended_next_action": "continue_enrichment",
                    "audit": {"writes_core_tables": False},
                },
            ),
        )

    runtime = HttpAgentRuntime(
        settings=build_settings(),
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    output = runtime.run_deep_enrichment(
        agent_run_id="22222222-2222-2222-2222-222222222222",
        staging_lead_id="33333333-3333-3333-3333-333333333333",
        lead_snapshot={"customer_name": "Ru Auto City"},
        missing_fields=["contacts_json"],
    )

    assert captured_request["url"] == "http://agents.local:8010/agent-runs/deep-enrichment"
    assert captured_request["api_key"] == "agents-test-key"
    assert captured_request["payload"] == {
        "request_id": "22222222-2222-2222-2222-222222222222",
        "agent_task_run_id": "22222222-2222-2222-2222-222222222222",
        "trigger_source": "phase3_deep_enrichment_runtime",
        "agent_mode": "active",
        "input": {
            "agent_run_id": "22222222-2222-2222-2222-222222222222",
            "staging_lead_id": "33333333-3333-3333-3333-333333333333",
            "lead_snapshot": {"customer_name": "Ru Auto City"},
            "missing_fields": ["contacts_json"],
        },
        "options": {"timeout_seconds": 15},
    }
    assert output["schema_version"] == "phase3.agent.deep_enrichment.v1"
    assert output["audit"]["writes_core_tables"] is False


def test_run_lead_cleanup_converts_existing_call_to_http_agent_request() -> None:
    captured_request: dict[str, object] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured_request["url"] = str(request.url)
        captured_request["payload"] = httpx.Response(200, request=request, content=request.content).json()
        return httpx.Response(
            200,
            json=phase4_response(
                agent_type="lead_cleanup",
                agent_mode="active",
                output={
                    "schema_version": "phase3.agent.lead_cleanup.v1",
                    "cleanup_run_id": "55555555-5555-5555-5555-555555555555",
                    "suggestions": [],
                    "blocked_items": [],
                    "audit": {"writes_core_tables": False},
                },
            ),
        )

    runtime = HttpAgentRuntime(
        settings=build_settings(),
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    output = runtime.run_lead_cleanup(
        cleanup_run_id="55555555-5555-5555-5555-555555555555",
        leads=[{"staging_lead_id": "66666666-6666-6666-6666-666666666666", "recommended_grade": "Invalid"}],
    )

    assert captured_request["url"] == "http://agents.local:8010/agent-runs/lead-cleanup"
    assert captured_request["payload"] == {
        "request_id": "55555555-5555-5555-5555-555555555555",
        "agent_task_run_id": None,
        "trigger_source": "phase3_lead_cleanup_runtime",
        "agent_mode": "active",
        "input": {
            "cleanup_run_id": "55555555-5555-5555-5555-555555555555",
            "leads": [{"staging_lead_id": "66666666-6666-6666-6666-666666666666", "recommended_grade": "Invalid"}],
        },
        "options": {"timeout_seconds": 15},
    }
    assert output["schema_version"] == "phase3.agent.lead_cleanup.v1"
    assert output["audit"]["writes_core_tables"] is False


def test_compatibility_methods_reject_missing_phase3_output() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=phase4_response(agent_type="deep_enrichment", agent_mode="active", output=None),
        )

    runtime = HttpAgentRuntime(
        settings=build_settings(),
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )

    with pytest.raises(HttpAgentRuntimeValidationError) as exc_info:
        runtime.run_deep_enrichment(
            agent_run_id="22222222-2222-2222-2222-222222222222",
            staging_lead_id="33333333-3333-3333-3333-333333333333",
            lead_snapshot={},
            missing_fields=[],
        )

    assert "output" in str(exc_info.value)


def test_compatibility_methods_reject_non_succeeded_phase4_run() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=phase4_response(
                agent_type="lead_cleanup",
                agent_mode="active",
                status="failed",
                output={
                    "schema_version": "phase3.agent.lead_cleanup.v1",
                    "cleanup_run_id": "55555555-5555-5555-5555-555555555555",
                    "suggestions": [],
                    "blocked_items": [],
                    "audit": {"writes_core_tables": False},
                },
            ),
        )

    runtime = HttpAgentRuntime(
        settings=build_settings(),
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )

    with pytest.raises(HttpAgentRuntimeValidationError) as exc_info:
        runtime.run_lead_cleanup(cleanup_run_id="55555555-5555-5555-5555-555555555555", leads=[])

    assert "succeeded" in str(exc_info.value)
