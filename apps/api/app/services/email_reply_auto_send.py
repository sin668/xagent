from __future__ import annotations

from dataclasses import dataclass

from app.models.email_reply_draft import EmailReplyDraft


AUTO_SEND_ELIGIBILITY_RULE_VERSION = "phase5-auto-send-eligibility-v1"

_FIXED_FAQ_CONTENT_TYPES = {"qa_entry", "fixed_faq"}
_FIXED_FAQ_BUSINESS_SCENES = {"fixed_faq", "faq_reply", "first_touch_faq"}
_LOW_RISK_LEVELS = {"low"}


@dataclass(frozen=True)
class EmailReplyAutoSendEligibilityInput:
    customer_is_whitelisted: bool
    knowledge_content_type: str | None
    business_scene: str | None
    scene_risk_level: str | None
    is_first_touch: bool
    knowledge_auto_reply_allowed: bool
    knowledge_embedding_ready: bool
    reply_language_confident: bool


@dataclass(frozen=True)
class EmailReplyAutoSendEligibilityDecision:
    auto_send_allowed: bool
    route: str
    rule_version: str
    reasons: list[str]
    manual_review_required: bool
    manual_review_reason: str | None = None

    def to_decision_json(self) -> dict:
        return {
            "rule_version": self.rule_version,
            "route": self.route,
            "auto_send_allowed": self.auto_send_allowed,
            "reasons": self.reasons,
            "manual_review_required": self.manual_review_required,
            "manual_review_reason": self.manual_review_reason,
        }


class EmailReplyAutoSendEligibilityService:
    @classmethod
    def evaluate(cls, input_data: EmailReplyAutoSendEligibilityInput) -> EmailReplyAutoSendEligibilityDecision:
        reasons: list[str] = []

        cls._append_boolean_reason(
            reasons,
            passed=input_data.customer_is_whitelisted,
            passed_reason="whitelisted_customer",
            failed_reason="not_whitelisted_customer",
        )

        is_fixed_faq = cls._is_fixed_faq(input_data.knowledge_content_type, input_data.business_scene)
        cls._append_boolean_reason(
            reasons,
            passed=is_fixed_faq,
            passed_reason="fixed_faq",
            failed_reason="not_fixed_faq",
        )

        cls._append_boolean_reason(
            reasons,
            passed=input_data.is_first_touch,
            passed_reason="first_touch",
            failed_reason="not_first_touch",
        )

        is_low_risk = cls._normalize(input_data.scene_risk_level) in _LOW_RISK_LEVELS
        cls._append_boolean_reason(
            reasons,
            passed=is_low_risk,
            passed_reason="low_risk_scene",
            failed_reason="not_low_risk_scene",
        )

        cls._append_boolean_reason(
            reasons,
            passed=input_data.knowledge_auto_reply_allowed,
            passed_reason="knowledge_auto_reply_allowed",
            failed_reason="knowledge_auto_reply_not_allowed",
        )

        cls._append_boolean_reason(
            reasons,
            passed=input_data.knowledge_embedding_ready,
            passed_reason="knowledge_embedding_ready",
            failed_reason="knowledge_embedding_not_ready",
        )

        cls._append_boolean_reason(
            reasons,
            passed=input_data.reply_language_confident,
            passed_reason="reply_language_confident",
            failed_reason="reply_language_not_confident",
        )

        auto_send_allowed = all(
            (
                input_data.customer_is_whitelisted,
                is_fixed_faq,
                input_data.is_first_touch,
                is_low_risk,
                input_data.knowledge_auto_reply_allowed,
                input_data.knowledge_embedding_ready,
                input_data.reply_language_confident,
            )
        )
        if auto_send_allowed:
            return EmailReplyAutoSendEligibilityDecision(
                auto_send_allowed=True,
                route="auto_send_candidate",
                rule_version=AUTO_SEND_ELIGIBILITY_RULE_VERSION,
                reasons=reasons,
                manual_review_required=False,
                manual_review_reason=None,
            )

        return EmailReplyAutoSendEligibilityDecision(
            auto_send_allowed=False,
            route="hold_for_manual_review",
            rule_version=AUTO_SEND_ELIGIBILITY_RULE_VERSION,
            reasons=reasons,
            manual_review_required=True,
            manual_review_reason="未满足自动发送准入条件，进入人工确认。",
        )

    @staticmethod
    def apply_to_draft(
        draft: EmailReplyDraft,
        decision: EmailReplyAutoSendEligibilityDecision,
    ) -> EmailReplyDraft:
        draft.auto_send_allowed = decision.auto_send_allowed
        draft.auto_send_decision_json = decision.to_decision_json()
        draft.manual_review_required = decision.manual_review_required
        draft.manual_review_reason = decision.manual_review_reason
        return draft

    @staticmethod
    def _append_boolean_reason(
        reasons: list[str],
        *,
        passed: bool,
        passed_reason: str,
        failed_reason: str,
    ) -> None:
        reasons.append(passed_reason if passed else failed_reason)

    @classmethod
    def _is_fixed_faq(cls, content_type: str | None, business_scene: str | None) -> bool:
        return cls._normalize(content_type) in _FIXED_FAQ_CONTENT_TYPES and cls._normalize(business_scene) in (
            _FIXED_FAQ_BUSINESS_SCENES
        )

    @staticmethod
    def _normalize(value: str | None) -> str:
        return (value or "").strip().lower()
