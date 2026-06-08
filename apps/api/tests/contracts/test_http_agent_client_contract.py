import httpx
import pytest

from app.agents.http_runtime import (
    HttpAgentRuntime,
    HttpAgentRuntimeAuthError,
    HttpAgentRuntimeServerError,
    HttpAgentRuntimeTimeoutError,
    HttpAgentRuntimeValidationError,
)
from app.settings import Settings
from tests.fixtures.http_agent_contracts import AGENT_TASK_RUN_ID, REQUEST_ID, success_response


def build_settings() -> Settings:
    return Settings(
        _env_file=None,
        AGENTS_BASE_URL="http://agents.local:8010",
        AGENTS_API_KEY="agents-contract-key",
        AGENTS_TIMEOUT_SECONDS="15",
    )


@pytest.mark.asyncio
async def test_contract_accepts_2xx_success_envelope_and_request_contract() -> None:
    captured_request: dict[str, object] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured_request["url"] = str(request.url)
        captured_request["api_key"] = request.headers.get("X-Agents-Api-Key")
        captured_request["payload"] = httpx.Response(200, request=request, content=request.content).json()
        return httpx.Response(200, json=success_response())

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        runtime = HttpAgentRuntime(settings=build_settings(), http_client=http_client)
        response = await runtime.run_agent(
            "deep-enrichment",
            request_id=REQUEST_ID,
            agent_task_run_id=AGENT_TASK_RUN_ID,
            trigger_source="manual_api",
            agent_mode="active",
            input_payload={"staging_lead_id": "33333333-3333-3333-3333-333333333333"},
            options={"max_retries": 2, "timeout_seconds": 120},
        )

    assert captured_request["url"] == "http://agents.local:8010/agent-runs/deep-enrichment"
    assert captured_request["api_key"] == "agents-contract-key"
    assert captured_request["payload"] == {
        "request_id": REQUEST_ID,
        "agent_task_run_id": AGENT_TASK_RUN_ID,
        "trigger_source": "manual_api",
        "agent_mode": "active",
        "input": {"staging_lead_id": "33333333-3333-3333-3333-333333333333"},
        "options": {"max_retries": 2, "timeout_seconds": 120},
    }
    assert response["schema_version"] == "phase4.agent.run.v1"
    assert response["agent_service_run_id"]
    assert response["audit"]["writes_core_tables"] is False


@pytest.mark.asyncio
async def test_contract_maps_401_auth_failure() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"detail": "invalid agents api key"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        runtime = HttpAgentRuntime(settings=build_settings(), http_client=http_client)
        with pytest.raises(HttpAgentRuntimeAuthError) as exc_info:
            await runtime.run_agent(
                "deep-enrichment",
                request_id=REQUEST_ID,
                trigger_source="manual_api",
                agent_mode="active",
                input_payload={},
            )

    assert exc_info.value.status_code == 401
    assert "invalid agents api key" in str(exc_info.value)


@pytest.mark.asyncio
async def test_contract_maps_4xx_business_error() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(422, json={"detail": "schema_validation_error"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        runtime = HttpAgentRuntime(settings=build_settings(), http_client=http_client)
        with pytest.raises(HttpAgentRuntimeValidationError) as exc_info:
            await runtime.run_agent(
                "source-discovery",
                request_id=REQUEST_ID,
                trigger_source="shadow_run",
                agent_mode="shadow",
                input_payload={},
            )

    assert exc_info.value.status_code == 422
    assert "schema_validation_error" in str(exc_info.value)


@pytest.mark.asyncio
async def test_contract_maps_5xx_service_error() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"detail": "agents service unavailable"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        runtime = HttpAgentRuntime(settings=build_settings(), http_client=http_client)
        with pytest.raises(HttpAgentRuntimeServerError) as exc_info:
            await runtime.run_agent(
                "lead-cleanup",
                request_id=REQUEST_ID,
                trigger_source="manual_api",
                agent_mode="active",
                input_payload={},
            )

    assert exc_info.value.status_code == 503
    assert "agents service unavailable" in str(exc_info.value)


@pytest.mark.asyncio
async def test_contract_maps_timeout_without_real_llm_call() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("contract timeout", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        runtime = HttpAgentRuntime(settings=build_settings(), http_client=http_client)
        with pytest.raises(HttpAgentRuntimeTimeoutError) as exc_info:
            await runtime.run_agent(
                "deep-enrichment",
                request_id=REQUEST_ID,
                trigger_source="manual_api",
                agent_mode="active",
                input_payload={},
            )

    assert "contract timeout" in str(exc_info.value)


@pytest.mark.asyncio
async def test_contract_rejects_success_envelope_that_claims_core_table_writes() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=success_response(audit={"writes_core_tables": True, "executed_nodes": []}))

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        runtime = HttpAgentRuntime(settings=build_settings(), http_client=http_client)
        with pytest.raises(HttpAgentRuntimeValidationError) as exc_info:
            await runtime.run_agent(
                "deep-enrichment",
                request_id=REQUEST_ID,
                trigger_source="manual_api",
                agent_mode="active",
                input_payload={},
            )

    assert "writes_core_tables" in str(exc_info.value)
