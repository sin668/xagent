from __future__ import annotations

from dataclasses import dataclass

from app.models.email_reply_draft import EmailReplyDraft
from app.models.enums import EmailReplyDraftStatus
from app.services.email_reply_auto_send import EmailReplyAutoSendEligibilityDecision


EMAIL_REPLY_HARD_BLOCK_RULE_VERSION = "phase5-email-reply-hard-block-v1"

_DE_GRADES = {"watch", "invalid", "d", "e"}
_COMPLAINT_FLAGS = {"complaint", "stop_contact", "report", "threat_report", "unsubscribe"}
_SENSITIVE_TOPIC_REASONS = {
    "payment": ("sensitive_payment", "来信或回复涉及付款/收款，禁止自动发送。", "high"),
    "price": ("sensitive_price", "来信或回复涉及价格承诺，禁止自动发送。", "high"),
    "contract": ("sensitive_contract", "来信或回复涉及合同条款，禁止自动发送。", "high"),
    "invoice": ("sensitive_invoice", "来信或回复涉及发票/税务，禁止自动发送。", "high"),
    "tax": ("sensitive_tax", "来信或回复涉及发票/税务，禁止自动发送。", "high"),
    "legal": ("sensitive_legal", "来信或回复涉及法律合规，禁止自动发送。", "high"),
    "delivery": ("sensitive_delivery", "来信或回复涉及交付/物流承诺，禁止自动发送。", "high"),
    "sanctions": ("sensitive_sanctions", "来信或回复涉及制裁、出口管制或禁运，禁止自动发送。", "critical"),
    "export_control": ("sensitive_sanctions", "来信或回复涉及制裁、出口管制或禁运，禁止自动发送。", "critical"),
    "embargo": ("sensitive_sanctions", "来信或回复涉及制裁、出口管制或禁运，禁止自动发送。", "critical"),
}
_BLOCKED_CHANNEL_RISKS = {"forbidden"}
_MANUAL_REVIEW_CHANNEL_RISKS = {"high"}


@dataclass(frozen=True)
class EmailReplyHardBlockInput:
    customer_do_not_contact: bool
    customer_grade: str | None
    customer_status: str | None
    inbound_risk_flags: list[str]
    sensitive_topics: list[str]
    reply_language_confident: bool
    has_same_language_knowledge: bool
    has_cited_knowledge_evidence: bool
    knowledge_retrieval_confident: bool
    channel_risk_level: str | None


@dataclass(frozen=True)
class EmailReplyHardBlockDecision:
    hard_blocked: bool
    route: str
    rule_version: str
    block_reasons: list[dict]
    manual_review_required: bool
    manual_review_reason: str | None = None

    def to_decision_json(self) -> dict:
        return {
            "hard_block_rule_version": self.rule_version,
            "route": self.route,
            "hard_blocked": self.hard_blocked,
            "auto_send_allowed": False,
            "manual_review_required": self.manual_review_required,
            "manual_review_reason": self.manual_review_reason,
            "block_reasons": self.block_reasons,
        }


