from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any

import httpx

from app.settings import AgentSettings, get_settings


@dataclass(frozen=True)
class LLMClientResult:
    provider: str
    model: str
    base_url: str | None
    latency_ms: int
    token_usage: dict[str, Any] | None
    output_json: dict[str, Any] | list[Any] | None
    raw_response: dict[str, Any] | None
    error: dict[str, str] | None


class LLMClient:
    def __init__(
        self,
        *,
        settings: AgentSettings | None = None,
        http_client: httpx.Client | None = None,
        timeout_seconds: float = 60.0,
    ) -> None:
        self.settings = settings or get_settings()
        self.http_client = http_client
        self.timeout_seconds = timeout_seconds

    def generate_json(
        self,
        task_type: str,
        system_prompt: str,
        user_prompt: str,
        output_schema: dict[str, Any],
    ) -> LLMClientResult:
        started = time.perf_counter()
        model = self._model_for_task(task_type)
        base_url = self.settings.llm_base_url.rstrip("/") if self.settings.llm_base_url else None
        api_key = (self.settings.llm_api_key or "").strip()

        if not api_key:
            return self._result(
                model=model,
                base_url=base_url,
                started=started,
                error={"type": "configuration_error", "message": "LLM API key is not configured."},
            )
        if not base_url:
            return self._result(
                model=model,
                base_url=base_url,
                started=started,
                error={"type": "configuration_error", "message": "LLM base URL is not configured."},
            )

        payload = self._build_payload(model, system_prompt, user_prompt, output_schema)
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

        try:
            if self.http_client is not None:
                response = self.http_client.post(f"{base_url}/chat/completions", json=payload, headers=headers)
            else:
                with httpx.Client(timeout=self.timeout_seconds) as client:
                    response = client.post(f"{base_url}/chat/completions", json=payload, headers=headers)
            response.raise_for_status()
            raw_response = response.json()
            output_json = self._parse_output_json(raw_response)
        except httpx.HTTPStatusError as exc:
            error_type = "rate_limit_error" if exc.response.status_code == 429 else "http_error"
            return self._result(
                model=model,
                base_url=base_url,
                started=started,
                raw_response=self._safe_response_json(exc.response),
                error={"type": error_type, "message": str(exc)},
            )
        except httpx.TimeoutException as exc:
            return self._result(
                model=model,
                base_url=base_url,
                started=started,
                error={"type": "timeout_error", "message": str(exc)},
            )
        except httpx.RequestError as exc:
            return self._result(
                model=model,
                base_url=base_url,
                started=started,
                error={"type": "network_error", "message": str(exc)},
            )
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            return self._result(
                model=model,
                base_url=base_url,
                started=started,
                raw_response=locals().get("raw_response"),
                error={"type": "parse_error", "message": str(exc)},
            )

        return self._result(
            model=model,
            base_url=base_url,
            started=started,
            token_usage=raw_response.get("usage"),
            output_json=output_json,
            raw_response=raw_response,
        )

    def _model_for_task(self, task_type: str) -> str:
        normalized = task_type.upper()
        if normalized == "SOURCE_DISCOVERY":
            return self.settings.llm_source_discovery_model
        if normalized == "LEAD_EXTRACTION":
            return self.settings.llm_extraction_model
        if normalized == "LEAD_GRADING":
            return self.settings.llm_grading_model
        if normalized == "DEEP_ENRICHMENT":
            return self.settings.llm_deep_enrichment_model
        if normalized == "LEAD_CLEANUP":
            return self.settings.llm_cleanup_model
        if normalized == "EMAIL_REPLY":
            return self.settings.llm_email_reply_model
        return self.settings.llm_default_model

    @staticmethod
    def _build_payload(
        model: str,
        system_prompt: str,
        user_prompt: str,
        output_schema: dict[str, Any],
    ) -> dict[str, Any]:
        schema_text = json.dumps(output_schema, ensure_ascii=False, sort_keys=True)
        user_content = f"{user_prompt}\n\n请严格输出符合以下 JSON schema 的 JSON：\n{schema_text}"
        return {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            "response_format": {"type": "json_object"},
        }

    def _parse_output_json(self, raw_response: dict[str, Any]) -> dict[str, Any] | list[Any]:
        content = raw_response["choices"][0]["message"]["content"]
        if not isinstance(content, str):
            raise TypeError("LLM response message content is not a string.")
        return json.loads(self._strip_json_fence(content))

    @staticmethod
    def _strip_json_fence(content: str) -> str:
        stripped = content.strip()
        if stripped.startswith("```"):
            lines = stripped.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            return "\n".join(lines).strip()
        return stripped

    @staticmethod
    def _safe_response_json(response: httpx.Response) -> dict[str, Any] | None:
        try:
            parsed = response.json()
        except ValueError:
            return None
        return parsed if isinstance(parsed, dict) else {"response": parsed}

    def _result(
        self,
        *,
        model: str,
        base_url: str | None,
        started: float,
        token_usage: dict[str, Any] | None = None,
        output_json: dict[str, Any] | list[Any] | None = None,
        raw_response: dict[str, Any] | None = None,
        error: dict[str, str] | None = None,
    ) -> LLMClientResult:
        return LLMClientResult(
            provider=self.settings.llm_provider,
            model=model,
            base_url=base_url,
            latency_ms=max(0, round((time.perf_counter() - started) * 1000)),
            token_usage=token_usage,
            output_json=output_json,
            raw_response=raw_response,
            error=error,
        )
