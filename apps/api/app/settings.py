from pathlib import Path

from pydantic import AliasChoices, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


ENV_FILE = Path(__file__).resolve().parents[1] / ".env"

LOCAL_DEVELOPMENT_CORS_ORIGINS = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
    "http://localhost:5175",
    "http://127.0.0.1:5175",
    "http://localhost:5176",
    "http://127.0.0.1:5176",
    "http://localhost:5177",
    "http://127.0.0.1:5177",
    "http://localhost:8080",
    "http://127.0.0.1:8080",
)


class Settings(BaseSettings):
    database_url: str = Field(
        default="postgresql+asyncpg://vehicle_leads:vehicle_leads@localhost:5432/vehicle_leads",
        validation_alias=AliasChoices("VEHICLE_LEADS_DATABASE_URL", "DATABASE_URL"),
    )
    database_pool_size: int = Field(default=5, validation_alias=AliasChoices("VEHICLE_LEADS_DATABASE_POOL_SIZE", "DATABASE_POOL_SIZE"))
    database_max_overflow: int = Field(
        default=10,
        validation_alias=AliasChoices("VEHICLE_LEADS_DATABASE_MAX_OVERFLOW", "DATABASE_MAX_OVERFLOW"),
    )
    redis_url: str | None = Field(default=None, validation_alias=AliasChoices("VEHICLE_LEADS_REDIS_URL", "REDIS_URL"))
    agent_scheduler_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices("VEHICLE_LEADS_AGENT_SCHEDULER_ENABLED", "AGENT_SCHEDULER_ENABLED"),
    )
    agent_scheduler_lock_ttl_seconds: int = Field(
        default=300,
        validation_alias=AliasChoices("VEHICLE_LEADS_AGENT_SCHEDULER_LOCK_TTL_SECONDS", "AGENT_SCHEDULER_LOCK_TTL_SECONDS"),
    )
    agent_source_discovery_enabled: bool = Field(
        default=True,
        validation_alias=AliasChoices("VEHICLE_LEADS_AGENT_SOURCE_DISCOVERY_ENABLED", "AGENT_SOURCE_DISCOVERY_ENABLED"),
    )
    agent_source_discovery_interval_seconds: int = Field(
        default=3600,
        validation_alias=AliasChoices(
            "VEHICLE_LEADS_AGENT_SOURCE_DISCOVERY_INTERVAL_SECONDS",
            "AGENT_SOURCE_DISCOVERY_INTERVAL_SECONDS",
        ),
    )
    agent_lead_extraction_enabled: bool = Field(
        default=True,
        validation_alias=AliasChoices("VEHICLE_LEADS_AGENT_LEAD_EXTRACTION_ENABLED", "AGENT_LEAD_EXTRACTION_ENABLED"),
    )
    agent_lead_extraction_interval_seconds: int = Field(
        default=900,
        validation_alias=AliasChoices(
            "VEHICLE_LEADS_AGENT_LEAD_EXTRACTION_INTERVAL_SECONDS",
            "AGENT_LEAD_EXTRACTION_INTERVAL_SECONDS",
        ),
    )
    agent_retry_worker_enabled: bool = Field(
        default=True,
        validation_alias=AliasChoices("VEHICLE_LEADS_AGENT_RETRY_WORKER_ENABLED", "AGENT_RETRY_WORKER_ENABLED"),
    )
    agent_retry_worker_interval_seconds: int = Field(
        default=300,
        validation_alias=AliasChoices(
            "VEHICLE_LEADS_AGENT_RETRY_WORKER_INTERVAL_SECONDS",
            "AGENT_RETRY_WORKER_INTERVAL_SECONDS",
        ),
    )
    agents_base_url: str = Field(
        default="http://localhost:8010",
        validation_alias=AliasChoices("VEHICLE_LEADS_AGENTS_BASE_URL", "AGENTS_BASE_URL"),
    )
    agents_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("VEHICLE_LEADS_AGENTS_API_KEY", "AGENTS_API_KEY"),
    )
    agents_timeout_seconds: int = Field(
        default=120,
        ge=1,
        validation_alias=AliasChoices("VEHICLE_LEADS_AGENTS_TIMEOUT_SECONDS", "AGENTS_TIMEOUT_SECONDS"),
    )
    external_agent_scheduler_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "VEHICLE_LEADS_EXTERNAL_AGENT_SCHEDULER_ENABLED",
            "EXTERNAL_AGENT_SCHEDULER_ENABLED",
        ),
    )
    external_agent_scheduler_lock_ttl_seconds: int = Field(
        default=300,
        validation_alias=AliasChoices(
            "VEHICLE_LEADS_EXTERNAL_AGENT_SCHEDULER_LOCK_TTL_SECONDS",
            "EXTERNAL_AGENT_SCHEDULER_LOCK_TTL_SECONDS",
        ),
    )
    external_agent_source_discovery_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "VEHICLE_LEADS_EXTERNAL_AGENT_SOURCE_DISCOVERY_ENABLED",
            "EXTERNAL_AGENT_SOURCE_DISCOVERY_ENABLED",
        ),
    )
    external_agent_source_discovery_interval_seconds: int = Field(
        default=900,
        ge=1,
        validation_alias=AliasChoices(
            "VEHICLE_LEADS_EXTERNAL_AGENT_SOURCE_DISCOVERY_INTERVAL_SECONDS",
            "EXTERNAL_AGENT_SOURCE_DISCOVERY_INTERVAL_SECONDS",
        ),
    )
    external_agent_lead_extraction_grading_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "VEHICLE_LEADS_EXTERNAL_AGENT_LEAD_EXTRACTION_GRADING_ENABLED",
            "EXTERNAL_AGENT_LEAD_EXTRACTION_GRADING_ENABLED",
        ),
    )
    external_agent_lead_extraction_grading_interval_seconds: int = Field(
        default=300,
        ge=1,
        validation_alias=AliasChoices(
            "VEHICLE_LEADS_EXTERNAL_AGENT_LEAD_EXTRACTION_GRADING_INTERVAL_SECONDS",
            "EXTERNAL_AGENT_LEAD_EXTRACTION_GRADING_INTERVAL_SECONDS",
        ),
    )
    agent_deep_enrichment_http_active_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "VEHICLE_LEADS_AGENT_DEEP_ENRICHMENT_HTTP_ACTIVE_ENABLED",
            "AGENT_DEEP_ENRICHMENT_HTTP_ACTIVE_ENABLED",
        ),
    )
    agent_lead_cleanup_http_active_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "VEHICLE_LEADS_AGENT_LEAD_CLEANUP_HTTP_ACTIVE_ENABLED",
            "AGENT_LEAD_CLEANUP_HTTP_ACTIVE_ENABLED",
        ),
    )
    agent_email_reply_http_active_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "VEHICLE_LEADS_AGENT_EMAIL_REPLY_HTTP_ACTIVE_ENABLED",
            "AGENT_EMAIL_REPLY_HTTP_ACTIVE_ENABLED",
        ),
    )
    email_sender_provider: str = Field(
        default="fake",
        validation_alias=AliasChoices("VEHICLE_LEADS_EMAIL_SENDER_PROVIDER", "EMAIL_SENDER_PROVIDER"),
    )
    email_sender_from_email: str | None = Field(
        default=None,
        validation_alias=AliasChoices("VEHICLE_LEADS_EMAIL_SENDER_FROM_EMAIL", "EMAIL_SENDER_FROM_EMAIL"),
    )
    smtp_host: str | None = Field(default=None, validation_alias=AliasChoices("VEHICLE_LEADS_SMTP_HOST", "SMTP_HOST"))
    smtp_port: int = Field(default=587, validation_alias=AliasChoices("VEHICLE_LEADS_SMTP_PORT", "SMTP_PORT"))
    smtp_username: str | None = Field(default=None, validation_alias=AliasChoices("VEHICLE_LEADS_SMTP_USERNAME", "SMTP_USERNAME"))
    smtp_password: SecretStr | None = Field(default=None, validation_alias=AliasChoices("VEHICLE_LEADS_SMTP_PASSWORD", "SMTP_PASSWORD"))
    smtp_use_tls: bool = Field(default=True, validation_alias=AliasChoices("VEHICLE_LEADS_SMTP_USE_TLS", "SMTP_USE_TLS"))
    smtp_timeout_seconds: int = Field(default=30, ge=1, validation_alias=AliasChoices("VEHICLE_LEADS_SMTP_TIMEOUT_SECONDS", "SMTP_TIMEOUT_SECONDS"))
    sendgrid_api_key: SecretStr | None = Field(default=None, validation_alias=AliasChoices("VEHICLE_LEADS_SENDGRID_API_KEY", "SENDGRID_API_KEY"))
    mailgun_api_key: SecretStr | None = Field(default=None, validation_alias=AliasChoices("VEHICLE_LEADS_MAILGUN_API_KEY", "MAILGUN_API_KEY"))
    mailgun_domain: str | None = Field(default=None, validation_alias=AliasChoices("VEHICLE_LEADS_MAILGUN_DOMAIN", "MAILGUN_DOMAIN"))
    enterprise_mail_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("VEHICLE_LEADS_ENTERPRISE_MAIL_API_KEY", "ENTERPRISE_MAIL_API_KEY"),
    )
    enterprise_mail_base_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("VEHICLE_LEADS_ENTERPRISE_MAIL_BASE_URL", "ENTERPRISE_MAIL_BASE_URL"),
    )
    lead_enrichment_daily_quota_per_lead: int = Field(
        default=2,
        validation_alias=AliasChoices(
            "VEHICLE_LEADS_LEAD_ENRICHMENT_DAILY_QUOTA_PER_LEAD",
            "LEAD_ENRICHMENT_DAILY_QUOTA_PER_LEAD",
        ),
    )
    feishu_app_id: str | None = Field(default=None, validation_alias=AliasChoices("VEHICLE_LEADS_FEISHU_APP_ID", "FEISHU_APP_ID"))
    feishu_app_secret: str | None = Field(default=None, validation_alias=AliasChoices("VEHICLE_LEADS_FEISHU_APP_SECRET", "FEISHU_APP_SECRET"))
    feishu_bitable_app_token: str | None = Field(
        default=None,
        validation_alias=AliasChoices("VEHICLE_LEADS_FEISHU_BITABLE_APP_TOKEN", "FEISHU_BITABLE_APP_TOKEN"),
    )
    cors_origins: str = Field(
        default=(
            "http://localhost:5173,http://127.0.0.1:5173,"
            "http://localhost:5174,http://127.0.0.1:5174,"
            "http://localhost:5175,http://127.0.0.1:5175,"
            "http://localhost:5176,http://127.0.0.1:5176,"
            "http://localhost:8080,http://127.0.0.1:8080"
        ),
        validation_alias=AliasChoices("VEHICLE_LEADS_CORS_ORIGINS", "CORS_ORIGINS"),
    )
    llm_provider: str = Field(
        default="deepseek",
        validation_alias=AliasChoices("VEHICLE_LEADS_LLM_PROVIDER", "LLM_PROVIDER"),
    )
    llm_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("VEHICLE_LEADS_LLM_API_KEY", "LLM_API_KEY"),
    )
    llm_base_url: str | None = Field(
        default="https://api.deepseek.com/v1",
        validation_alias=AliasChoices("VEHICLE_LEADS_LLM_BASE_URL", "LLM_BASE_URL"),
    )
    llm_default_model: str = Field(
        default="deepseek-chat",
        validation_alias=AliasChoices("VEHICLE_LEADS_LLM_DEFAULT_MODEL", "LLM_DEFAULT_MODEL"),
    )
    llm_source_discovery_model: str = Field(
        default="deepseek-chat",
        validation_alias=AliasChoices("VEHICLE_LEADS_LLM_SOURCE_DISCOVERY_MODEL", "LLM_SOURCE_DISCOVERY_MODEL"),
    )
    llm_extraction_model: str = Field(
        default="deepseek-chat",
        validation_alias=AliasChoices("VEHICLE_LEADS_LLM_EXTRACTION_MODEL", "LLM_EXTRACTION_MODEL"),
    )
    llm_grading_model: str = Field(
        default="deepseek-chat",
        validation_alias=AliasChoices("VEHICLE_LEADS_LLM_GRADING_MODEL", "LLM_GRADING_MODEL"),
    )
    llm_embedding_model: str = Field(
        default="text-embedding-3-small",
        validation_alias=AliasChoices("VEHICLE_LEADS_LLM_EMBEDDING_MODEL", "LLM_EMBEDDING_MODEL"),
    )
    llm_embedding_dimensions: int = Field(
        default=1536,
        validation_alias=AliasChoices("VEHICLE_LEADS_LLM_EMBEDDING_DIMENSIONS", "LLM_EMBEDDING_DIMENSIONS"),
    )
    llm_embedding_base_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("VEHICLE_LEADS_LLM_EMBEDDING_BASE_URL", "LLM_EMBEDDING_BASE_URL"),
    )
    llm_embedding_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("VEHICLE_LEADS_LLM_EMBEDDING_API_KEY", "LLM_EMBEDDING_API_KEY"),
    )

    @property
    def cors_origin_list(self) -> list[str]:
        configured = [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
        merged = [*configured]
        for origin in LOCAL_DEVELOPMENT_CORS_ORIGINS:
            if origin not in merged:
                merged.append(origin)
        return merged

    @property
    def http_agent_runtime_enabled(self) -> bool:
        return bool(self.agents_api_key and self.agents_api_key.get_secret_value().strip())

    @field_validator("agents_api_key", mode="before")
    @classmethod
    def blank_agents_api_key_to_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("llm_embedding_api_key", mode="before")
    @classmethod
    def blank_embedding_api_key_to_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")


settings = Settings()
