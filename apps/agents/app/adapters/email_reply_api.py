from __future__ import annotations

from typing import Any

import httpx

from app.schemas.email_reply import EmailReplyRequestEnvelope


class EmailReplyApiClient:
    def __init__(self, *, base_url: str, api_key: str, timeout_seconds: int = 120) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    @property
    def headers(self) -> dict[str, str]:
        return {"X-Agents-Api-Key": self.api_key}

    def load_context(self, envelope: EmailReplyRequestEnvelope) -> dict[str, Any]:
        response = httpx.post(
            f"{self.base_url}/internal/email-reply/context",
            headers=self.headers,
            json=envelope.model_dump(mode="json"),
            timeout=self.timeout_seconds,
        )
        if response.status_code >= 400:
            raise RuntimeError(f"apps/api internal auth failed or context unavailable: {response.status_code}")
        return dict(response.json())

    def retrieve_knowledge(
        self,
        *,
        query: str | None,
        language: str,
        channel: str | None,
        content_types: list[str],
        business_scene: str | None,
        auto_send_candidate: bool,
        market: str | None,
        tone: str | None,
        limit: int,
    ) -> dict[str, Any]:
        response = httpx.post(
            f"{self.base_url}/internal/email-reply/knowledge",
            headers=self.headers,
            json={
                "query": query,
                "language": language,
                "channel": channel,
                "content_types": content_types,
                "business_scene": business_scene,
                "auto_send_candidate": auto_send_candidate,
                "market": market,
                "tone": tone,
                "limit": limit,
            },
            timeout=self.timeout_seconds,
        )
        if response.status_code >= 400:
            raise RuntimeError(f"apps/api internal knowledge retrieval failed: {response.status_code}")
        return dict(response.json())

    def auto_send_check(
        self,
        *,
        envelope: EmailReplyRequestEnvelope,
        output: dict[str, Any],
        context: dict[str, Any],
        knowledge_hits: list[dict[str, Any]],
        options: dict[str, Any],
        dry_run: bool,
    ) -> dict[str, Any]:
        response = httpx.post(
            f"{self.base_url}/internal/email-reply/auto-send-check",
            headers=self.headers,
            json={
                "schema_version": envelope.schema_version,
                "request_id": str(envelope.request_id),
                "draft_id": str(envelope.draft_id) if envelope.draft_id else None,
                "thread_id": str(envelope.thread_id),
                "message_id": str(envelope.message_id),
                "customer_id": str(envelope.customer_id) if envelope.customer_id else None,
                "output": output,
                "context": context,
                "knowledge_hits": knowledge_hits,
                "options": options,
                "dry_run": dry_run,
            },
            timeout=self.timeout_seconds,
        )
        if response.status_code >= 400:
            raise RuntimeError(f"apps/api internal auto-send check failed: {response.status_code}")
        return dict(response.json())
