from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_llm_health_api_reports_configuration_without_calling_real_llm() -> None:
    response = client.get("/llm-health")

    assert response.status_code == 200
    body = response.json()

    assert body["provider"]
    assert "api_key" not in body
    assert "secret" not in str(body).lower()
    assert set(body["models"].keys()) == {"default", "source_discovery", "extraction", "grading"}
    assert isinstance(body["base_url_configured"], bool)
    assert isinstance(body["api_key_configured"], bool)
    assert isinstance(body["configuration_complete"], bool)


def test_llm_health_api_is_registered_in_openapi() -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert "/llm-health" in response.json()["paths"]
