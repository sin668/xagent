import os
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel


ENV_FILE = Path(__file__).resolve().parents[1] / ".env"


class AgentSettings(BaseModel):
    agents_api_key: str = ""
    database_url: str = "sqlite:///./agents.db"


def load_env_file(path: Path | None = None) -> None:
    env_path = path or ENV_FILE
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


@lru_cache
def get_settings() -> AgentSettings:
    load_env_file()
    database_url = os.getenv("AGENTS_DATABASE_URL") or os.getenv("DATABASE_URL") or "sqlite:///./agents.db"
    return AgentSettings(
        agents_api_key=os.getenv("AGENTS_API_KEY", ""),
        database_url=normalize_sync_database_url(database_url),
    )


def normalize_sync_database_url(database_url: str) -> str:
    if database_url.startswith("postgresql+asyncpg://"):
        return database_url.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)
    return database_url
