import httpx
import pytest

from app.services.llm_client import LLMClient, LLMClientResult
from app.settings import Settings


def build_settings(api_key: str | None = "sk-test") -> Settings:
    return Settings(
        _env_file=None,
        LLM_PROVIDER="deepseek",
        LLM_API_KEY=api_key or "",
        LLM_BASE_URL="https://api.deepseek.com/v1",
        LLM_DEFAULT_MODEL="deepseek-chat",
        LLM_SOURCE_DISCOVERY_MODEL="deepseek-source",
        LLM_EXTRACTION_MODEL="deepseek-extraction",
        LLM_GRADING_MODEL="deepseek-grading",
    )


@pytest.mark.asyncio
async def test_llm_client_generate_json_parses_mock_success_response() -> None:
    captured_request: dict[str, object] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured_request["url"] = str(request.url)
        captured_request["authorization"] = request.headers.get("authorization")
        captured_request["json"] = httpx.Response(200, request=request, content=request.content).json()
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl-test",
                "choices": [
                    {
                        "message": {
                            "content": '{"task_type":"SOURCE_DISCOVERY","candidates":[]}',
                        }
                    }
                ],
                "usage": {"prompt_tokens": 12, "completion_tokens": 8, "total_tokens": 20},
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = LLMClient(settings=build_settings(), http_client=http_client)
        result = await client.generate_json(
            task_type="SOURCE_DISCOVERY",
            system_prompt="只输出 JSON。",
            user_prompt="发现俄罗斯车商来源。",
            output_schema={"type": "object"},
        )

    assert isinstance(result, LLMClientResult)
    assert result.provider == "deepseek"
    assert result.model == "deepseek-source"
    assert result.base_url == "https://api.deepseek.com/v1"
    assert result.output_json == {"task_type": "SOURCE_DISCOVERY", "candidates": []}
    assert result.error is None
    assert result.token_usage == {"prompt_tokens": 12, "completion_tokens": 8, "total_tokens": 20}
    assert result.latency_ms >= 0
    assert result.raw_response["id"] == "chatcmpl-test"

    assert captured_request["url"] == "https://api.deepseek.com/v1/chat/completions"
    assert captured_request["authorization"] == "Bearer sk-test"
    payload = captured_request["json"]
    assert payload["model"] == "deepseek-source"
    assert payload["response_format"] == {"type": "json_object"}
    assert payload["messages"][0] == {"role": "system", "content": "只输出 JSON。"}
    assert payload["messages"][1]["role"] == "user"
    assert "发现俄罗斯车商来源。" in payload["messages"][1]["content"]
    assert '"type": "object"' in payload["messages"][1]["content"]


@pytest.mark.asyncio
async def test_llm_client_uses_task_specific_models() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        payload = httpx.Response(200, request=request, content=request.content).json()
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": '{"ok":true,"model":"' + payload["model"] + '"}'}}],
                "usage": {"total_tokens": 1},
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = LLMClient(settings=build_settings(), http_client=http_client)
        extraction = await client.generate_json("LEAD_EXTRACTION", "s", "u", {"type": "object"})
        grading = await client.generate_json("LEAD_GRADING", "s", "u", {"type": "object"})
        unknown = await client.generate_json("UNKNOWN_TASK", "s", "u", {"type": "object"})

    assert extraction.model == "deepseek-extraction"
    assert extraction.output_json["model"] == "deepseek-extraction"
    assert grading.model == "deepseek-grading"
    assert grading.output_json["model"] == "deepseek-grading"
    assert unknown.model == "deepseek-chat"
    assert unknown.output_json["model"] == "deepseek-chat"


@pytest.mark.asyncio
async def test_llm_client_network_failure_returns_structured_error() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("network down", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = LLMClient(settings=build_settings(), http_client=http_client)
        result = await client.generate_json("SOURCE_DISCOVERY", "s", "u", {"type": "object"})

    assert result.output_json is None
    assert result.raw_response is None
    assert result.error is not None
    assert result.error["type"] == "network_error"
    assert "network down" in result.error["message"]
    assert result.provider == "deepseek"
    assert result.model == "deepseek-source"


@pytest.mark.asyncio
async def test_llm_client_missing_api_key_returns_structured_error_without_http_call() -> None:
    called = False

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal called
        called = True
        return httpx.Response(200, json={})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = LLMClient(settings=build_settings(api_key=None), http_client=http_client)
        result = await client.generate_json("SOURCE_DISCOVERY", "s", "u", {"type": "object"})

    assert called is False
    assert result.output_json is None
    assert result.raw_response is None
    assert result.error is not None
    assert result.error["type"] == "configuration_error"
    assert "API key" in result.error["message"]
