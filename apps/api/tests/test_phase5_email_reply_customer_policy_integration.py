from app.models.customer import Customer
from app.models.email_reply_draft import EmailReplyDraft
from app.models.enums import CustomerGrade, CustomerStatus, CustomerType, EmailReplyDraftStatus
from app.services.email_reply_customer_policy import EmailReplyCustomerPolicyService
from app.services.email_reply_hard_block import EMAIL_REPLY_HARD_BLOCK_RULE_VERSION


def _customer(
    *,
    grade: CustomerGrade = CustomerGrade.B,
    status: CustomerStatus = CustomerStatus.READY_FOR_SALES,
    do_not_contact: bool = False,
) -> Customer:
    return Customer(
        name="Policy Test Dealer",
        country="Russia",
        city="Moscow",
        customer_type=CustomerType.LOCAL_DEALER_SECONDARY_DEALER,
        grade=grade,
        status=status,
        do_not_contact=do_not_contact,
        do_not_contact_reason="客户明确要求停止联系" if do_not_contact else None,
    )


def test_customer_policy_builds_dnc_hard_block_input_from_customer_state() -> None:
    customer = _customer(status=CustomerStatus.DO_NOT_CONTACT, do_not_contact=True)

    decision = EmailReplyCustomerPolicyService.evaluate_customer_policy(
        customer,
        reply_language_confident=True,
        has_same_language_knowledge=True,
        has_cited_knowledge_evidence=True,
        knowledge_retrieval_confident=True,
        channel_risk_level="Low",
    )

    assert decision.hard_blocked is True
    assert decision.route == "blocked"
    assert decision.block_reasons[0] == {
        "code": "customer_do_not_contact",
        "message": "客户已标记勿扰或 DNC。",
        "severity": "critical",
    }


def test_customer_policy_maps_watch_and_invalid_to_external_de_grade_block_reasons() -> None:
    watch = EmailReplyCustomerPolicyService.evaluate_customer_policy(
        _customer(grade=CustomerGrade.WATCH, status=CustomerStatus.WATCH),
        reply_language_confident=True,
        has_same_language_knowledge=True,
        has_cited_knowledge_evidence=True,
        knowledge_retrieval_confident=True,
        channel_risk_level="Low",
    )
    invalid = EmailReplyCustomerPolicyService.evaluate_customer_policy(
        _customer(grade=CustomerGrade.INVALID, status=CustomerStatus.INVALID),
        reply_language_confident=True,
        has_same_language_knowledge=True,
        has_cited_knowledge_evidence=True,
        knowledge_retrieval_confident=True,
        channel_risk_level="Low",
    )

    assert watch.block_reasons[0]["code"] == "customer_de_grade"
    assert invalid.block_reasons[0]["code"] == "customer_de_grade"
    assert EmailReplyCustomerPolicyService.external_grade_label(CustomerGrade.WATCH) == "D"
    assert EmailReplyCustomerPolicyService.external_grade_label(CustomerGrade.INVALID) == "E"


def test_customer_policy_applies_block_reasons_to_draft_for_manual_review_page() -> None:
    customer = _customer(status=CustomerStatus.DO_NOT_CONTACT, do_not_contact=True)
    draft = EmailReplyDraft(
        ai_suggested_body="Здравствуйте, спасибо за обращение.",
        knowledge_hits_json=[],
        status=EmailReplyDraftStatus.DRAFTED,
    )

    decision = EmailReplyCustomerPolicyService.apply_customer_policy_to_draft(
        draft,
        customer,
        reply_language_confident=True,
        has_same_language_knowledge=True,
        has_cited_knowledge_evidence=True,
        knowledge_retrieval_confident=True,
        channel_risk_level="Low",
    )

    assert decision.hard_blocked is True
    assert draft.auto_send_allowed is False
    assert draft.manual_review_required is True
    assert draft.status == EmailReplyDraftStatus.BLOCKED
    assert draft.manual_review_reason == "命中 DNC/勿扰或 D/E 客户阻断规则，禁止自动发送。"
    assert draft.auto_send_decision_json["hard_block_rule_version"] == EMAIL_REPLY_HARD_BLOCK_RULE_VERSION
    assert draft.auto_send_decision_json["customer_policy"]["do_not_contact"] is True
    assert draft.auto_send_decision_json["customer_policy"]["external_grade_label"] == "B"
    assert draft.auto_send_decision_json["block_reasons"][0]["code"] == "customer_do_not_contact"
