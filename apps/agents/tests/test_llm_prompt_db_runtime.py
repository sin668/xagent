from __future__ import annotations

import json

import httpx

from app.graphs.lead_extraction import LLMLeadFieldExtractor
from app.services.llm_client import LLMClient
from app.services.llm_prompt_repository import LoadedLLMPromptTemplate
from app.settings import AgentSettings


class RecordingPromptRepository:
    def __init__(self) -> None:
        self.requests: list[dict[str, str]] = []

    def load_active_default(self, *, task_type: str, provider: str, model: str) -> LoadedLLMPromptTemplate:
        self.requests.append({"task_type": task_type, "provider": provider, "model": model})
        return LoadedLLMPromptTemplate(
            template_id="11111111-1111-1111-1111-111111111111",
            name="lead_extraction_db_default",
            task_type=task_type,
            provider=provider,
            model=model,
            system_prompt="DB ONLY SYSTEM PROMPT",
            user_prompt_template="DB ONLY USER PROMPT {{source_url}} {{source_content}}",
            output_schema_json={"type": "object", "required": ["fields"]},
            version="db-v1",
        )


def test_llm_extractor_uses_database_prompt_template_instead_of_code_prompt() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["payload"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": json.dumps({"fields": {"email": "sales@example.com"}})}}],
                "usage": {"total_tokens": 12},
            },
        )

    settings = AgentSettings(
        agents_api_key="agent-secret",
        database_url="sqlite:///./agents.db",
        llm_provider="deepseek",
        llm_api_key="sk-test",
        llm_base_url="https://api.deepseek.com/v1",
        llm_default_model="deepseek-chat",
    )
    repository = RecordingPromptRepository()
    extractor = LLMLeadFieldExtractor(
        llm_client=LLMClient(settings=settings, http_client=httpx.Client(transport=httpx.MockTransport(handler))),
        prompt_repository=repository,
    )

    fields = extractor.extract(source_url="https://dealer.example", source_content="Email sales@example.com")

    assert fields["email"] == "sales@example.com"
    assert repository.requests == [
        {"task_type": "LEAD_EXTRACTION", "provider": "deepseek", "model": "deepseek-chat"}
    ]
    payload = captured["payload"]
    messages = payload["messages"]  # type: ignore[index]
    assert messages[0]["content"] == "DB ONLY SYSTEM PROMPT"
    assert "DB ONLY USER PROMPT https://dealer.example Email sales@example.com" in messages[1]["content"]
    assert "公开网页线索抽取 Agent" not in messages[0]["content"]
    assert extractor.last_audit["prompt_template_id"] == "11111111-1111-1111-1111-111111111111"
    assert extractor.last_audit["prompt_version"] == "db-v1"
