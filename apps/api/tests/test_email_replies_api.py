from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_email_replies_list_contract_returns_real_empty_queue_before_models_land() -> None:
    response = client.get("/email-replies?limit=50&decision=manual_review")

    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0}


def test_email_reply_detail_and_actions_return_404_without_uuid_validation() -> None:
    for method, path in [
        ("GET", "/email-replies/reply-seed-slug"),
        ("POST", "/email-replies/reply-seed-slug/confirm-send"),
        ("POST", "/email-replies/reply-seed-slug/reject"),
    ]:
        payload = {"actor": "ops-anna", "review_note": "mobile check", "manual_confirmed": True}
        response = client.request(method, path, json=payload if method == "POST" else None)

        assert response.status_code == 404
        assert response.status_code != 422


def test_email_replies_api_is_registered_in_openapi() -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/email-replies" in paths
    assert "/email-replies/{reply_id}" in paths
    assert "/email-replies/{reply_id}/confirm-send" in paths
    assert "/email-replies/{reply_id}/reject" in paths
