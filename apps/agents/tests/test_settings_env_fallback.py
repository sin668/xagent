from app import settings as settings_module


def test_agents_settings_loads_only_agents_env_file(monkeypatch) -> None:
    loaded_paths = []

    def fake_load_env_file(path=None) -> None:
        loaded_paths.append(path or settings_module.ENV_FILE)

    monkeypatch.setattr(settings_module, "load_env_file", fake_load_env_file)
    settings_module.get_settings.cache_clear()
    try:
        settings_module.get_settings()
    finally:
        settings_module.get_settings.cache_clear()

    assert loaded_paths == [settings_module.ENV_FILE]
