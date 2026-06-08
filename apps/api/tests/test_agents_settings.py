from pydantic import SecretStr

from app.settings import Settings


def test_agents_settings_have_local_service_defaults() -> None:
    config = Settings(_env_file=None)

    assert config.agents_base_url == "http://localhost:8010"
    assert config.agents_timeout_seconds == 120
    assert config.agents_api_key is None
    assert config.http_agent_runtime_enabled is False
    assert config.agent_deep_enrichment_http_active_enabled is False
    assert config.agent_lead_cleanup_http_active_enabled is False
    assert config.external_agent_scheduler_enabled is False
    assert config.external_agent_scheduler_lock_ttl_seconds == 300
    assert config.external_agent_source_discovery_enabled is False
    assert config.external_agent_source_discovery_interval_seconds == 900
    assert config.external_agent_lead_extraction_grading_enabled is False
    assert config.external_agent_lead_extraction_grading_interval_seconds == 300


def test_agents_settings_load_env_aliases() -> None:
    config = Settings(
        _env_file=None,
        AGENTS_BASE_URL="http://127.0.0.1:8010",
        AGENTS_API_KEY="agents-test-key",
        AGENTS_TIMEOUT_SECONDS="30",
        AGENT_DEEP_ENRICHMENT_HTTP_ACTIVE_ENABLED="true",
        AGENT_LEAD_CLEANUP_HTTP_ACTIVE_ENABLED="true",
        EXTERNAL_AGENT_SCHEDULER_ENABLED="true",
        EXTERNAL_AGENT_SCHEDULER_LOCK_TTL_SECONDS="120",
        EXTERNAL_AGENT_SOURCE_DISCOVERY_ENABLED="true",
        EXTERNAL_AGENT_SOURCE_DISCOVERY_INTERVAL_SECONDS="901",
        EXTERNAL_AGENT_LEAD_EXTRACTION_GRADING_ENABLED="true",
        EXTERNAL_AGENT_LEAD_EXTRACTION_GRADING_INTERVAL_SECONDS="301",
    )

    assert config.agents_base_url == "http://127.0.0.1:8010"
    assert isinstance(config.agents_api_key, SecretStr)
    assert config.agents_api_key.get_secret_value() == "agents-test-key"
    assert config.agents_timeout_seconds == 30
    assert config.http_agent_runtime_enabled is True
    assert config.agent_deep_enrichment_http_active_enabled is True
    assert config.agent_lead_cleanup_http_active_enabled is True
    assert config.external_agent_scheduler_enabled is True
    assert config.external_agent_scheduler_lock_ttl_seconds == 120
    assert config.external_agent_source_discovery_enabled is True
    assert config.external_agent_source_discovery_interval_seconds == 901
    assert config.external_agent_lead_extraction_grading_enabled is True
    assert config.external_agent_lead_extraction_grading_interval_seconds == 301


def test_agents_settings_load_vehicle_leads_prefixed_aliases() -> None:
    config = Settings(
        _env_file=None,
        VEHICLE_LEADS_AGENTS_BASE_URL="http://agents.internal:8010",
        VEHICLE_LEADS_AGENTS_API_KEY="prefixed-agents-key",
        VEHICLE_LEADS_AGENTS_TIMEOUT_SECONDS="45",
        VEHICLE_LEADS_AGENT_DEEP_ENRICHMENT_HTTP_ACTIVE_ENABLED="true",
        VEHICLE_LEADS_AGENT_LEAD_CLEANUP_HTTP_ACTIVE_ENABLED="true",
        VEHICLE_LEADS_EXTERNAL_AGENT_SCHEDULER_ENABLED="true",
        VEHICLE_LEADS_EXTERNAL_AGENT_SCHEDULER_LOCK_TTL_SECONDS="180",
        VEHICLE_LEADS_EXTERNAL_AGENT_SOURCE_DISCOVERY_ENABLED="true",
        VEHICLE_LEADS_EXTERNAL_AGENT_SOURCE_DISCOVERY_INTERVAL_SECONDS="902",
        VEHICLE_LEADS_EXTERNAL_AGENT_LEAD_EXTRACTION_GRADING_ENABLED="true",
        VEHICLE_LEADS_EXTERNAL_AGENT_LEAD_EXTRACTION_GRADING_INTERVAL_SECONDS="302",
    )

    assert config.agents_base_url == "http://agents.internal:8010"
    assert config.agents_api_key is not None
    assert config.agents_api_key.get_secret_value() == "prefixed-agents-key"
    assert config.agents_timeout_seconds == 45
    assert config.http_agent_runtime_enabled is True
    assert config.agent_deep_enrichment_http_active_enabled is True
    assert config.agent_lead_cleanup_http_active_enabled is True
    assert config.external_agent_scheduler_enabled is True
    assert config.external_agent_scheduler_lock_ttl_seconds == 180
    assert config.external_agent_source_discovery_enabled is True
    assert config.external_agent_source_discovery_interval_seconds == 902
    assert config.external_agent_lead_extraction_grading_enabled is True
    assert config.external_agent_lead_extraction_grading_interval_seconds == 302


def test_empty_agents_api_key_disables_http_agent_runtime() -> None:
    config = Settings(_env_file=None, AGENTS_API_KEY="")

    assert config.agents_api_key is None
    assert config.http_agent_runtime_enabled is False


def test_legacy_local_agent_scheduler_settings_remain_independent_from_external_scheduler() -> None:
    config = Settings(
        _env_file=None,
        AGENT_SOURCE_DISCOVERY_ENABLED="false",
        AGENT_SOURCE_DISCOVERY_INTERVAL_SECONDS="900",
        AGENT_LEAD_EXTRACTION_ENABLED="false",
        AGENT_LEAD_EXTRACTION_INTERVAL_SECONDS="300",
        AGENT_RETRY_WORKER_ENABLED="false",
        AGENT_RETRY_WORKER_INTERVAL_SECONDS="900",
        EXTERNAL_AGENT_SCHEDULER_ENABLED="true",
        EXTERNAL_AGENT_SOURCE_DISCOVERY_ENABLED="true",
        EXTERNAL_AGENT_LEAD_EXTRACTION_GRADING_ENABLED="true",
    )

    assert config.agent_source_discovery_enabled is False
    assert config.agent_source_discovery_interval_seconds == 900
    assert config.agent_lead_extraction_enabled is False
    assert config.agent_lead_extraction_interval_seconds == 300
    assert config.agent_retry_worker_enabled is False
    assert config.agent_retry_worker_interval_seconds == 900
    assert config.external_agent_scheduler_enabled is True
    assert config.external_agent_source_discovery_enabled is True
    assert config.external_agent_lead_extraction_grading_enabled is True
