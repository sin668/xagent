from __future__ import annotations

from collections.abc import Iterator

import pytest

from app import settings as settings_module


@pytest.fixture(autouse=True)
def isolate_agents_env(monkeypatch: pytest.MonkeyPatch, tmp_path) -> Iterator[None]:
    monkeypatch.setattr(settings_module, "ENV_FILE", tmp_path / ".missing-agents-env")
    for key in (
        "AGENTS_LLM_PROVIDER",
        "AGENTS_LLM_API_KEY",
        "AGENTS_LLM_BASE_URL",
        "AGENTS_LLM_DEFAULT_MODEL",
        "AGENTS_LLM_SOURCE_DISCOVERY_MODEL",
        "AGENTS_LLM_EXTRACTION_MODEL",
        "AGENTS_LLM_GRADING_MODEL",
        "AGENTS_LLM_DEEP_ENRICHMENT_MODEL",
        "AGENTS_LLM_CLEANUP_MODEL",
        "AGENTS_LLM_EMAIL_REPLY_MODEL",
        "LLM_PROVIDER",
        "LLM_API_KEY",
        "LLM_BASE_URL",
        "LLM_DEFAULT_MODEL",
        "LLM_SOURCE_DISCOVERY_MODEL",
        "LLM_EXTRACTION_MODEL",
        "LLM_GRADING_MODEL",
        "LLM_DEEP_ENRICHMENT_MODEL",
        "LLM_CLEANUP_MODEL",
        "LLM_EMAIL_REPLY_MODEL",
        "LLM_OUTREACH_MODEL",
    ):
        monkeypatch.delenv(key, raising=False)
    settings_module.get_settings.cache_clear()
    yield
    settings_module.get_settings.cache_clear()
