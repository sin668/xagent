import os
from functools import lru_cache

from pydantic import BaseModel


class AgentSettings(BaseModel):
    agents_api_key: str = ""
    database_url: str = "sqlite:///./agents.db"


@lru_cache
def get_settings() -> AgentSettings:
    return AgentSettings(
        agents_api_key=os.getenv("AGENTS_API_KEY", ""),
        database_url=os.getenv("AGENTS_DATABASE_URL") or os.getenv("DATABASE_URL") or "sqlite:///./agents.db",
    )
