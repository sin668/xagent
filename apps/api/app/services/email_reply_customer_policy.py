from __future__ import annotations

from app.models.customer import Customer
from app.models.email_reply_draft import EmailReplyDraft
from app.models.enums import CustomerGrade
from app.services.email_reply_hard_block import (
    EmailReplyHardBlockDecision,
    EmailReplyHardBlockInput,
    EmailReplyHardBlockService,
)


class EmailReplyCustomerPolicyService:
    @classmethod
    def evaluate_customer_policy(
        cls,
        customer: Customer,
        *,
        reply_language_confident: bool,
        has_same_language_knowledge: bool,
        has_cited_knowledge_evidence: bool,
        knowledge_retrieval_confident: bool,
        channel_risk_level: str | None,
        inbound_risk_flags: list[str] | None = None,
        sensitive_topics: list[str] | None = None,
    ) -> EmailReplyHardBlockDecision:
        return EmailReplyHardBlockService.evaluate(
            EmailReplyHardBlockInput(
                customer_do_not_contact=bool(getattr(customer, "do_not_contact", False)),
                customer_grade=cls._grade_value(getattr(customer, "grade", None)),
                customer_status=cls._status_value(getattr(customer, "status", None)),
                inbound_risk_flags=list(inbound_risk_flags or []),
                sensitive_topics=list(sensitive_topics or []),
                reply_language_confident=reply_language_confident,
                has_same_language_knowledge=has_same_language_knowledge,
                has_cited_knowledge_evidence=has_cited_knowledge_evidence,
                knowledge_retrieval_confident=knowledge_retrieval_confident,
                channel_risk_level=channel_risk_level,
            )
        )

    @classmethod
    def apply_customer_policy_to_draft(
        cls,
        draft: EmailReplyDraft,
        customer: Customer,
        *,
        reply_language_confident: bool,
        has_same_language_knowledge: bool,
        has_cited_knowledge_evidence: bool,
        knowledge_retrieval_confident: bool,
        channel_risk_level: str | None,
        inbound_risk_flags: list[str] | None = None,
        sensitive_topics: list[str] | None = None,
    ) -> EmailReplyHardBlockDecision:
        decision = cls.evaluate_customer_policy(
            customer,
            reply_language_confident=reply_language_confident,
            has_same_language_knowledge=has_same_language_knowledge,
            has_cited_knowledge_evidence=has_cited_knowledge_evidence,
            knowledge_retrieval_confident=knowledge_retrieval_confident,
            channel_risk_level=channel_risk_level,
            inbound_risk_flags=inbound_risk_flags,
            sensitive_topics=sensitive_topics,
        )
        EmailReplyHardBlockService.apply_to_draft(draft, decision)
        if decision.hard_blocked:
            draft.manual_review_reason = "命中 DNC/勿扰或 D/E 客户阻断规则，禁止自动发送。"
            draft.auto_send_decision_json = {
                **draft.auto_send_decision_json,
                "manual_review_reason": draft.manual_review_reason,
                "customer_policy": cls.customer_policy_snapshot(customer),
            }
        return decision

    @classmethod
    def customer_policy_snapshot(cls, customer: Customer) -> dict:
        return {
            "customer_id": str(getattr(customer, "id", "")) if getattr(customer, "id", None) else None,
            "customer_name": getattr(customer, "name", None),
            "grade": cls._grade_value(getattr(customer, "grade", None)),
            "external_grade_label": cls.external_grade_label(getattr(customer, "grade", None)),
            "status": cls._status_value(getattr(customer, "status", None)),
            "do_not_contact": bool(getattr(customer, "do_not_contact", False)),
            "do_not_contact_reason": getattr(customer, "do_not_contact_reason", None),
        }

    @staticmethod
    def external_grade_label(grade: CustomerGrade | str | None) -> str | None:
        value = EmailReplyCustomerPolicyService._grade_value(grade)
        if value == CustomerGrade.WATCH.value:
            return "D"
        if value == CustomerGrade.INVALID.value:
            return "E"
        return value

    @staticmethod
    def _grade_value(grade: CustomerGrade | str | None) -> str | None:
        return grade.value if hasattr(grade, "value") else grade

    @staticmethod
    def _status_value(status) -> str | None:
        return status.value if hasattr(status, "value") else status
