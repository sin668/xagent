import pytest

from app.services.llm_client import LLMClientResult
from app.services.llm_fallback import LLMFallbackPolicy, LLMFallbackService


def make_result(
    *,
    provider: str,
    model: str = "deepseek-chat",
    output_json: dict | None = None,
    error_type: str | None = None,
) -> LLMClientResult:
    return LLMClientResult(
        provider=provider,
        model=model,
        base_url=f"https://{provider}.example.com/v1",
        latency_ms=10,
        token_usage={"total_tokens": 1} if output_json else None,
        output_json=output_json,
        raw_response={"provider": provider} if output_json else None,
        error={"type": error_type, "message": f"{provider} {error_type}"} if error_type else None,
    )


class MockProvider:
    def __init__(self, provider: str, result: LLMClientResult) -> None:
        self.provider = provider
        self.result = result
        self.calls: list[dict] = []

    async def generate_json(self, task_type: str, system_prompt: str, user_prompt: str, output_schema: dict):
        self.calls.append(
            {
                "task_type": task_type,
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "output_schema": output_schema,
            }
        )
        return self.result


@pytest.mark.asyncio
async def test_technical_network_failure_can_fallback_and_preserve_primary_error() -> None:
    primary = MockProvider("deepseek", make_result(provider="deepseek", error_type="network_error"))
    fallback = MockProvider("qwen", make_result(provider="qwen", output_json={"ok": True}))
    service = LLMFallbackService(primary_client=primary, fallback_client=fallback)

    result = await service.generate_json_with_fallback("SOURCE_DISCOVERY", "system", "user", {"type": "object"})

    assert len(primary.calls) == 1
    assert len(fallback.calls) == 1
    assert result.output_json == {"ok": True}
    assert result.error is None
    assert result.provider == "qwen"
    assert result.fallback_used is True
    assert result.primary_provider_error == {"type": "network_error", "message": "deepseek network_error"}
    assert result.fallback_provider == "qwen"


@pytest.mark.asyncio
async def test_timeout_and_rate_limit_are_fallback_eligible() -> None:
    for error_type in ("timeout_error", "rate_limit_error"):
        primary = MockProvider("deepseek", make_result(provider="deepseek", error_type=error_type))
        fallback = MockProvider("qwen", make_result(provider="qwen", output_json={"ok": error_type}))
        service = LLMFallbackService(primary_client=primary, fallback_client=fallback)

        result = await service.generate_json_with_fallback("SOURCE_DISCOVERY", "system", "user", {"type": "object"})

        assert result.fallback_used is True
        assert result.output_json == {"ok": error_type}
        assert result.primary_provider_error["type"] == error_type


@pytest.mark.asyncio
async def test_schema_fabrication_and_risk_block_failures_never_fallback() -> None:
    blocked_errors = ("schema_validation_error", "suspected_fabrication", "risk_blocked", "forbidden_risk", "high_risk_blocked")

    for error_type in blocked_errors:
        primary = MockProvider("deepseek", make_result(provider="deepseek", error_type=error_type))
        fallback = MockProvider("qwen", make_result(provider="qwen", output_json={"should_not": "run"}))
        service = LLMFallbackService(primary_client=primary, fallback_client=fallback)

        result = await service.generate_json_with_fallback("LEAD_EXTRACTION", "system", "user", {"type": "object"})

        assert len(primary.calls) == 1
        assert fallback.calls == []
        assert result.provider == "deepseek"
        assert result.error["type"] == error_type
        assert result.fallback_used is False
        assert result.primary_provider_error == primary.result.error
        assert result.fallback_provider is None


@pytest.mark.asyncio
async def test_primary_success_does_not_call_fallback() -> None:
    primary = MockProvider("deepseek", make_result(provider="deepseek", output_json={"primary": True}))
    fallback = MockProvider("qwen", make_result(provider="qwen", output_json={"fallback": True}))
    service = LLMFallbackService(primary_client=primary, fallback_client=fallback)

    result = await service.generate_json_with_fallback("SOURCE_DISCOVERY", "system", "user", {"type": "object"})

    assert len(primary.calls) == 1
    assert fallback.calls == []
    assert result.output_json == {"primary": True}
    assert result.fallback_used is False
    assert result.primary_provider_error is None
    assert result.fallback_provider is None


def test_fallback_policy_only_allows_technical_failures() -> None:
    assert LLMFallbackPolicy.should_fallback({"type": "network_error"}) is True
    assert LLMFallbackPolicy.should_fallback({"type": "timeout_error"}) is True
    assert LLMFallbackPolicy.should_fallback({"type": "rate_limit_error"}) is True

    assert LLMFallbackPolicy.should_fallback({"type": "schema_validation_error"}) is False
    assert LLMFallbackPolicy.should_fallback({"type": "suspected_fabrication"}) is False
    assert LLMFallbackPolicy.should_fallback({"type": "risk_blocked"}) is False
    assert LLMFallbackPolicy.should_fallback({"type": "forbidden_risk"}) is False
    assert LLMFallbackPolicy.should_fallback({"type": "high_risk_blocked"}) is False
    assert LLMFallbackPolicy.should_fallback(None) is False
