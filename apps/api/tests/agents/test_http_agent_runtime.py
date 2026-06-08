import httpx
import pytest

from app.agents.http_runtime import (
    HttpAgentRuntime,
    HttpAgentRuntimeAuthError,
    HttpAgentRuntimeConfigurationError,
    HttpAgentRuntimeServerError,
    HttpAgentRuntimeTimeoutError,
    HttpAgentRuntimeValidationError,
)
from app.settings import Settings


def build_settings(api_key: str | None = "agents-test-key") -> Settings:
    return Settings(
        _env_file=None,
        AGENTS_BASE_URL="http://agents.local:8010",
        AGENTS_API_KEY=api_key or "",
        AGENTS_TIMEOUT_SECONDS="15",
    )


@pytest.mark.asyncio
async def test_http_agent_runtime_default_client_ignores_environment_proxy(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    class FakeAsyncClient:
        def __init__(self, **kwargs):
            captured["client_kwargs"] = kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback):
            return None

        async def post(self, url, *, json, headers):
            captured["url"] = url
            return httpx.Response(
                200,
                json={
                    "schema_version": "phase4.agent.run.v1",
                    "agent_service_run_id": "44444444-4444-4444-4444-444444444444",
                    "request_id": "11111111-1111-1111-1111-111111111111",
                    "status": "succeeded",
                    "agent_type": "source_discovery",
                    "agent_mode": "shadow",
                    "output": {},
                    "audit": {"writes_core_tables": False, "executed_nodes": []},
                    "error": None,
                },
            )

    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)

    runtime = HttpAgentRuntime(settings=build_settings())
    await runtime.run_agent(
        "source-discovery",
        request_id="11111111-1111-1111-1111-111111111111",
        trigger_source="scheduler",
        agent_mode="shadow",
        input_payload={},
    )

    assert captured["client_kwargs"]["trust_env"] is False
    assert captured["url"] == "http://agents.local:8010/agent-runs/source-discovery"


def test_http_agent_runtime_error_message_includes_422_detail_list() -> None:
    request = httpx.Request("POST", "http://agents.local:8010/agent-runs/source-discovery")
    response = httpx.Response(
        422,
        request=request,
        json={
            "detail": [
                {
                    "type": "literal_error",
                    "loc": ["body", "trigger_source"],
                    "msg": "Input should be 'manual_api', 'shadow_run', 'scheduler' or 'test'",
                }
            ]
        },
    )

    message = HttpAgentRuntime(settings=build_settings())._error_message(response, response.json())

    assert "HTTP 422" in message
    assert "trigger_source" in message
    assert "scheduler" in message


