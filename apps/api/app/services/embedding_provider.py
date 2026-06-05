from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

import httpx

from app.settings import Settings, settings


class EmbeddingProvider(Protocol):
    model: str
    dimensions: int

    def embed_text(self, text: str) -> list[float]:
        """生成单条文本 embedding。"""


@dataclass
class OpenAICompatibleEmbeddingProvider:
    settings: Settings = field(default_factory=lambda: settings)
    timeout_seconds: float = 60.0

    @property
    def model(self) -> str:
        return self.settings.llm_embedding_model

    @property
    def dimensions(self) -> int:
        return self.settings.llm_embedding_dimensions

    def embed_text(self, text: str) -> list[float]:
        api_key = self._api_key_value()
        base_url = self.settings.llm_embedding_base_url or self.settings.llm_base_url
        if not api_key:
            raise RuntimeError("Embedding API key is not configured.")
        if not base_url:
            raise RuntimeError("Embedding base URL is not configured.")

        payload = {
            "model": self.model,
            "input": text,
        }
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.post(f"{base_url.rstrip('/')}/embeddings", json=payload, headers=headers)
            response.raise_for_status()
        raw_response = response.json()
        embedding = raw_response["data"][0]["embedding"]
        if not isinstance(embedding, list):
            raise RuntimeError("Embedding response data[0].embedding is not a list.")
        return [float(value) for value in embedding]

    def _api_key_value(self) -> str | None:
        api_key = self.settings.llm_embedding_api_key or self.settings.llm_api_key
        if api_key is None:
            return None
        return api_key.get_secret_value() or None


def create_embedding_provider() -> EmbeddingProvider:
    return OpenAICompatibleEmbeddingProvider()
