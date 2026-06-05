from app.models.email_reply_draft import EmailReplyDraft
from app.models.enums import EmailReplyDraftStatus
from app.services.email_reply_auto_send import (
    AUTO_SEND_ELIGIBILITY_RULE_VERSION,
    EmailReplyAutoSendEligibilityInput,
    EmailReplyAutoSendEligibilityService,
)


def test_auto_send_eligibility_allows_whitelisted_fixed_faq_first_touch_low_risk() -> None:
    decision = EmailReplyAutoSendEligibilityService.evaluate(
        EmailReplyAutoSendEligibilityInput(
            customer_is_whitelisted=True,
            knowledge_content_type="qa_entry",
            business_scene="fixed_faq",
            scene_risk_level="low",
            is_first_touch=True,
            knowledge_auto_reply_allowed=True,
            knowledge_embedding_ready=True,
            reply_language_confident=True,
        )
    )

    assert decision.auto_send_allowed is True
    assert decision.route == "auto_send_candidate"
    assert decision.manual_review_required is False
    assert decision.rule_version == AUTO_SEND_ELIGIBILITY_RULE_VERSION
    assert decision.reasons == [
        "whitelisted_customer",
        "fixed_faq",
        "first_touch",
        "low_risk_scene",
        "knowledge_auto_reply_allowed",
        "knowledge_embedding_ready",
        "reply_language_confident",
    ]
    assert decision.to_decision_json()["rule_version"] == AUTO_SEND_ELIGIBILITY_RULE_VERSION


def test_auto_send_eligibility_routes_unqualified_context_to_manual_review_without_error() -> None:
    decision = EmailReplyAutoSendEligibilityService.evaluate(
        EmailReplyAutoSendEligibilityInput(
            customer_is_whitelisted=False,
            knowledge_content_type="qa_entry",
            business_scene="fixed_faq",
            scene_risk_level="low",
            is_first_touch=False,
            knowledge_auto_reply_allowed=True,
            knowledge_embedding_ready=True,
            reply_language_confident=True,
        )
    )

    assert decision.auto_send_allowed is False
    assert decision.route == "hold_for_manual_review"
    assert decision.manual_review_required is True
    assert decision.manual_review_reason == "未满足自动发送准入条件，进入人工确认。"
    assert decision.rule_version == AUTO_SEND_ELIGIBILITY_RULE_VERSION
    assert "not_whitelisted_customer" in decision.reasons
    assert "not_first_touch" in decision.reasons


def test_auto_send_eligibility_blocks_medium_or_high_risk_from_auto_send() -> None:
    for risk_level in ("medium", "high", "blocked", "Forbidden"):
        decision = EmailReplyAutoSendEligibilityService.evaluate(
            EmailReplyAutoSendEligibilityInput(
                customer_is_whitelisted=True,
                knowledge_content_type="qa_entry",
                business_scene="fixed_faq",
                scene_risk_level=risk_level,
                is_first_touch=True,
                knowledge_auto_reply_allowed=True,
                knowledge_embedding_ready=True,
                reply_language_confident=True,
            )
        )

        assert decision.auto_send_allowed is False
        assert decision.manual_review_required is True
        assert decision.route == "hold_for_manual_review"
        assert "not_low_risk_scene" in decision.reasons


def test_auto_send_eligibility_applies_decision_to_email_reply_draft() -> None:
    draft = EmailReplyDraft(
        ai_suggested_body="Здравствуйте, спасибо за обращение.",
        knowledge_hits_json=[],
        status=EmailReplyDraftStatus.DRAFTED,
    )
    decision = EmailReplyAutoSendEligibilityService.evaluate(
        EmailReplyAutoSendEligibilityInput(
            customer_is_whitelisted=True,
            knowledge_content_type="qa_entry",
            business_scene="fixed_faq",
            scene_risk_level="low",
            is_first_touch=True,
            knowledge_auto_reply_allowed=True,
            knowledge_embedding_ready=True,
            reply_language_confident=True,
        )
    )

    EmailReplyAutoSendEligibilityService.apply_to_draft(draft, decision)

    assert draft.auto_send_allowed is True
    assert draft.manual_review_required is False
    assert draft.manual_review_reason is None
    assert draft.auto_send_decision_json["rule_version"] == AUTO_SEND_ELIGIBILITY_RULE_VERSION
    assert draft.auto_send_decision_json["reasons"] == decision.reasons
    assert draft.status == EmailReplyDraftStatus.DRAFTED
