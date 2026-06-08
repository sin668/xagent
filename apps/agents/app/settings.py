import os
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel


ENV_FILE = Path(__file__).resolve().parents[1] / ".env"


class AgentSettings(BaseModel):
    agents_api_key: str = ""
    database_url: str = "sqlite:///./agents.db"
    llm_provider: str = "deepseek"
    llm_api_key: str = ""
    llm_base_url: str | None = "https://api.deepseek.com/v1"
    llm_default_model: str = "deepseek-chat"
    llm_source_discovery_model: str = "deepseek-chat"
    llm_extraction_model: str = "deepseek-chat"
    llm_grading_model: str = "deepseek-chat"
    llm_deep_enrichment_model: str = "deepseek-chat"
    llm_cleanup_model: str = "deepseek-chat"
    llm_email_reply_model: str = "deepseek-chat"


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
        llm_provider=os.getenv("AGENTS_LLM_PROVIDER") or os.getenv("LLM_PROVIDER", "deepseek"),
        llm_api_key=os.getenv("AGENTS_LLM_API_KEY") or os.getenv("LLM_API_KEY", ""),
        llm_base_url=os.getenv("AGENTS_LLM_BASE_URL") or os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1"),
        llm_default_model=os.getenv("AGENTS_LLM_DEFAULT_MODEL") or os.getenv("LLM_DEFAULT_MODEL", "deepseek-chat"),
        llm_source_discovery_model=(
            os.getenv("AGENTS_LLM_SOURCE_DISCOVERY_MODEL")
            or os.getenv("LLM_SOURCE_DISCOVERY_MODEL")
            or os.getenv("LLM_DEFAULT_MODEL", "deepseek-chat")
        ),
        llm_extraction_model=(
            os.getenv("AGENTS_LLM_EXTRACTION_MODEL")
            or os.getenv("LLM_EXTRACTION_MODEL")
            or os.getenv("LLM_DEFAULT_MODEL", "deepseek-chat")
        ),
        llm_grading_model=(
            os.getenv("AGENTS_LLM_GRADING_MODEL")
            or os.getenv("LLM_GRADING_MODEL")
            or os.getenv("LLM_DEFAULT_MODEL", "deepseek-chat")
        ),
        llm_deep_enrichment_model=(
            os.getenv("AGENTS_LLM_DEEP_ENRICHMENT_MODEL")
            or os.getenv("LLM_DEEP_ENRICHMENT_MODEL")
            or os.getenv("LLM_EXTRACTION_MODEL")
            or os.getenv("LLM_DEFAULT_MODEL", "deepseek-chat")
        ),
        llm_cleanup_model=(
            os.getenv("AGENTS_LLM_CLEANUP_MODEL")
            or os.getenv("LLM_CLEANUP_MODEL")
            or os.getenv("LLM_GRADING_MODEL")
            or os.getenv("LLM_DEFAULT_MODEL", "deepseek-chat")
        ),
        llm_email_reply_model=(
            os.getenv("AGENTS_LLM_EMAIL_REPLY_MODEL")
            or os.getenv("LLM_EMAIL_REPLY_MODEL")
            or os.getenv("LLM_OUTREACH_MODEL")
            or os.getenv("LLM_DEFAULT_MODEL", "deepseek-chat")
        ),
    )


def normalize_sync_database_url(database_url: str) -> str:
    if database_url.startswith("postgresql+asyncpg://"):
        return database_url.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)
    return database_url
