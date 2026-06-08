from collections.abc import Iterator
from pathlib import Path

import pytest

from app.settings import get_settings, load_env_file, normalize_sync_database_url


@pytest.fixture(autouse=True)
def clear_settings_cache() -> Iterator[None]:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_agents_database_url_prefers_agents_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENTS_DATABASE_URL", "postgresql+psycopg://agents:secret@db/agents")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://shared:secret@db/shared")

    assert get_settings().database_url == "postgresql+psycopg://agents:secret@db/agents"


def test_agents_database_url_normalizes_asyncpg_to_sync_psycopg(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENTS_DATABASE_URL", "postgresql+asyncpg://agents:secret@db/agents")
    monkeypatch.delenv("DATABASE_URL", raising=False)

    assert get_settings().database_url == "postgresql+psycopg://agents:secret@db/agents"
    assert normalize_sync_database_url("postgresql+asyncpg://a:b@host/db") == "postgresql+psycopg://a:b@host/db"


def test_agents_database_url_falls_back_to_database_url(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr("app.settings.ENV_FILE", tmp_path / ".missing-env")
    monkeypatch.delenv("AGENTS_DATABASE_URL", raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://shared:secret@db/shared")

    assert get_settings().database_url == "postgresql+psycopg://shared:secret@db/shared"


def test_agents_settings_can_load_dotenv_without_overriding_existing_env(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "# local agents env",
                "AGENTS_DATABASE_URL=sqlite:///./from-file.db",
                "AGENTS_API_KEY=file-key",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("AGENTS_API_KEY", "existing-key")
    monkeypatch.delenv("AGENTS_DATABASE_URL", raising=False)

    load_env_file(env_file)

    assert get_settings().database_url == "sqlite:///./from-file.db"
    assert get_settings().agents_api_key == "existing-key"
