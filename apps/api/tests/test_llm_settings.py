from pydantic import SecretStr

from app.settings import Settings, settings


def test_llm_settings_have_deepseek_defaults() -> None:
    config = Settings(_env_file=None)

    assert config.llm_provider == "deepseek"
    assert config.llm_default_model == "deepseek-chat"
    assert config.llm_source_discovery_model == "deepseek-chat"
    assert config.llm_extraction_model == "deepseek-chat"
    assert config.llm_grading_model == "deepseek-chat"
    assert config.llm_base_url == "https://api.deepseek.com/v1"
    assert config.llm_embedding_model == "text-embedding-3-small"
    assert config.llm_embedding_dimensions == 1536
    assert config.llm_embedding_base_url is None
    assert config.llm_embedding_api_key is None


def test_llm_settings_load_openai_compatible_env_aliases() -> None:
    config = Settings(
        _env_file=None,
        LLM_PROVIDER="openai",
        LLM_API_KEY="sk-test-secret",
        LLM_BASE_URL="https://api.example.com/v1",
        LLM_DEFAULT_MODEL="gpt-4.1-mini",
        LLM_SOURCE_DISCOVERY_MODEL="gpt-4.1",
        LLM_EXTRACTION_MODEL="gpt-4.1-mini",
        LLM_GRADING_MODEL="gpt-4.1-nano",
        LLM_EMBEDDING_MODEL="text-embedding-3-large",
        LLM_EMBEDDING_DIMENSIONS="1536",
        LLM_EMBEDDING_BASE_URL="https://embedding.example.com/v1",
        LLM_EMBEDDING_API_KEY="sk-embedding-secret",
    )

    assert config.llm_provider == "openai"
    assert isinstance(config.llm_api_key, SecretStr)
    assert config.llm_api_key.get_secret_value() == "sk-test-secret"
    assert config.llm_base_url == "https://api.example.com/v1"
    assert config.llm_default_model == "gpt-4.1-mini"
    assert config.llm_source_discovery_model == "gpt-4.1"
    assert config.llm_extraction_model == "gpt-4.1-mini"
    assert config.llm_grading_model == "gpt-4.1-nano"
    assert config.llm_embedding_model == "text-embedding-3-large"
    assert config.llm_embedding_dimensions == 1536
    assert config.llm_embedding_base_url == "https://embedding.example.com/v1"
    assert config.llm_embedding_api_key is not None
    assert config.llm_embedding_api_key.get_secret_value() == "sk-embedding-secret"


def test_llm_settings_loaded_from_apps_api_env_without_calling_provider() -> None:
    assert settings.llm_provider == "deepseek"
    assert settings.llm_base_url == "https://api.deepseek.com/v1"
    assert settings.llm_default_model == "deepseek-chat"
    assert settings.llm_source_discovery_model == "deepseek-chat"
    assert settings.llm_extraction_model == "deepseek-chat"
    assert settings.llm_grading_model == "deepseek-chat"
    assert settings.llm_embedding_model == "text-embedding-3-small"
    assert settings.llm_embedding_dimensions == 1536
    assert settings.llm_api_key is None or isinstance(settings.llm_api_key, SecretStr)
