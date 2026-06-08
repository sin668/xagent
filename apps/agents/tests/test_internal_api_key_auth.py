from collections.abc import Iterator

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.main import app as main_app
from app.security import require_internal_api_key
from app.settings import get_settings


@pytest.fixture(autouse=True)
def clear_settings_cache() -> Iterator[None]:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def build_protected_client(monkeypatch: pytest.MonkeyPatch, api_key: str = "phase4-secret") -> TestClient:
    monkeypatch.setenv("AGENTS_API_KEY", api_key)
    get_settings.cache_clear()

    app = FastAPI()

    @app.get("/protected", dependencies=[Depends(require_internal_api_key)])
    def protected() -> dict[str, str]:
        return {"status": "accepted"}

    return TestClient(app)


def test_missing_internal_api_key_returns_401(monkeypatch: pytest.MonkeyPatch) -> None:
    client = build_protected_client(monkeypatch)

    response = client.get("/protected")

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or missing agents API key"}


def test_wrong_internal_api_key_returns_401(monkeypatch: pytest.MonkeyPatch) -> None:
    client = build_protected_client(monkeypatch)

    response = client.get("/protected", headers={"X-Agents-Api-Key": "wrong-key"})

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or missing agents API key"}


def test_correct_internal_api_key_allows_request(monkeypatch: pytest.MonkeyPatch) -> None:
    client = build_protected_client(monkeypatch)

    response = client.get("/protected", headers={"X-Agents-Api-Key": "phase4-secret"})

    assert response.status_code == 200
    assert response.json() == {"status": "accepted"}


def test_health_endpoint_remains_public() -> None:
    client = TestClient(main_app)

    response = client.get("/health")

    assert response.status_code == 200
