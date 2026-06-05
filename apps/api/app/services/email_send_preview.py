from __future__ import annotations

from app.models.email_reply_draft import EmailReplyDraft


class EmailSendPreviewService:
    @staticmethod
    def build_preview(
        draft: EmailReplyDraft,
        *,
        sender_from_email: str | None,
        recent_send_count: int = 0,
        frequency_limit: int = 3,
    ) -> dict:
        customer = getattr(draft, "customer", None)
        message = getattr(draft, "message", None)
        subject = draft.final_subject or draft.ai_suggested_subject or "Unknown"
        body_text = draft.final_body or draft.ai_suggested_body or "Unknown"
        knowledge_hits = list(draft.knowledge_hits_json or [])
        decision_json = draft.auto_send_decision_json or {}

        reasons: list[str] = []
        hard_blocks: list[str] = []

        if bool(getattr(customer, "do_not_contact", False)) or _normalize(getattr(customer, "status", None)) == "do_not_contact":
            hard_blocks.append("customer_do_not_contact")

        if _normalize(getattr(customer, "grade", None)) in {"watch", "invalid", "d", "e"}:
            hard_blocks.append("customer_de_grade")

        if bool(decision_json.get("hard_blocked")):
            hard_blocks.extend(_extract_block_codes(decision_json.get("block_reasons") or []))

        hard_blocks = _unique(hard_blocks)
        if hard_blocks:
            return _response(
                draft=draft,
                from_email=sender_from_email,
                to_emails=_recipient_emails(message),
                cc_emails=_cc_emails(message),
                subject=subject,
                body_text=body_text,
                knowledge_hit_count=len(knowledge_hits),
                decision="blocked",
                allow_auto_send=False,
                reasons=reasons,
                hard_blocks=hard_blocks,
                manual_review_required=True,
                manual_review_reason="命中硬拦截规则，禁止自动发送。",
            )

        if not knowledge_hits:
            reasons.append("missing_knowledge_evidence")
        if frequency_limit >= 0 and recent_send_count >= frequency_limit:
            reasons.append("frequency_limit_reached")
        if not bool(draft.auto_send_allowed):
            reasons.append("auto_send_not_allowed")
        if bool(draft.manual_review_required):
            reasons.append("manual_review_required")

        reasons = _unique(reasons)
        if reasons:
            return _response(
                draft=draft,
                from_email=sender_from_email,
                to_emails=_recipient_emails(message),
                cc_emails=_cc_emails(message),
                subject=subject,
                body_text=body_text,
                knowledge_hit_count=len(knowledge_hits),
                decision="manual_review",
                allow_auto_send=False,
                reasons=reasons,
                hard_blocks=[],
                manual_review_required=True,
                manual_review_reason=draft.manual_review_reason or "发送前检查未满足自动发送条件，需要人工复核。",
            )

        return _response(
            draft=draft,
            from_email=sender_from_email,
            to_emails=_recipient_emails(message),
            cc_emails=_cc_emails(message),
            subject=subject,
            body_text=body_text,
            knowledge_hit_count=len(knowledge_hits),
            decision="auto_send_allowed",
            allow_auto_send=True,
            reasons=list(decision_json.get("reasons") or []),
            hard_blocks=[],
            manual_review_required=False,
            manual_review_reason=None,
        )


def _response(
    *,
    draft: EmailReplyDraft,
    from_email: str | None,
    to_emails: list[str],
    cc_emails: list[str],
    subject: str,
    body_text: str,
    knowledge_hit_count: int,
    decision: str,
    allow_auto_send: bool,
    reasons: list[str],
    hard_blocks: list[str],
    manual_review_required: bool,
    manual_review_reason: str | None,
) -> dict:
    return {
        "reply_id": str(draft.id),
        "decision": decision,
        "allow_auto_send": allow_auto_send,
        "send_triggered": False,
        "from_email": from_email or "Unknown",
        "to_emails": to_emails,
        "cc_emails": cc_emails,
        "subject": subject,
        "body_text": body_text,
        "knowledge_hit_count": knowledge_hit_count,
        "reasons": reasons,
        "hard_blocks": hard_blocks,
        "manual_review_required": manual_review_required,
        "manual_review_reason": manual_review_reason,
    }


def _recipient_emails(message) -> list[str]:
    value = getattr(message, "from_email", None)
    return [value] if isinstance(value, str) and value.strip() else []


def _cc_emails(message) -> list[str]:
    value = getattr(message, "cc_emails", None)
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str) and item.strip()]
    return []


def _extract_block_codes(block_reasons: list) -> list[str]:
    codes: list[str] = []
    for reason in block_reasons:
        if isinstance(reason, dict):
            code = reason.get("code")
            if isinstance(code, str) and code.strip():
                codes.append(code)
        elif isinstance(reason, str) and reason.strip():
            codes.append(reason)
    return codes


def _normalize(value) -> str:
    raw = getattr(value, "value", value)
    return str(raw or "").strip().lower()


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result
