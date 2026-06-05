from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.email_reply import (
    EMAIL_REPLY_SCHEMA_VERSION,
    EmailReplyAgentOutput,
    EmailReplyKnowledgeHit,
    EmailReplyRequestEnvelope,
)


def test_email_reply_request_envelope_uses_fixed_schema_version_and_business_context() -> None:
    request_id = uuid4()
    envelope = EmailReplyRequestEnvelope(
        request_id=request_id,
        schema_version=EMAIL_REPLY_SCHEMA_VERSION,
        draft_id=uuid4(),
        thread_id=uuid4(),
        message_id=uuid4(),
        customer_id=uuid4(),
        context={"customer": {"name": "Moscow Auto Dealer"}},
        prompt={"template_id": str(uuid4()), "version": "email-reply-v3"},
        options={"agent_mode": "dry_run"},
    )

    assert envelope.schema_version == "email-reply-v1"
    assert envelope.request_id == request_id
    assert envelope.context["customer"]["name"] == "Moscow Auto Dealer"


def test_email_reply_output_schema_contains_required_reply_risk_and_audit_fields() -> None:
    output = EmailReplyAgentOutput(
        schema_version=EMAIL_REPLY_SCHEMA_VERSION,
        reply_language="ru",
        detected_language="en",
        suggested_subject="Vehicle sourcing options",
        suggested_body="Здравствуйте, можем уточнить детали запроса.",
        knowledge_hits=[
            EmailReplyKnowledgeHit(
                knowledge_item_id=str(uuid4()),
                title="Shipping FAQ",
                version="v2",
                similarity_score=0.91,
                evidence_note="FAQ contains shipping process wording.",
            )
        ],
        risk_flags=["manual_review_required"],
        auto_send_allowed=False,
        manual_review_required=True,
        next_action="hold_for_manual_review",
        audit={
            "writes_core_tables": False,
            "executed_nodes": ["load_context", "retrieve_knowledge", "draft_reply", "schema_validation"],
        },
    )

    payload = output.model_dump(mode="json")

    assert payload["schema_version"] == "email-reply-v1"
    assert payload["reply_language"] == "ru"
    assert payload["knowledge_hits"][0]["title"] == "Shipping FAQ"
    assert payload["auto_send_allowed"] is False
    assert payload["manual_review_required"] is True
    assert payload["next_action"] == "hold_for_manual_review"
    assert payload["audit"]["writes_core_tables"] is False


def test_email_reply_output_rejects_invalid_schema_version_and_core_table_writes() -> None:
    with pytest.raises(ValidationError) as schema_error:
        EmailReplyAgentOutput(
            schema_version="email-reply-v0",
            reply_language="ru",
            suggested_subject="Subject",
            suggested_body="Body",
            next_action="hold_for_manual_review",
        )

    assert "schema_version" in str(schema_error.value)

    with pytest.raises(ValidationError) as audit_error:
        EmailReplyAgentOutput(
            schema_version=EMAIL_REPLY_SCHEMA_VERSION,
            reply_language="ru",
            suggested_subject="Subject",
            suggested_body="Body",
            auto_send_allowed=True,
            manual_review_required=False,
            next_action="auto_send_candidate",
            audit={"writes_core_tables": True},
        )

    assert "writes_core_tables" in str(audit_error.value)


def test_email_reply_output_requires_manual_review_when_auto_send_is_not_allowed() -> None:
    with pytest.raises(ValidationError) as error:
        EmailReplyAgentOutput(
            schema_version=EMAIL_REPLY_SCHEMA_VERSION,
            reply_language="ru",
            suggested_subject="Subject",
            suggested_body="Body",
            auto_send_allowed=False,
            manual_review_required=False,
            next_action="auto_send_candidate",
            audit={"writes_core_tables": False},
        )

    assert "manual_review_required" in str(error.value)
