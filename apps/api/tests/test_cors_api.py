from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_h5_mobile_origin_is_allowed_for_api_requests() -> None:
    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:5176",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5176"
