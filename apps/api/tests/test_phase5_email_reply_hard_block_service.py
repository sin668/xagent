from app.models.email_reply_draft import EmailReplyDraft
from app.models.enums import EmailReplyDraftStatus
from app.services.email_reply_auto_send import EmailReplyAutoSendEligibilityDecision
from app.services.email_reply_hard_block import (
    EMAIL_REPLY_HARD_BLOCK_RULE_VERSION,
    EmailReplyHardBlockInput,
    EmailReplyHardBlockService,
)


def test_email_reply_hard_block_blocks_complaint_dnc_sensitive_topics_language_and_missing_evidence() -> None:
    decision = EmailReplyHardBlockService.evaluate(
        EmailReplyHardBlockInput(
            customer_do_not_contact=True,
            customer_grade="B",
            customer_status="ready_for_sales",
            inbound_risk_flags=["complaint", "stop_contact"],
            sensitive_topics=["payment", "contract", "tax", "legal", "delivery", "sanctions"],
            reply_language_confident=False,
            has_same_language_knowledge=True,
            has_cited_knowledge_evidence=False,
            knowledge_retrieval_confident=False,
            channel_risk_level="Low",
        )
    )

    assert decision.hard_blocked is True
    assert decision.route == "blocked"
    assert decision.rule_version == EMAIL_REPLY_HARD_BLOCK_RULE_VERSION
    assert decision.manual_review_required is True
    assert decision.block_reasons == [
        {"code": "customer_do_not_contact", "message": "客户已标记勿扰或 DNC。", "severity": "critical"},
        {"code": "inbound_complaint", "message": "客户来信包含投诉、举报或要求停止联系。", "severity": "critical"},
        {"code": "sensitive_payment", "message": "来信或回复涉及付款/收款，禁止自动发送。", "severity": "high"},
        {"code": "sensitive_contract", "message": "来信或回复涉及合同条款，禁止自动发送。", "severity": "high"},
        {"code": "sensitive_tax", "message": "来信或回复涉及发票/税务，禁止自动发送。", "severity": "high"},
        {"code": "sensitive_legal", "message": "来信或回复涉及法律合规，禁止自动发送。", "severity": "high"},
        {"code": "sensitive_delivery", "message": "来信或回复涉及交付/物流承诺，禁止自动发送。", "severity": "high"},
        {"code": "sensitive_sanctions", "message": "来信或回复涉及制裁、出口管制或禁运，禁止自动发送。", "severity": "critical"},
        {"code": "reply_language_uncertain", "message": "回复语言识别或生成置信度不足。", "severity": "high"},
        {"code": "missing_knowledge_evidence", "message": "缺少可引用知识证据，禁止自动发送。", "severity": "high"},
        {"code": "knowledge_retrieval_uncertain", "message": "知识召回不足或置信度不足。", "severity": "high"},
    ]
    assert decision.to_decision_json()["block_reasons"][0]["code"] == "customer_do_not_contact"


def test_email_reply_hard_block_has_priority_over_auto_send_eligibility() -> None:
    hard_block = EmailReplyHardBlockService.evaluate(
        EmailReplyHardBlockInput(
            customer_do_not_contact=False,
            customer_grade="A",
            customer_status="ready_for_sales",
            inbound_risk_flags=[],
            sensitive_topics=["legal"],
            reply_language_confident=True,
            has_same_language_knowledge=True,
            has_cited_knowledge_evidence=True,
            knowledge_retrieval_confident=True,
            channel_risk_level="Low",
        )
    )
    auto_send = EmailReplyAutoSendEligibilityDecision(
        auto_send_allowed=True,
        route="auto_send_candidate",
        rule_version="phase5-auto-send-eligibility-v1",
        reasons=["whitelisted_customer", "fixed_faq", "first_touch", "low_risk_scene"],
        manual_review_required=False,
    )

    merged = EmailReplyHardBlockService.enforce_priority(hard_block, auto_send)

    assert merged["auto_send_allowed"] is False
    assert merged["route"] == "blocked"
    assert merged["manual_review_required"] is True
    assert merged["hard_block_rule_version"] == EMAIL_REPLY_HARD_BLOCK_RULE_VERSION
    assert merged["auto_send_decision"]["auto_send_allowed"] is True
    assert merged["block_reasons"][0]["code"] == "sensitive_legal"


def test_email_reply_hard_block_routes_watch_invalid_and_high_risk_to_manual_review_or_blocked() -> None:
    for grade in ("Watch", "Invalid"):
        decision = EmailReplyHardBlockService.evaluate(
            EmailReplyHardBlockInput(
                customer_do_not_contact=False,
                customer_grade=grade,
                customer_status="ready_for_sales",
                inbound_risk_flags=[],
                sensitive_topics=[],
                reply_language_confident=True,
                has_same_language_knowledge=True,
                has_cited_knowledge_evidence=True,
                knowledge_retrieval_confident=True,
                channel_risk_level="Low",
            )
        )

        assert decision.hard_blocked is True
        assert decision.route == "blocked"
        assert decision.block_reasons[0]["code"] == "customer_de_grade"

    high_risk = EmailReplyHardBlockService.evaluate(
        EmailReplyHardBlockInput(
            customer_do_not_contact=False,
            customer_grade="B",
            customer_status="ready_for_sales",
            inbound_risk_flags=[],
            sensitive_topics=[],
            reply_language_confident=True,
            has_same_language_knowledge=True,
            has_cited_knowledge_evidence=True,
            knowledge_retrieval_confident=True,
            channel_risk_level="High",
        )
    )

    assert high_risk.hard_blocked is True
    assert high_risk.route == "hold_for_manual_review"
    assert high_risk.block_reasons[0]["code"] == "high_risk_channel"


def test_email_reply_hard_block_applies_structured_reasons_to_draft() -> None:
    draft = EmailReplyDraft(
        ai_suggested_body="Здравствуйте, спасибо за обращение.",
        knowledge_hits_json=[],
        status=EmailReplyDraftStatus.DRAFTED,
    )
    decision = EmailReplyHardBlockService.evaluate(
        EmailReplyHardBlockInput(
            customer_do_not_contact=True,
            customer_grade="B",
            customer_status="do_not_contact",
            inbound_risk_flags=[],
            sensitive_topics=[],
            reply_language_confident=True,
            has_same_language_knowledge=True,
            has_cited_knowledge_evidence=True,
            knowledge_retrieval_confident=True,
            channel_risk_level="Low",
        )
    )

    EmailReplyHardBlockService.apply_to_draft(draft, decision)

    assert draft.auto_send_allowed is False
    assert draft.manual_review_required is True
    assert draft.status == EmailReplyDraftStatus.BLOCKED
    assert draft.manual_review_reason == "命中硬拦截规则，禁止自动发送。"
    assert draft.auto_send_decision_json["hard_block_rule_version"] == EMAIL_REPLY_HARD_BLOCK_RULE_VERSION
    assert draft.auto_send_decision_json["block_reasons"][0]["code"] == "customer_do_not_contact"