class EmailReplyHardBlockService:
    @classmethod
    def evaluate(cls, input_data: EmailReplyHardBlockInput) -> EmailReplyHardBlockDecision:
        reasons: list[dict] = []

        if input_data.customer_do_not_contact or cls._normalize(input_data.customer_status) == "do_not_contact":
            reasons.append(cls._reason("customer_do_not_contact", "客户已标记勿扰或 DNC。", "critical"))

        if cls._normalize(input_data.customer_grade) in _DE_GRADES:
            reasons.append(cls._reason("customer_de_grade", "D/E 级客户不得自动发送邮件。", "critical"))

        normalized_flags = {cls._normalize(flag) for flag in input_data.inbound_risk_flags}
        if normalized_flags & _COMPLAINT_FLAGS:
            reasons.append(cls._reason("inbound_complaint", "客户来信包含投诉、举报或要求停止联系。", "critical"))

        seen_sensitive_codes: set[str] = set()
        for topic in input_data.sensitive_topics:
            reason_spec = _SENSITIVE_TOPIC_REASONS.get(cls._normalize(topic))
            if reason_spec is None:
                continue
            code, message, severity = reason_spec
            if code in seen_sensitive_codes:
                continue
            seen_sensitive_codes.add(code)
            reasons.append(cls._reason(code, message, severity))

        if not input_data.reply_language_confident:
            reasons.append(cls._reason("reply_language_uncertain", "回复语言识别或生成置信度不足。", "high"))

        if not input_data.has_same_language_knowledge:
            reasons.append(cls._reason("missing_same_language_knowledge", "缺少同语言知识，禁止自动发送。", "high"))

        if not input_data.has_cited_knowledge_evidence:
            reasons.append(cls._reason("missing_knowledge_evidence", "缺少可引用知识证据，禁止自动发送。", "high"))

        if not input_data.knowledge_retrieval_confident:
            reasons.append(cls._reason("knowledge_retrieval_uncertain", "知识召回不足或置信度不足。", "high"))

        channel_risk = cls._normalize(input_data.channel_risk_level)
        if channel_risk in _BLOCKED_CHANNEL_RISKS:
            reasons.append(cls._reason("forbidden_channel", "Forbidden 风险渠道不得自动发送邮件。", "critical"))
        if channel_risk in _MANUAL_REVIEW_CHANNEL_RISKS:
            reasons.append(cls._reason("high_risk_channel", "High 风险渠道必须人工复核。", "high"))

        if not reasons:
            return EmailReplyHardBlockDecision(
                hard_blocked=False,
                route="continue_auto_send_check",
                rule_version=EMAIL_REPLY_HARD_BLOCK_RULE_VERSION,
                block_reasons=[],
                manual_review_required=False,
                manual_review_reason=None,
            )

        route = "hold_for_manual_review" if cls._only_high_risk_channel_reason(reasons) else "blocked"
        return EmailReplyHardBlockDecision(
            hard_blocked=True,
            route=route,
            rule_version=EMAIL_REPLY_HARD_BLOCK_RULE_VERSION,
            block_reasons=reasons,
            manual_review_required=True,
            manual_review_reason="命中硬拦截规则，禁止自动发送。",
        )

    @staticmethod
    def enforce_priority(
        hard_block_decision: EmailReplyHardBlockDecision,
        auto_send_decision: EmailReplyAutoSendEligibilityDecision,
    ) -> dict:
        if not hard_block_decision.hard_blocked:
            decision_json = auto_send_decision.to_decision_json()
            decision_json["hard_block_rule_version"] = hard_block_decision.rule_version
            decision_json["hard_blocked"] = False
            decision_json["block_reasons"] = []
            return decision_json

        decision_json = hard_block_decision.to_decision_json()
        decision_json["auto_send_allowed"] = False
        decision_json["auto_send_decision"] = auto_send_decision.to_decision_json()
        return decision_json

    @staticmethod
    def apply_to_draft(
        draft: EmailReplyDraft,
        decision: EmailReplyHardBlockDecision,
    ) -> EmailReplyDraft:
        if not decision.hard_blocked:
            return draft
        draft.auto_send_allowed = False
        draft.auto_send_decision_json = decision.to_decision_json()
        draft.manual_review_required = True
        draft.manual_review_reason = decision.manual_review_reason
        if decision.route == "blocked":
            draft.status = EmailReplyDraftStatus.BLOCKED
        else:
            draft.status = EmailReplyDraftStatus.PENDING_REVIEW
        return draft

    @staticmethod
    def _reason(code: str, message: str, severity: str) -> dict:
        return {"code": code, "message": message, "severity": severity}

    @staticmethod
    def _normalize(value: str | None) -> str:
        return (value or "").strip().lower()

    @staticmethod
    def _only_high_risk_channel_reason(reasons: list[dict]) -> bool:
        return len(reasons) == 1 and reasons[0].get("code") == "high_risk_channel"
