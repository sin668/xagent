from uuid import uuid4

from app.models.customer import Customer
from app.models.email_message import EmailMessage
from app.models.email_reply_draft import EmailReplyDraft
from app.models.enums import CustomerGrade, CustomerStatus, EmailMessageDirection, EmailReplyDraftStatus
from app.services.email_send_preview import EmailSendPreviewService


def _message(from_email: str = "buyer@example.ru") -> EmailMessage:
    return EmailMessage(
        id=uuid4(),
        thread_id=uuid4(),
        direction=EmailMessageDirection.INBOUND,
        from_email=from_email,
        to_emails=["sales@example.com"],
        cc_emails=[],
        subject="Toyota Land Cruiser inquiry",
        body_text="Please send details.",
    )


def _customer(
    *,
    grade: CustomerGrade = CustomerGrade.B,
    status: CustomerStatus = CustomerStatus.READY_FOR_SALES,
    do_not_contact: bool = False,
) -> Customer:
    return Customer(
        id=uuid4(),
        external_id=f"preview-{uuid4()}",
        name="Rus Auto Buyer",
        country="Russia",
        city="Moscow",
        grade=grade,
        status=status,
        do_not_contact=do_not_contact,
    )


def _draft(
    *,
    customer: Customer | None = None,
    knowledge_hits: list[dict] | None = None,
    auto_send_allowed: bool = True,
    manual_review_required: bool = False,
    auto_send_decision_json: dict | None = None,
) -> EmailReplyDraft:
    draft = EmailReplyDraft(
        id=uuid4(),
        thread_id=uuid4(),
        message_id=uuid4(),
        customer_id=getattr(customer, "id", None),
        detected_language="ru",
        reply_language="ru",
        language_confidence=0.94,
        ai_suggested_subject="Re: Toyota Land Cruiser inquiry",
        ai_suggested_body="Здравствуйте, можем подготовить подборку автомобилей.",
        final_subject="Re: Toyota Land Cruiser inquiry",
        final_body="Здравствуйте, можем подготовить подборку автомобилей и условия следующего шага.",
        knowledge_hits_json=knowledge_hits
        if knowledge_hits is not None
        else [
            {
                "knowledge_item_id": str(uuid4()),
                "title": "固定 FAQ：首封回复",
                "similarity_score": 0.91,
                "auto_reply_allowed": True,
            }
        ],
        auto_send_allowed=auto_send_allowed,
        auto_send_decision_json=auto_send_decision_json
        if auto_send_decision_json is not None
        else {
            "route": "auto_send_candidate",
            "auto_send_allowed": auto_send_allowed,
            "manual_review_required": manual_review_required,
            "reasons": ["whitelisted_customer", "fixed_faq", "low_risk_scene"],
        },
        manual_review_required=manual_review_required,
        manual_review_reason="需要人工确认。" if manual_review_required else None,
        status=EmailReplyDraftStatus.DRAFTED,
    )
    draft.message = _message()
    draft.customer = customer or _customer()
    return draft


def test_email_send_preview_allows_auto_send_candidate_without_sending() -> None:
    preview = EmailSendPreviewService.build_preview(
        _draft(),
        sender_from_email="sales@example.com",
        recent_send_count=0,
        frequency_limit=3,
    )

    assert preview["decision"] == "auto_send_allowed"
    assert preview["allow_auto_send"] is True
    assert preview["send_triggered"] is False
    assert preview["from_email"] == "sales@example.com"
    assert preview["to_emails"] == ["buyer@example.ru"]
    assert preview["subject"] == "Re: Toyota Land Cruiser inquiry"
    assert "условия следующего шага" in preview["body_text"]
    assert preview["knowledge_hit_count"] == 1
    assert preview["hard_blocks"] == []
    assert preview["manual_review_required"] is False
    assert preview["manual_review_reason"] is None


def test_email_send_preview_blocks_dnc_watch_and_invalid_customers() -> None:
    cases = [
        (_customer(do_not_contact=True), "customer_do_not_contact"),
        (_customer(grade=CustomerGrade.WATCH, status=CustomerStatus.WATCH), "customer_de_grade"),
        (_customer(grade=CustomerGrade.INVALID, status=CustomerStatus.INVALID), "customer_de_grade"),
    ]

    for customer, expected_block in cases:
        preview = EmailSendPreviewService.build_preview(_draft(customer=customer), sender_from_email="sales@example.com")

        assert preview["decision"] == "blocked"
        assert preview["allow_auto_send"] is False
        assert preview["send_triggered"] is False
        assert expected_block in preview["hard_blocks"]
        assert preview["manual_review_required"] is True


def test_email_send_preview_routes_missing_knowledge_and_frequency_limit_to_manual_review() -> None:
    missing_knowledge = EmailSendPreviewService.build_preview(
        _draft(knowledge_hits=[]),
        sender_from_email="sales@example.com",
    )
    rate_limited = EmailSendPreviewService.build_preview(
        _draft(),
        sender_from_email="sales@example.com",
        recent_send_count=3,
        frequency_limit=3,
    )

    assert missing_knowledge["decision"] == "manual_review"
    assert missing_knowledge["allow_auto_send"] is False
    assert missing_knowledge["manual_review_required"] is True
    assert "missing_knowledge_evidence" in missing_knowledge["reasons"]

    assert rate_limited["decision"] == "manual_review"
    assert rate_limited["allow_auto_send"] is False
    assert rate_limited["manual_review_required"] is True
    assert "frequency_limit_reached" in rate_limited["reasons"]


def test_email_send_preview_hard_block_decision_has_priority_over_auto_send() -> None:
    preview = EmailSendPreviewService.build_preview(
        _draft(
            auto_send_allowed=True,
            manual_review_required=False,
            auto_send_decision_json={
                "route": "blocked",
                "hard_blocked": True,
                "auto_send_allowed": False,
                "manual_review_required": True,
                "block_reasons": [
                    {"code": "sensitive_legal", "message": "涉及法律合规，禁止自动发送。", "severity": "high"}
                ],
            },
        ),
        sender_from_email="sales@example.com",
    )

    assert preview["decision"] == "blocked"
    assert preview["allow_auto_send"] is False
    assert preview["send_triggered"] is False
    assert preview["hard_blocks"] == ["sensitive_legal"]
    assert preview["manual_review_required"] is True