@pytest.mark.asyncio
async def test_http_agent_runtime_posts_unified_envelope_with_api_key() -> None:
    captured_request: dict[str, object] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured_request["method"] = request.method
        captured_request["url"] = str(request.url)
        captured_request["api_key"] = request.headers.get("X-Agents-Api-Key")
        captured_request["payload"] = httpx.Response(200, request=request, content=request.content).json()
        return httpx.Response(
            200,
            json={
                "schema_version": "phase4.agent.run.v1",
                "agent_service_run_id": "44444444-4444-4444-4444-444444444444",
                "request_id": "11111111-1111-1111-1111-111111111111",
                "status": "succeeded",
                "agent_type": "deep_enrichment",
                "agent_mode": "active",
                "output": {"field_candidates": []},
                "audit": {"writes_core_tables": False, "executed_nodes": []},
                "error": None,
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        runtime = HttpAgentRuntime(settings=build_settings(), http_client=http_client)
        response = await runtime.run_agent(
            "deep-enrichment",
            request_id="11111111-1111-1111-1111-111111111111",
            agent_task_run_id="22222222-2222-2222-2222-222222222222",
            trigger_source="manual_api",
            agent_mode="active",
            input_payload={"staging_lead_id": "33333333-3333-3333-3333-333333333333"},
            options={"max_retries": 2, "timeout_seconds": 120},
        )

    assert captured_request["method"] == "POST"
    assert captured_request["url"] == "http://agents.local:8010/agent-runs/deep-enrichment"
    assert captured_request["api_key"] == "agents-test-key"
    assert captured_request["payload"] == {
        "request_id": "11111111-1111-1111-1111-111111111111",
        "agent_task_run_id": "22222222-2222-2222-2222-222222222222",
        "trigger_source": "manual_api",
        "agent_mode": "active",
        "input": {"staging_lead_id": "33333333-3333-3333-3333-333333333333"},
        "options": {"max_retries": 2, "timeout_seconds": 120},
    }
    assert response["schema_version"] == "phase4.agent.run.v1"
    assert response["agent_service_run_id"] == "44444444-4444-4444-4444-444444444444"
    assert response["status"] == "succeeded"
    assert response["output"] == {"field_candidates": []}


@pytest.mark.asyncio
async def test_http_agent_runtime_rejects_missing_api_key_without_http_call() -> None:
    called = False

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal called
        called = True
        return httpx.Response(200, json={})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        runtime = HttpAgentRuntime(settings=build_settings(api_key=None), http_client=http_client)
        with pytest.raises(HttpAgentRuntimeConfigurationError):
            await runtime.run_agent(
                "deep-enrichment",
                request_id="11111111-1111-1111-1111-111111111111",
                trigger_source="manual_api",
                agent_mode="active",
                input_payload={},
            )

    assert called is False


@pytest.mark.asyncio
async def test_http_agent_runtime_maps_401_to_auth_error() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"detail": "invalid api key"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        runtime = HttpAgentRuntime(settings=build_settings(), http_client=http_client)
        with pytest.raises(HttpAgentRuntimeAuthError) as exc_info:
            await runtime.run_agent(
                "lead-cleanup",
                request_id="11111111-1111-1111-1111-111111111111",
                trigger_source="manual_api",
                agent_mode="active",
                input_payload={},
            )

    assert exc_info.value.status_code == 401
    assert "invalid api key" in str(exc_info.value)


@pytest.mark.asyncio
async def test_http_agent_runtime_maps_4xx_to_validation_error() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(422, json={"detail": "invalid envelope"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        runtime = HttpAgentRuntime(settings=build_settings(), http_client=http_client)
        with pytest.raises(HttpAgentRuntimeValidationError) as exc_info:
            await runtime.run_agent(
                "source-discovery",
                request_id="11111111-1111-1111-1111-111111111111",
                trigger_source="shadow_run",
                agent_mode="shadow",
                input_payload={},
            )

    assert exc_info.value.status_code == 422
    assert "invalid envelope" in str(exc_info.value)


@pytest.mark.asyncio
async def test_http_agent_runtime_maps_5xx_to_server_error() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"detail": "agents unavailable"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        runtime = HttpAgentRuntime(settings=build_settings(), http_client=http_client)
        with pytest.raises(HttpAgentRuntimeServerError) as exc_info:
            await runtime.run_agent(
                "lead-extraction-grading",
                request_id="11111111-1111-1111-1111-111111111111",
                trigger_source="shadow_run",
                agent_mode="shadow",
                input_payload={},
            )

    assert exc_info.value.status_code == 503
    assert "agents unavailable" in str(exc_info.value)


@pytest.mark.asyncio
async def test_http_agent_runtime_maps_timeout_to_timeout_error() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("agents timeout", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        runtime = HttpAgentRuntime(settings=build_settings(), http_client=http_client)
        with pytest.raises(HttpAgentRuntimeTimeoutError) as exc_info:
            await runtime.run_agent(
                "deep-enrichment",
                request_id="11111111-1111-1111-1111-111111111111",
                trigger_source="manual_api",
                agent_mode="active",
                input_payload={},
            )

    assert "agents timeout" in str(exc_info.value)


@pytest.mark.asyncio
async def test_http_agent_runtime_rejects_invalid_response_envelope() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"status": "ok"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        runtime = HttpAgentRuntime(settings=build_settings(), http_client=http_client)
        with pytest.raises(HttpAgentRuntimeValidationError) as exc_info:
            await runtime.run_agent(
                "deep-enrichment",
                request_id="11111111-1111-1111-1111-111111111111",
                trigger_source="manual_api",
                agent_mode="active",
                input_payload={},
            )

    assert exc_info.value.status_code == 200
    assert "phase4.agent.run.v1" in str(exc_info.value)


def test_http_agent_runtime_posts_email_reply_response_contract() -> None:
    captured_request: dict[str, object] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured_request["method"] = request.method
        captured_request["url"] = str(request.url)
        captured_request["api_key"] = request.headers.get("X-Agents-Api-Key")
        captured_request["payload"] = httpx.Response(200, request=request, content=request.content).json()
        return httpx.Response(
            200,
            json={
                "schema_version": "phase4.agent.run.v1",
                "agent_service_run_id": "44444444-4444-4444-4444-444444444444",
                "request_id": "11111111-1111-1111-1111-111111111111",
                "status": "succeeded",
                "agent_type": "email_reply",
                "agent_mode": "active",
                "output": {
                    "schema_version": "email-reply-v1",
                    "suggested_subject": "Vehicle procurement follow-up",
                    "suggested_body": "Hello, thanks for your message.",
                    "knowledge_hits": [],
                    "auto_send_allowed": False,
                    "manual_review_required": True,
                    "manual_review_reason": "需要人工确认。",
                    "audit": {"model": "deepseek-chat"},
                },
                "audit": {"writes_core_tables": False, "executed_nodes": ["load_context", "draft_reply"]},
                "error": None,
            },
        )

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    try:
        runtime = HttpAgentRuntime(settings=build_settings(), http_client=http_client)
        response = runtime.run_email_reply_response(
            request_id="11111111-1111-1111-1111-111111111111",
            agent_task_run_id="22222222-2222-2222-2222-222222222222",
            thread_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            message_id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            customer_id="cccccccc-cccc-cccc-cccc-cccccccccccc",
            draft_id="dddddddd-dddd-dddd-dddd-dddddddddddd",
            context={"customer": {"name": "OOO Test"}},
            prompt={"task_type": "EMAIL_REPLY_DRAFT", "version": "v1"},
            options={"tone": "concise"},
            agent_mode="active",
            dry_run=True,
        )
    finally:
        __import__("asyncio").run(http_client.aclose())

    assert captured_request["method"] == "POST"
    assert captured_request["url"] == "http://agents.local:8010/agent-runs/email-reply"
    assert captured_request["api_key"] == "agents-test-key"
    assert captured_request["payload"] == {
        "request_id": "11111111-1111-1111-1111-111111111111",
        "agent_task_run_id": "22222222-2222-2222-2222-222222222222",
        "trigger_source": "phase5_email_reply_runtime",
        "agent_mode": "active",
        "input": {
            "thread_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "message_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            "customer_id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
            "draft_id": "dddddddd-dddd-dddd-dddd-dddddddddddd",
            "context": {"customer": {"name": "OOO Test"}},
            "prompt": {"task_type": "EMAIL_REPLY_DRAFT", "version": "v1"},
            "options": {"tone": "concise"},
        },
        "options": {"timeout_seconds": 15, "dry_run": True},
    }
    assert response["agent_service_run_id"] == "44444444-4444-4444-4444-444444444444"
    assert response["output"]["schema_version"] == "email-reply-v1"
