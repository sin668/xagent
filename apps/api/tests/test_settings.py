from urllib.parse import urlparse

from app.settings import ENV_FILE, settings


def test_settings_load_apps_api_env_file() -> None:
    assert ENV_FILE.name == ".env"
    assert ENV_FILE.parent.name == "api"
    assert ENV_FILE.exists()


def test_database_and_redis_urls_are_loaded_from_apps_api_env() -> None:
    database = urlparse(settings.database_url)
    redis = urlparse(settings.redis_url or "")

    assert database.hostname != "localhost"
    assert database.scheme == "postgresql+asyncpg"
    assert database.path.endswith("/xagent")
    assert settings.database_pool_size == 5
    assert settings.database_max_overflow == 10
    assert redis.scheme == "redis"
    assert redis.hostname is not None
