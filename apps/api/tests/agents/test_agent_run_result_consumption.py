import httpx
import pytest

from app.agents.http_runtime import (
    HttpAgentRuntime,
    HttpAgentRuntimeConfigurationError,
    HttpAgentRuntimeValidationError,
)
from app.settings import Settings


AGENT_SERVICE_RUN_ID = "44444444-4444-4444-4444-444444444444"


def build_settings(api_key: str | None = "agents-test-key") -> Settings:
    return Settings(
        _env_file=None,
        AGENTS_BASE_URL="http://agents.local:8010",
        AGENTS_API_KEY=api_key or "",
        AGENTS_TIMEOUT_SECONDS="15",
    )


def phase4_run_response(
    *,
    status: str,
    output: dict | None = None,
    error: dict | None = None,
) -> dict:
    return {
        "schema_version": "phase4.agent.run.v1",
        "agent_service_run_id": AGENT_SERVICE_RUN_ID,
        "request_id": "11111111-1111-1111-1111-111111111111",
        "status": status,
        "agent_type": "deep_enrichment",
        "agent_mode": "active",
        "output": output,
        "audit": {"writes_core_tables": False, "executed_nodes": []},
        "error": error,
    }


@pytest.mark.asyncio
async def test_get_agent_run_fetches_external_agent_run_by_id() -> None:
    captured_request: dict[str, object] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured_request["method"] = request.method
        captured_request["url"] = str(request.url)
        captured_request["api_key"] = request.headers.get("X-Agents-Api-Key")
        return httpx.Response(
            200,
            json=phase4_run_response(
                status="succeeded",
                output={
                    "schema_version": "phase3.agent.deep_enrichment.v1",
                    "field_candidates": [],
                    "audit": {"writes_core_tables": False},
                },
            ),
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        runtime = HttpAgentRuntime(settings=build_settings(), http_client=http_client)
        result = await runtime.get_agent_run(AGENT_SERVICE_RUN_ID)

    assert captured_request["method"] == "GET"
    assert captured_request["url"] == f"http://agents.local:8010/agent-runs/{AGENT_SERVICE_RUN_ID}"
    assert captured_request["api_key"] == "agents-test-key"
    assert result["status"] == "succeeded"
    assert result["output"]["schema_version"] == "phase3.agent.deep_enrichment.v1"


@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["running", "retrying"])
async def test_get_agent_run_treats_running_and_retrying_as_non_terminal(status: str) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=phase4_run_response(status=status))

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        runtime = HttpAgentRuntime(settings=build_settings(), http_client=http_client)
        result = await runtime.get_agent_run(AGENT_SERVICE_RUN_ID)

    assert result["status"] == status
    assert result["is_terminal"] is False
    assert result["is_success"] is False
    assert result["is_failure"] is False
    assert result["output"] is None


@pytest.mark.asyncio
async def test_get_agent_run_returns_structured_succeeded_output_for_services() -> None:
    output = {
        "schema_version": "phase3.agent.deep_enrichment.v1",
        "field_candidates": [{"field": "contacts_json", "value": [{"type": "phone", "value": "+971500000000"}]}],
        "missing_fields": [],
        "recommended_next_action": "manual_review",
        "audit": {"writes_core_tables": False},
    }

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=phase4_run_response(status="succeeded", output=output))

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        runtime = HttpAgentRuntime(settings=build_settings(), http_client=http_client)
        result = await runtime.get_agent_run(AGENT_SERVICE_RUN_ID)

    assert result["status"] == "succeeded"
    assert result["is_terminal"] is True
    assert result["is_success"] is True
    assert result["is_failure"] is False
    assert result["output"] == output


@pytest.mark.asyncio
async def test_get_agent_run_failed_preserves_error_type_message_and_retryable() -> None:
    error = {
        "error_type": "provider_rate_limited",
        "message": "LLM provider rate limited the run.",
        "retryable": True,
        "failed_node": "call_llm",
    }

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=phase4_run_response(status="failed", error=error))

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        runtime = HttpAgentRuntime(settings=build_settings(), http_client=http_client)
        result = await runtime.get_agent_run(AGENT_SERVICE_RUN_ID)

    assert result["status"] == "failed"
    assert result["is_terminal"] is True
    assert result["is_success"] is False
    assert result["is_failure"] is True
    assert result["error"] == error
    assert result["error_type"] == "provider_rate_limited"
    assert result["error_message"] == "LLM provider rate limited the run."
    assert result["retryable"] is True


@pytest.mark.asyncio
async def test_get_agent_run_rejects_failed_without_structured_error() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=phase4_run_response(status="failed", error=None))

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        runtime = HttpAgentRuntime(settings=build_settings(), http_client=http_client)
        with pytest.raises(HttpAgentRuntimeValidationError) as exc_info:
            await runtime.get_agent_run(AGENT_SERVICE_RUN_ID)

    assert "error" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_agent_run_rejects_missing_api_key_without_http_call() -> None:
    called = False

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal called
        called = True
        return httpx.Response(200, json={})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        runtime = HttpAgentRuntime(settings=build_settings(api_key=None), http_client=http_client)
        with pytest.raises(HttpAgentRuntimeConfigurationError):
            await runtime.get_agent_run(AGENT_SERVICE_RUN_ID)

    assert called is False


@pytest.mark.asyncio
async def test_get_agent_run_rejects_succeeded_without_structured_output() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=phase4_run_response(status="succeeded", output=None))

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        runtime = HttpAgentRuntime(settings=build_settings(), http_client=http_client)
        with pytest.raises(HttpAgentRuntimeValidationError) as exc_info:
            await runtime.get_agent_run(AGENT_SERVICE_RUN_ID)

    assert "output" in str(exc_info.value)
