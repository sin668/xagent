import httpx

from app.services.llm_client import LLMClient, LLMClientResult
from app.settings import AgentSettings


def build_settings(api_key: str = "sk-test") -> AgentSettings:
    return AgentSettings(
        agents_api_key="agent-secret",
        database_url="sqlite:///./agents.db",
        llm_provider="deepseek",
        llm_api_key=api_key,
        llm_base_url="https://api.deepseek.com/v1",
        llm_default_model="deepseek-chat",
        llm_email_reply_model="deepseek-email",
    )


def test_agents_llm_client_calls_openai_compatible_chat_completions_and_parses_json() -> None:
    captured_request: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured_request["url"] = str(request.url)
        captured_request["authorization"] = request.headers.get("authorization")
        captured_request["json"] = httpx.Response(200, request=request, content=request.content).json()
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl-agents-test",
                "choices": [{"message": {"content": '{"schema_version":"email-reply-v1","ok":true}'}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 4, "total_tokens": 14},
            },
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        client = LLMClient(settings=build_settings(), http_client=http_client)
        result = client.generate_json(
            task_type="EMAIL_REPLY",
            system_prompt="只输出 JSON。",
            user_prompt="生成邮件回复。",
            output_schema={"type": "object"},
        )

    assert isinstance(result, LLMClientResult)
    assert result.provider == "deepseek"
    assert result.model == "deepseek-email"
    assert result.base_url == "https://api.deepseek.com/v1"
    assert result.output_json == {"schema_version": "email-reply-v1", "ok": True}
    assert result.error is None
    assert result.token_usage == {"prompt_tokens": 10, "completion_tokens": 4, "total_tokens": 14}
    assert captured_request["url"] == "https://api.deepseek.com/v1/chat/completions"
    assert captured_request["authorization"] == "Bearer sk-test"
    payload = captured_request["json"]
    assert payload["model"] == "deepseek-email"
    assert payload["response_format"] == {"type": "json_object"}
    assert payload["messages"][0] == {"role": "system", "content": "只输出 JSON。"}
    assert "生成邮件回复。" in payload["messages"][1]["content"]
    assert '"type": "object"' in payload["messages"][1]["content"]


def test_agents_llm_client_missing_api_key_returns_configuration_error_without_http_call() -> None:
    called = False

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal called
        called = True
        return httpx.Response(200, json={})

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        client = LLMClient(settings=build_settings(api_key=""), http_client=http_client)
        result = client.generate_json("EMAIL_REPLY", "s", "u", {"type": "object"})

    assert called is False
    assert result.output_json is None
    assert result.error is not None
    assert result.error["type"] == "configuration_error"
    assert "API key" in result.error["message"]
