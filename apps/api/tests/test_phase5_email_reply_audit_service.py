from uuid import uuid4

from app.models.email_reply_draft import EmailReplyDraft
from app.models.email_send_attempt import EmailSendAttempt
from app.models.enums import EmailReplyDraftStatus, EmailSendAttemptStatus
from app.services.email_reply_audit import EmailReplyAuditService


def _draft() -> EmailReplyDraft:
    return EmailReplyDraft(
        ai_suggested_subject="AI subject",
        ai_suggested_body="AI body with original suggested wording.",
        final_subject=None,
        final_body=None,
        knowledge_hits_json=[
            {"knowledge_item_id": str(uuid4()), "title": "FAQ", "version": "v1", "similarity_score": 0.92}
        ],
        prompt_version="email-reply-v3",
        model="gpt-test",
        status=EmailReplyDraftStatus.DRAFTED,
    )


def test_email_reply_audit_preserves_ai_suggestion_when_human_edits_final_content() -> None:
    draft = _draft()

    result = EmailReplyAuditService.apply_human_edit(
        draft,
        final_subject="Human subject",
        final_body="Human edited body with safer wording.",
        reviewed_by="运营A",
    )

    assert draft.ai_suggested_subject == "AI subject"
    assert draft.ai_suggested_body == "AI body with original suggested wording."
    assert draft.final_subject == "Human subject"
    assert draft.final_body == "Human edited body with safer wording."
    assert draft.reviewed_by == "运营A"
    assert draft.reviewed_at is not None
    assert draft.status == EmailReplyDraftStatus.PENDING_REVIEW
    assert result["ai_content_preserved"] is True
    assert result["edit_metrics"]["changed"] is True
    assert result["edit_metrics"]["ai_body_length"] == len("AI body with original suggested wording.")


def test_email_reply_audit_statistics_detect_no_edit_and_edit_distance() -> None:
    unchanged = EmailReplyAuditService.calculate_edit_metrics(
        ai_subject="Same",
        ai_body="Same body",
        final_subject="Same",
        final_body="Same body",
    )
    changed = EmailReplyAuditService.calculate_edit_metrics(
        ai_subject="AI subject",
        ai_body="Short AI body",
        final_subject="Human subject",
        final_body="Longer human body with reviewed wording",
    )

    assert unchanged["changed"] is False
    assert unchanged["body_length_delta"] == 0
    assert changed["changed"] is True
    assert changed["subject_changed"] is True
    assert changed["body_length_delta"] == len("Longer human body with reviewed wording") - len("Short AI body")
    assert changed["body_similarity_ratio"] < 1


def test_email_reply_audit_builds_send_trace_with_prompt_model_knowledge_and_actor() -> None:
    draft = _draft()
    EmailReplyAuditService.apply_human_edit(
        draft,
        final_subject="Human subject",
        final_body="Human edited body with safer wording.",
        reviewed_by="运营A",
    )
    attempt = EmailSendAttempt(
        provider="smtp",
        from_email="sales@example.com",
        to_emails=["dealer@example.ru"],
        subject_snapshot="Human subject",
        body_text_snapshot="Human edited body with safer wording.",
        status=EmailSendAttemptStatus.SENT,
        attempt_count=1,
    )

    trace = EmailReplyAuditService.build_send_trace(
        draft,
        attempt=attempt,
        actor="销售B",
        action="manual_send_confirmed",
    )

    assert trace["actor"] == "销售B"
    assert trace["action"] == "manual_send_confirmed"
    assert trace["prompt_version"] == "email-reply-v3"
    assert trace["model"] == "gpt-test"
    assert trace["knowledge_hits"][0]["title"] == "FAQ"
    assert trace["ai_suggested_body"] == "AI body with original suggested wording."
    assert trace["final_body"] == "Human edited body with safer wording."
    assert trace["send_attempt"]["provider"] == "smtp"
    assert trace["send_attempt"]["status"] == "sent"
