from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.settings import settings


def test_outreach_draft_api_returns_existing_safe_draft_with_audit() -> None:
    client = TestClient(app)
    customer_id = uuid4()

    response = client.get(f"/outreach-drafts/{customer_id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["customer_id"] == str(customer_id)
    assert payload["template_id"] == "TMP-RU-B-001"
    assert payload["template_status"] == "可外发"
    assert payload["can_generate_draft"] is True
    assert payload["can_record_sent"] is True
    assert payload["manual_only"] is True
    assert payload["auto_send_enabled"] is False
    assert payload["audit"]["input_saved"] is True
    assert payload["audit"]["output_saved"] is True
    assert all(check["passed"] for check in payload["compliance_checks"])


def test_outreach_draft_api_supports_known_mobile_seed_slug() -> None:
    client = TestClient(app)

    response = client.get("/outreach-drafts/ru-auto-city")

    assert response.status_code == 200
    payload = response.json()
    assert payload["customer_id"] == "11111111-1111-4111-8111-111111111111"
    assert payload["customer_name"] == "AutoCity Moscow"
    assert payload["can_generate_draft"] is True
    assert payload["auto_send_enabled"] is False


def test_outreach_draft_api_rejects_unknown_seed_slug_without_uuid_validation_422() -> None:
    client = TestClient(app)

    response = client.get("/outreach-drafts/unknown-seed-slug")

    assert response.status_code == 404
    assert response.status_code != 422


def test_outreach_draft_api_blocks_do_not_contact_and_high_risk() -> None:
    client = TestClient(app)
    customer_id = uuid4()

    dnc_response = client.get(f"/outreach-drafts/{customer_id}?do_not_contact=true")
    assert dnc_response.status_code == 200
    dnc_payload = dnc_response.json()
    assert dnc_payload["can_generate_draft"] is False
    assert dnc_payload["can_record_sent"] is False
    assert "客户已标记勿扰" in dnc_payload["block_reasons"]

    high_response = client.get(f"/outreach-drafts/{customer_id}?risk_level=High")
    assert high_response.status_code == 200
    high_payload = high_response.json()
    assert high_payload["can_generate_draft"] is False
    assert high_payload["can_record_sent"] is False
    assert "渠道风险不允许触达动作" in high_payload["block_reasons"]


def test_outreach_draft_api_requires_human_confirmation_before_recording_sent() -> None:
    client = TestClient(app)
    customer_id = uuid4()

    blocked = client.post(
        f"/outreach-drafts/{customer_id}/record-manual-send",
        json={"human_confirmed": False, "sender": "Anna", "channel": "Email"},
    )
    assert blocked.status_code == 400

    response = client.post(
        f"/outreach-drafts/{customer_id}/record-manual-send",
        json={"human_confirmed": True, "sender": "Anna", "channel": "Email"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["customer_id"] == str(customer_id)
    assert payload["status"] == "sent_manual"
    assert payload["auto_send"] is False
    assert payload["sender"] == "Anna"


def test_outreach_draft_api_sends_manual_email_with_existing_email_sender() -> None:
    client = TestClient(app)
    customer_id = uuid4()
    original_provider = settings.email_sender_provider
    original_from = settings.email_sender_from_email
    settings.email_sender_provider = "fake"
    settings.email_sender_from_email = "sales@example.com"
    try:
        blocked = client.post(
            f"/outreach-drafts/{customer_id}/send-email",
            json={
                "to_email": "buyer@example.ru",
                "subject": "Поставка подержанных автомобилей из Китая",
                "body": "Здравствуйте! Готовы обсудить поставки автомобилей.",
                "sender": "Anna",
                "human_confirmed": False,
            },
        )
        response = client.post(
            f"/outreach-drafts/{customer_id}/send-email",
            json={
                "to_email": "buyer@example.ru",
                "subject": "Поставка подержанных автомобилей из Китая",
                "body": "Здравствуйте! Готовы обсудить поставки автомобилей.",
                "sender": "Anna",
                "human_confirmed": True,
            },
        )
    finally:
        settings.email_sender_provider = original_provider
        settings.email_sender_from_email = original_from

    assert blocked.status_code == 400
    assert response.status_code == 200
    payload = response.json()
    assert payload["customer_id"] == str(customer_id)
    assert payload["status"] == "sent"
    assert payload["provider"] == "fake"
    assert payload["provider_message_id"].startswith("fake-")
    assert payload["to_email"] == "buyer@example.ru"
    assert payload["auto_send"] is False
