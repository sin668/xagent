from __future__ import annotations

import asyncio
from typing import Any

import httpx

from app.settings import Settings, settings


class HttpAgentRuntimeError(RuntimeError):
    pass


class HttpAgentRuntimeConfigurationError(HttpAgentRuntimeError):
    pass


class HttpAgentRuntimeTimeoutError(HttpAgentRuntimeError):
    pass


class HttpAgentRuntimeHTTPError(HttpAgentRuntimeError):
    def __init__(self, message: str, *, status_code: int, response_json: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_json = response_json


class HttpAgentRuntimeAuthError(HttpAgentRuntimeHTTPError):
    pass


class HttpAgentRuntimeValidationError(HttpAgentRuntimeHTTPError):
    pass


class HttpAgentRuntimeServerError(HttpAgentRuntimeHTTPError):
    pass


class HttpAgentRuntime:
    def __init__(
        self,
        *,
        settings: Settings = settings,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.settings = settings
        self.http_client = http_client

    def run_deep_enrichment(
        self,
        *,
        agent_run_id: Any,
        staging_lead_id: Any,
        lead_snapshot: dict[str, Any],
        missing_fields: list[str],
    ) -> dict[str, Any]:
        response = self.run_deep_enrichment_response(
            agent_run_id=agent_run_id,
            staging_lead_id=staging_lead_id,
            lead_snapshot=lead_snapshot,
            missing_fields=missing_fields,
        )
        return self._phase3_output_from_response(response, expected_schema_version="phase3.agent.deep_enrichment.v1")

    def run_deep_enrichment_response(
        self,
        *,
        agent_run_id: Any,
        staging_lead_id: Any,
        lead_snapshot: dict[str, Any],
        missing_fields: list[str],
    ) -> dict[str, Any]:
        return self._run_agent_sync(
            "deep-enrichment",
            request_id=str(agent_run_id),
            agent_task_run_id=str(agent_run_id),
            trigger_source="phase3_deep_enrichment_runtime",
            agent_mode="active",
            input_payload={
                "agent_run_id": str(agent_run_id),
                "staging_lead_id": str(staging_lead_id),
                "lead_snapshot": lead_snapshot,
                "missing_fields": missing_fields,
            },
            options={"timeout_seconds": self.settings.agents_timeout_seconds},
        )

    def run_lead_cleanup(
        self,
        *,
        cleanup_run_id: Any,
        leads: list[dict[str, Any]],
    ) -> dict[str, Any]:
        response = self.run_lead_cleanup_response(cleanup_run_id=cleanup_run_id, leads=leads)
        return self._phase3_output_from_response(response, expected_schema_version="phase3.agent.lead_cleanup.v1")

    def run_lead_cleanup_response(
        self,
        *,
        cleanup_run_id: Any,
        leads: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return self._run_agent_sync(
            "lead-cleanup",
            request_id=str(cleanup_run_id),
            trigger_source="phase3_lead_cleanup_runtime",
            agent_mode="active",
            input_payload={
                "cleanup_run_id": str(cleanup_run_id),
                "leads": leads,
            },
            options={"timeout_seconds": self.settings.agents_timeout_seconds},
        )

    def run_email_reply_response(
        self,
        *,
        request_id: Any,
        agent_task_run_id: Any,
        thread_id: Any,
        message_id: Any,
        customer_id: Any | None = None,
        draft_id: Any | None = None,
        context: dict[str, Any] | None = None,
        prompt: dict[str, Any] | None = None,
        options: dict[str, Any] | None = None,
        agent_mode: str = "active",
        dry_run: bool = False,
    ) -> dict[str, Any]:
        input_payload = {
            "thread_id": str(thread_id),
            "message_id": str(message_id),
            "customer_id": str(customer_id) if customer_id is not None else None,
            "draft_id": str(draft_id) if draft_id is not None else None,
            "context": context or {},
            "prompt": prompt or {},
            "options": options or {},
        }
        return self._run_agent_sync(
            "email-reply",
            request_id=str(request_id),
            agent_task_run_id=str(agent_task_run_id),
            trigger_source="phase5_email_reply_runtime",
            agent_mode=agent_mode,
            input_payload=input_payload,
            options={"timeout_seconds": self.settings.agents_timeout_seconds, "dry_run": dry_run},
        )

    async def run_agent(
        self,
        agent_endpoint: str,
        *,
        request_id: str,
        trigger_source: str,
        agent_mode: str,
        input_payload: dict[str, Any],
        agent_task_run_id: str | None = None,
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        api_key = self._api_key_value()
        if not api_key:
            raise HttpAgentRuntimeConfigurationError("AGENTS_API_KEY is not configured; HTTP Agent runtime is disabled.")

        payload = {
            "request_id": request_id,
            "agent_task_run_id": agent_task_run_id,
            "trigger_source": trigger_source,
            "agent_mode": agent_mode,
            "input": input_payload,
            "options": options or {},
        }
        headers = {"X-Agents-Api-Key": api_key, "Content-Type": "application/json"}
        url = f"{self.settings.agents_base_url.rstrip('/')}/agent-runs/{agent_endpoint.strip('/')}"

        try:
            if self.http_client is not None:
                response = await self.http_client.post(url, json=payload, headers=headers)
            else:
                async with httpx.AsyncClient(timeout=self.settings.agents_timeout_seconds) as client:
                    response = await client.post(url, json=payload, headers=headers)
        except httpx.TimeoutException as exc:
            raise HttpAgentRuntimeTimeoutError(str(exc)) from exc
        except httpx.RequestError as exc:
            raise HttpAgentRuntimeError(str(exc)) from exc

        if response.status_code >= 400:
            self._raise_for_error_response(response)

        parsed = self._safe_response_json(response)
        if parsed is None:
            raise HttpAgentRuntimeValidationError(
                "apps/agents returned a non-JSON response.",
                status_code=response.status_code,
                response_json=None,
            )
        self._validate_response_envelope(parsed, status_code=response.status_code)
        return parsed

    async def get_agent_run(self, external_agent_run_id: str) -> dict[str, Any]:
        api_key = self._api_key_value()
        if not api_key:
            raise HttpAgentRuntimeConfigurationError("AGENTS_API_KEY is not configured; HTTP Agent runtime is disabled.")

        headers = {"X-Agents-Api-Key": api_key}
        run_id = str(external_agent_run_id).strip("/")
        url = f"{self.settings.agents_base_url.rstrip('/')}/agent-runs/{run_id}"

        try:
            if self.http_client is not None:
                response = await self.http_client.get(url, headers=headers)
            else:
                async with httpx.AsyncClient(timeout=self.settings.agents_timeout_seconds) as client:
                    response = await client.get(url, headers=headers)
        except httpx.TimeoutException as exc:
            raise HttpAgentRuntimeTimeoutError(str(exc)) from exc
        except httpx.RequestError as exc:
            raise HttpAgentRuntimeError(str(exc)) from exc

        if response.status_code >= 400:
            self._raise_for_error_response(response)

        parsed = self._safe_response_json(response)
        if parsed is None:
            raise HttpAgentRuntimeValidationError(
                "apps/agents returned a non-JSON response.",
                status_code=response.status_code,
                response_json=None,
            )
        self._validate_response_envelope(parsed, status_code=response.status_code)
        return self._agent_run_consumption_result(parsed, status_code=response.status_code)

    def _run_agent_sync(self, agent_endpoint: str, **kwargs: Any) -> dict[str, Any]:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.run_agent(agent_endpoint, **kwargs))
        raise HttpAgentRuntimeConfigurationError("HttpAgentRuntime compatibility methods must be called from synchronous service code.")

    def _raise_for_error_response(self, response: httpx.Response) -> None:
        response_json = self._safe_response_json(response)
        message = self._error_message(response, response_json)
        if response.status_code == 401:
            raise HttpAgentRuntimeAuthError(message, status_code=response.status_code, response_json=response_json)
        if 400 <= response.status_code < 500:
            raise HttpAgentRuntimeValidationError(message, status_code=response.status_code, response_json=response_json)
        raise HttpAgentRuntimeServerError(message, status_code=response.status_code, response_json=response_json)

    def _api_key_value(self) -> str | None:
        if self.settings.agents_api_key is None:
            return None
        value = self.settings.agents_api_key.get_secret_value().strip()
        return value or None

    def _safe_response_json(self, response: httpx.Response) -> dict[str, Any] | None:
        try:
            parsed = response.json()
        except ValueError:
            return None
        return parsed if isinstance(parsed, dict) else {"response": parsed}

    def _validate_response_envelope(self, payload: dict[str, Any], *, status_code: int) -> None:
        required_fields = {"schema_version", "agent_service_run_id", "request_id", "status"}
        missing_fields = sorted(required_fields - set(payload))
        if payload.get("schema_version") != "phase4.agent.run.v1" or missing_fields:
            raise HttpAgentRuntimeValidationError(
                "apps/agents response envelope must use schema_version=phase4.agent.run.v1 and include required run fields.",
                status_code=status_code,
                response_json=payload,
            )
        audit = payload.get("audit")
        if isinstance(audit, dict) and audit.get("writes_core_tables") is not False:
            raise HttpAgentRuntimeValidationError(
                "apps/agents response audit.writes_core_tables must be false.",
                status_code=status_code,
                response_json=payload,
            )

    def _phase3_output_from_response(self, response: dict[str, Any], *, expected_schema_version: str) -> dict[str, Any]:
        if response.get("status") != "succeeded":
            raise HttpAgentRuntimeValidationError(
                "apps/agents response status must be succeeded before compatibility runtime returns phase3 output.",
                status_code=200,
                response_json=response,
            )
        output = response.get("output")
        if not isinstance(output, dict):
            raise HttpAgentRuntimeValidationError(
                "apps/agents response envelope must include an output object for compatibility runtime methods.",
                status_code=200,
                response_json=response,
            )
        if output.get("schema_version") != expected_schema_version:
            raise HttpAgentRuntimeValidationError(
                f"apps/agents output schema_version must be {expected_schema_version}.",
                status_code=200,
                response_json=response,
            )
        return output

    def _agent_run_consumption_result(self, response: dict[str, Any], *, status_code: int) -> dict[str, Any]:
        status = response.get("status")
        result = dict(response)
        result["is_terminal"] = status in {"succeeded", "failed", "blocked", "cancelled"}
        result["is_success"] = status == "succeeded"
        result["is_failure"] = status in {"failed", "blocked", "cancelled"}

        if status == "succeeded" and not isinstance(response.get("output"), dict):
            raise HttpAgentRuntimeValidationError(
                "apps/agents succeeded run response must include a structured output object.",
                status_code=status_code,
                response_json=response,
            )

        error = response.get("error")
        if result["is_failure"] and not isinstance(error, dict):
            raise HttpAgentRuntimeValidationError(
                "apps/agents failed run response must include a structured error object.",
                status_code=status_code,
                response_json=response,
            )
        if isinstance(error, dict):
            result["error_type"] = error.get("error_type")
            result["error_message"] = error.get("message")
            result["retryable"] = error.get("retryable")
        else:
            result["error_type"] = None
            result["error_message"] = None
            result["retryable"] = None
        return result

    def _error_message(self, response: httpx.Response, response_json: dict[str, Any] | None) -> str:
        if response_json is not None:
            detail = response_json.get("detail")
            if isinstance(detail, str) and detail:
                return detail
            if isinstance(detail, list) and detail:
                return f"apps/agents request failed with HTTP {response.status_code}: {detail}"
        return f"apps/agents request failed with HTTP {response.status_code}."
