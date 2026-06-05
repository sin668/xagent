from __future__ import annotations

from datetime import UTC, datetime
from difflib import SequenceMatcher
from typing import Any

from app.models.email_reply_draft import EmailReplyDraft
from app.models.email_send_attempt import EmailSendAttempt
from app.models.enums import EmailReplyDraftStatus


class EmailReplyAuditService:
    @classmethod
    def apply_human_edit(
        cls,
        draft: EmailReplyDraft,
        *,
        final_subject: str | None,
        final_body: str,
        reviewed_by: str,
        reviewed_at: datetime | None = None,
    ) -> dict[str, Any]:
        ai_subject_before = draft.ai_suggested_subject
        ai_body_before = draft.ai_suggested_body

        draft.final_subject = final_subject
        draft.final_body = final_body
        draft.reviewed_by = reviewed_by
        draft.reviewed_at = reviewed_at or datetime.now(UTC)
        if draft.status == EmailReplyDraftStatus.DRAFTED:
            draft.status = EmailReplyDraftStatus.PENDING_REVIEW

        edit_metrics = cls.calculate_edit_metrics(
            ai_subject=ai_subject_before,
            ai_body=ai_body_before,
            final_subject=final_subject,
            final_body=final_body,
        )
        audit_summary = {
            "ai_content_preserved": draft.ai_suggested_subject == ai_subject_before
            and draft.ai_suggested_body == ai_body_before,
            "reviewed_by": reviewed_by,
            "reviewed_at": draft.reviewed_at.isoformat() if draft.reviewed_at else None,
            "edit_metrics": edit_metrics,
        }
        draft.auto_send_decision_json = {
            **(draft.auto_send_decision_json or {}),
            "human_edit_audit": audit_summary,
        }
        return audit_summary

    @classmethod
    def calculate_edit_metrics(
        cls,
        *,
        ai_subject: str | None,
        ai_body: str | None,
        final_subject: str | None,
        final_body: str | None,
    ) -> dict[str, Any]:
        normalized_ai_subject = ai_subject or ""
        normalized_ai_body = ai_body or ""
        normalized_final_subject = final_subject or ""
        normalized_final_body = final_body or ""
        subject_changed = normalized_ai_subject != normalized_final_subject
        body_changed = normalized_ai_body != normalized_final_body
        return {
            "changed": subject_changed or body_changed,
            "subject_changed": subject_changed,
            "body_changed": body_changed,
            "ai_subject_length": len(normalized_ai_subject),
            "final_subject_length": len(normalized_final_subject),
            "subject_length_delta": len(normalized_final_subject) - len(normalized_ai_subject),
            "ai_body_length": len(normalized_ai_body),
            "final_body_length": len(normalized_final_body),
            "body_length_delta": len(normalized_final_body) - len(normalized_ai_body),
            "body_similarity_ratio": round(cls._similarity_ratio(normalized_ai_body, normalized_final_body), 4),
        }

    @classmethod
    def build_send_trace(
        cls,
        draft: EmailReplyDraft,
        *,
        attempt: EmailSendAttempt | None,
        actor: str,
        action: str,
        occurred_at: datetime | None = None,
    ) -> dict[str, Any]:
        timestamp = occurred_at or datetime.now(UTC)
        return {
            "actor": actor,
            "action": action,
            "occurred_at": timestamp.isoformat(),
            "draft_id": str(draft.id) if getattr(draft, "id", None) else None,
            "customer_id": str(draft.customer_id) if getattr(draft, "customer_id", None) else None,
            "message_id": str(draft.message_id) if getattr(draft, "message_id", None) else None,
            "prompt_template_id": str(draft.prompt_template_id) if getattr(draft, "prompt_template_id", None) else None,
            "prompt_version": draft.prompt_version,
            "model": draft.model,
            "knowledge_hits": list(draft.knowledge_hits_json or []),
            "ai_suggested_subject": draft.ai_suggested_subject,
            "ai_suggested_body": draft.ai_suggested_body,
            "final_subject": draft.final_subject,
            "final_body": draft.final_body,
            "reviewed_by": draft.reviewed_by,
            "reviewed_at": draft.reviewed_at.isoformat() if getattr(draft, "reviewed_at", None) else None,
            "edit_metrics": cls.calculate_edit_metrics(
                ai_subject=draft.ai_suggested_subject,
                ai_body=draft.ai_suggested_body,
                final_subject=draft.final_subject,
                final_body=draft.final_body,
            ),
            "send_attempt": cls._serialize_send_attempt(attempt),
        }

    @staticmethod
    def _serialize_send_attempt(attempt: EmailSendAttempt | None) -> dict[str, Any] | None:
        if attempt is None:
            return None
        status = attempt.status.value if hasattr(attempt.status, "value") else attempt.status
        return {
            "id": str(attempt.id) if getattr(attempt, "id", None) else None,
            "provider": attempt.provider,
            "provider_message_id": attempt.provider_message_id,
            "from_email": attempt.from_email,
            "to_emails": list(attempt.to_emails or []),
            "cc_emails": list(attempt.cc_emails or []),
            "bcc_emails": list(attempt.bcc_emails or []),
            "subject_snapshot": attempt.subject_snapshot,
            "body_text_snapshot": attempt.body_text_snapshot,
            "status": status,
            "attempt_count": attempt.attempt_count,
            "error_code": attempt.error_code,
            "error_message": attempt.error_message,
            "bounce_reason": attempt.bounce_reason,
            "sent_at": attempt.sent_at.isoformat() if getattr(attempt, "sent_at", None) else None,
        }

    @staticmethod
    def _similarity_ratio(left: str, right: str) -> float:
        if not left and not right:
            return 1.0
        return SequenceMatcher(a=left, b=right).ratio()
