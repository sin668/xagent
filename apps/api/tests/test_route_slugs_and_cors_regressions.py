from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_seed_slug_detail_paths_do_not_return_uuid_validation_422() -> None:
    for path in [
        "/staging-leads/ru-siberia",
        "/customers/ru-siberia",
        "/customers/ru-siberia/outreach-records",
    ]:
        response = client.get(path)
        assert response.status_code == 404
        assert response.status_code != 422

    seed_response = client.get("/outreach-drafts/ru-auto-city")
    assert seed_response.status_code == 200
    assert seed_response.status_code != 422

    unknown_draft_response = client.get("/outreach-drafts/unknown-seed-slug")
    assert unknown_draft_response.status_code == 404
    assert unknown_draft_response.status_code != 422


def test_local_development_preflight_origins_are_allowed() -> None:
    for origin, path in [
        ("http://127.0.0.1:5176", "/staging-leads?limit=100"),
        ("http://localhost:5176", "/outreach-drafts/ru-auto-city"),
        ("http://127.0.0.1:5174", "/inventory/items"),
        ("http://localhost:5174", "/dashboard/admin-overview"),
        ("http://127.0.0.1:8080", "/staging-leads?limit=100"),
        ("http://localhost:8080", "/inventory/items"),
    ]:
        response = client.options(
            path,
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )
        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == origin
