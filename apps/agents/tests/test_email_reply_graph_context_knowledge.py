from uuid import uuid4

import pytest

from app.graphs.email_reply import EmailReplyGraphRunner, EmailReplyGraphState
from app.adapters.email_reply_api import EmailReplyApiClient


class FakeEmailReplyApiClient:
    def __init__(self, *, fail_context: bool = False) -> None:
        self.fail_context = fail_context
        self.context_calls = []
        self.knowledge_calls = []

    def load_context(self, envelope):
        self.context_calls.append(envelope)
        if self.fail_context:
            raise RuntimeError("apps/api internal auth failed: 401")
        return {
            "customer": {"name": "Moscow Auto Dealer"},
            "inbound_message": {"language": "ru", "body_text": "Нужны авто"},
            "audit_summary": {"included_sections": ["customer", "inbound_message"]},
        }

    def retrieve_knowledge(self, *, query, language, channel, content_types, business_scene, auto_send_candidate, market, tone, limit):
        self.knowledge_calls.append(
            {
                "query": query,
                "language": language,
                "channel": channel,
                "content_types": content_types,
                "business_scene": business_scene,
                "auto_send_candidate": auto_send_candidate,
                "market": market,
                "tone": tone,
                "limit": limit,
            }
        )
        return {
            "items": [{"knowledge_item_id": str(uuid4()), "title": "FAQ", "version": "v1", "similarity_score": 0.9}],
            "total": 1,
            "rejection_reason": None,
        }

    def auto_send_check(self, **kwargs):
        return {
            "route": "hold_for_manual_review",
            "auto_send_allowed": False,
            "manual_review_required": True,
            "manual_review_reason": "测试替身默认进入人工确认。",
            "reasons": ["test_default_manual_review"],
            "dry_run": True,
            "send_triggered": False,
        }


def test_email_reply_graph_loads_context_and_retrieves_knowledge_through_api_client() -> None:
    api_client = FakeEmailReplyApiClient()
    runner = EmailReplyGraphRunner(api_client=api_client)

    result = runner.run(
        EmailReplyGraphState(
            request_id=uuid4(),
            thread_id=uuid4(),
            message_id=uuid4(),
            customer_id=uuid4(),
            draft_id=uuid4(),
            prompt={"template_id": str(uuid4()), "version": "email-reply-v3"},
            options={
                "language": "ru",
                "channel": "email",
                "content_types": ["qa_entry", "email_reply_template"],
                "business_scene": "first_touch_faq",
                "auto_send_candidate": True,
                "market": "Russia",
                "tone": "professional",
                "limit": 5,
            },
        )
    )

    assert result.executed_nodes == [
        "load_context",
        "retrieve_knowledge",
        "draft_reply",
        "schema_validation",
        "auto_send_check",
        "route_decision",
    ]
    assert api_client.context_calls[0].schema_version == "email-reply-v1"
    assert api_client.knowledge_calls == [
        {
            "query": "Нужны авто",
            "language": "ru",
            "channel": "email",
            "content_types": ["qa_entry", "email_reply_template"],
            "business_scene": "first_touch_faq",
            "auto_send_candidate": True,
            "market": "Russia",
            "tone": "professional",
            "limit": 5,
        }
    ]
    assert result.output.schema_version == "email-reply-v1"
    assert result.output.knowledge_hits[0].title == "FAQ"
    assert result.output.manual_review_required is True
    assert result.output.audit["writes_core_tables"] is False
    assert result.output.audit["executed_nodes"] == [
        "load_context",
        "retrieve_knowledge",
        "draft_reply",
        "schema_validation",
        "auto_send_check",
        "route_decision",
    ]


def test_email_reply_graph_fails_when_internal_api_auth_fails_and_records_reason() -> None:
    runner = EmailReplyGraphRunner(api_client=FakeEmailReplyApiClient(fail_context=True))

    with pytest.raises(RuntimeError) as exc_info:
        runner.run(
            EmailReplyGraphState(
                request_id=uuid4(),
                thread_id=uuid4(),
                message_id=uuid4(),
                options={},
            )
        )

    assert "apps/api internal auth failed" in str(exc_info.value)
    assert runner.executed_nodes == ["load_context"]


def test_email_reply_api_client_uses_internal_context_and_knowledge_endpoints(monkeypatch) -> None:
    calls = []

    class FakeResponse:
        status_code = 200

        @staticmethod
        def json():
            return {}

    def fake_post(url, **kwargs):
        calls.append({"url": url, **kwargs})
        return FakeResponse()

    monkeypatch.setattr("app.adapters.email_reply_api.httpx.post", fake_post)
    client = EmailReplyApiClient(base_url="http://api.test", api_key="secret")

    client.load_context(
        api_client_envelope := __import__(
            "app.schemas.email_reply",
            fromlist=["EmailReplyRequestEnvelope"],
        ).EmailReplyRequestEnvelope(
            request_id=uuid4(),
            thread_id=uuid4(),
            message_id=uuid4(),
        )
    )
    client.retrieve_knowledge(
        query="logistics",
        language="ru",
        channel="email",
        content_types=["qa_entry"],
        business_scene="first_touch_faq",
        auto_send_candidate=True,
        market="Russia",
        tone="professional",
        limit=5,
    )

    assert api_client_envelope.schema_version == "email-reply-v1"
    assert calls[0]["url"] == "http://api.test/internal/email-reply/context"
    assert calls[1]["url"] == "http://api.test/internal/email-reply/knowledge"
    assert calls[0]["headers"] == {"X-Agents-Api-Key": "secret"}


def test_email_reply_api_client_uses_internal_auto_send_check_endpoint(monkeypatch) -> None:
    calls = []

    class FakeResponse:
        status_code = 200

        @staticmethod
        def json():
            return {"route": "hold_for_manual_review"}

    def fake_post(url, **kwargs):
        calls.append({"url": url, **kwargs})
        return FakeResponse()

    monkeypatch.setattr("app.adapters.email_reply_api.httpx.post", fake_post)
    client = EmailReplyApiClient(base_url="http://api.test", api_key="secret")

    envelope = __import__(
        "app.schemas.email_reply",
        fromlist=["EmailReplyRequestEnvelope"],
    ).EmailReplyRequestEnvelope(
        request_id=uuid4(),
        thread_id=uuid4(),
        message_id=uuid4(),
    )
    response = client.auto_send_check(
        envelope=envelope,
        output={"schema_version": "email-reply-v1"},
        context={},
        knowledge_hits=[],
        options={},
        dry_run=True,
    )

    assert response["route"] == "hold_for_manual_review"
    assert calls[0]["url"] == "http://api.test/internal/email-reply/auto-send-check"
    assert calls[0]["headers"] == {"X-Agents-Api-Key": "secret"}
    assert calls[0]["json"]["dry_run"] is True
