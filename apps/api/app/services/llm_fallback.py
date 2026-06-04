from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from app.services.llm_client import LLMClientResult


class LLMGenerateJsonClient(Protocol):
    async def generate_json(
        self,
        task_type: str,
        system_prompt: str,
        user_prompt: str,
        output_schema: dict[str, Any],
    ) -> LLMClientResult:
        ...


@dataclass(frozen=True)
class LLMFallbackResult:
    provider: str
    model: str
    base_url: str | None
    latency_ms: int
    token_usage: dict[str, Any] | None
    output_json: dict[str, Any] | list[Any] | None
    raw_response: dict[str, Any] | None
    error: dict[str, str] | None
    fallback_used: bool
    primary_provider_error: dict[str, str] | None
    fallback_provider: str | None


class LLMFallbackPolicy:
    TECHNICAL_ERROR_TYPES = frozenset({"network_error", "timeout_error", "rate_limit_error"})

    @classmethod
    def should_fallback(cls, error: dict[str, str] | None) -> bool:
        if not error:
            return False
        return error.get("type") in cls.TECHNICAL_ERROR_TYPES


class LLMFallbackService:
    def __init__(self, *, primary_client: LLMGenerateJsonClient, fallback_client: LLMGenerateJsonClient | None) -> None:
        self.primary_client = primary_client
        self.fallback_client = fallback_client

    async def generate_json_with_fallback(
        self,
        task_type: str,
        system_prompt: str,
        user_prompt: str,
        output_schema: dict[str, Any],
    ) -> LLMFallbackResult:
        primary_result = await self.primary_client.generate_json(task_type, system_prompt, user_prompt, output_schema)
        primary_error = primary_result.error

        if not self._can_fallback(primary_error):
            return self._from_client_result(
                primary_result,
                fallback_used=False,
                primary_provider_error=primary_error,
                fallback_provider=None,
            )

        fallback_result = await self.fallback_client.generate_json(task_type, system_prompt, user_prompt, output_schema)
        return self._from_client_result(
            fallback_result,
            fallback_used=True,
            primary_provider_error=primary_error,
            fallback_provider=fallback_result.provider,
        )

    def _can_fallback(self, error: dict[str, str] | None) -> bool:
        return self.fallback_client is not None and LLMFallbackPolicy.should_fallback(error)

    def _from_client_result(
        self,
        result: LLMClientResult,
        *,
        fallback_used: bool,
        primary_provider_error: dict[str, str] | None,
        fallback_provider: str | None,
    ) -> LLMFallbackResult:
        return LLMFallbackResult(
            provider=result.provider,
            model=result.model,
            base_url=result.base_url,
            latency_ms=result.latency_ms,
            token_usage=result.token_usage,
            output_json=result.output_json,
            raw_response=result.raw_response,
            error=result.error,
            fallback_used=fallback_used,
            primary_provider_error=primary_provider_error,
            fallback_provider=fallback_provider,
        )
