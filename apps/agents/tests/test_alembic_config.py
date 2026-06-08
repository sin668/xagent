from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_agents_alembic_config_files_exist_and_point_to_agents_app() -> None:
    alembic_ini = (PROJECT_ROOT / "alembic.ini").read_text(encoding="utf-8")
    env_py = (PROJECT_ROOT / "alembic" / "env.py").read_text(encoding="utf-8")

    assert "script_location = %(here)s/alembic" in alembic_ini
    assert "prepend_sys_path = %(here)s" in alembic_ini
    assert "from app.settings import get_settings" in env_py
    assert "settings.database_url" in env_py
    assert "from app import models" in env_py
    assert 'AGENTS_VERSION_TABLE = "agents_alembic_version"' in env_py
    assert "version_table=AGENTS_VERSION_TABLE" in env_py
    assert "async_engine_from_config" not in env_py
    assert "postgresql+asyncpg" not in env_py
