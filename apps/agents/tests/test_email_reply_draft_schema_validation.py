from uuid import uuid4

import pytest

from app.graphs.email_reply import EmailReplyGraphRunner, EmailReplyGraphState


class FakeEmailReplyApiClient:
    def load_context(self, envelope):
        return {
            "customer": {"name": "Moscow Auto Dealer"},
            "inbound_message": {"language": "ru", "body_text": "Нужны автомобили Toyota"},
            "audit_summary": {"included_sections": ["customer", "inbound_message"]},
        }

    def retrieve_knowledge(self, **kwargs):
        return {
            "items": [
                {
                    "knowledge_item_id": str(uuid4()),
                    "title": "FAQ Toyota sourcing",
                    "version": "v1",
                    "similarity_score": 0.91,
                    "evidence_note": "FAQ contains approved first reply wording.",
                }
            ],
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


class MissingFieldsDrafter:
    def draft(self, *, context, knowledge_hits, prompt, options):
        return {"suggested_body": "Здравствуйте, уточним детали."}


class InvalidSchemaDrafter:
    def draft(self, *, context, knowledge_hits, prompt, options):
        return {
            "schema_version": "email-reply-v0",
            "reply_language": "ru",
            "suggested_subject": "Toyota",
            "suggested_body": "Здравствуйте",
            "auto_send_allowed": True,
            "manual_review_required": False,
            "next_action": "auto_send_candidate",
            "audit": {"writes_core_tables": False},
        }


class AutoSendDrafter:
    def draft(self, *, context, knowledge_hits, prompt, options):
        return {
            "schema_version": "email-reply-v1",
            "reply_language": "ru",
            "detected_language": "ru",
            "suggested_subject": "Toyota sourcing",
            "suggested_body": "Здравствуйте, можем уточнить детали запроса.",
            "auto_send_allowed": True,
            "manual_review_required": False,
            "next_action": "auto_send_candidate",
            "risk_flags": [],
            "audit": {"writes_core_tables": False},
        }


def test_email_reply_draft_reply_normalizes_missing_fields_without_fabrication() -> None:
    runner = EmailReplyGraphRunner(api_client=FakeEmailReplyApiClient(), llm_drafter=MissingFieldsDrafter())

    result = runner.run(
        EmailReplyGraphState(
            request_id=uuid4(),
            thread_id=uuid4(),
            message_id=uuid4(),
            options={"language": "ru", "auto_send_candidate": False},
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
    assert result.output.schema_version == "email-reply-v1"
    assert result.output.reply_language == "Unknown"
    assert result.output.suggested_subject == "Unknown"
    assert result.output.suggested_body == "Здравствуйте, уточним детали."
    assert result.output.knowledge_hits[0].title == "FAQ Toyota sourcing"
    assert result.output.auto_send_allowed is False
    assert result.output.manual_review_required is True
    assert result.output.next_action == "hold_for_manual_review"
    assert "llm_missing_required_fields" in result.output.risk_flags
    assert result.output.audit["schema_validation_status"] == "succeeded"


def test_email_reply_draft_reply_disables_auto_send_when_knowledge_hits_are_missing() -> None:
    class EmptyKnowledgeApi(FakeEmailReplyApiClient):
        def retrieve_knowledge(self, **kwargs):
            return {"items": [], "total": 0, "rejection_reason": "缺少同语言 embedding_ready 知识，不能自动发送。"}

    runner = EmailReplyGraphRunner(api_client=EmptyKnowledgeApi(), llm_drafter=AutoSendDrafter())

    result = runner.run(
        EmailReplyGraphState(
            request_id=uuid4(),
            thread_id=uuid4(),
            message_id=uuid4(),
            options={"language": "ru", "auto_send_candidate": True},
        )
    )

    assert result.output.auto_send_allowed is False
    assert result.output.manual_review_required is True
    assert result.output.next_action == "hold_for_manual_review"
    assert "knowledge_hits_insufficient" in result.output.risk_flags
    assert result.output.audit["knowledge_hit_count"] == 0


def test_email_reply_schema_validation_failure_records_node_trace() -> None:
    runner = EmailReplyGraphRunner(api_client=FakeEmailReplyApiClient(), llm_drafter=InvalidSchemaDrafter())

    with pytest.raises(ValueError) as exc_info:
        runner.run(
            EmailReplyGraphState(
                request_id=uuid4(),
                thread_id=uuid4(),
                message_id=uuid4(),
                options={"language": "ru", "auto_send_candidate": True},
            )
        )

    assert "schema_validation" in str(exc_info.value)
    assert runner.last_error["failed_node"] == "schema_validation"
    assert runner.last_error["error_type"] == "schema_validation_error"
    assert runner.last_error["trace"]["node"] == "schema_validation"
    assert runner.last_error["trace"]["status"] == "failed"
