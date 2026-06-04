from pathlib import Path

from app.models.enums import ChannelRiskLevel, CustomerGrade, StagingQueueStatus, StagingReviewStatus
from app.services.llm_lead_grading import LLMLeadGradingService


API_ROOT = Path(__file__).resolve().parents[1]


def grading_output(**overrides):
    payload = {
        "schema_version": "poc-ai-output-v1",
        "task_type": "lead_grading",
        "lead_id": "staging-1",
        "recommended_grade": "B",
        "recommended_reason": "客户有公开联系方式和二手车库存信号，证据：автомобили с пробегом。",
        "reason_codes": ["has_public_contact", "used_car_signal"],
        "evidence_refs": [
            {
                "claim": "used_car_signal",
                "evidence_text": "автомобили с пробегом",
                "source_url": "https://dealer.example/contact",
            }
        ],
        "missing_fields": ["是否有进口车经验"],
        "next_action": "handoff_to_customer_service",
        "suggested_handoff_team": "customer_service",
        "touch_queue_allowed": True,
        "touch_channel_limit": "manual_only_low_medium_risk",
        "compliance_review_required": False,
        "human_review_required": True,
        "risk_flags": [],
        "audit": {
            "model": "test-model",
            "prompt_version": "lead-grading-v1",
            "input_saved": True,
            "output_saved": True,
            "executed_at": "2026-05-29T10:10:00+08:00",
        },
    }
    payload.update(overrides)
    return payload


def test_invalid_and_watch_are_forced_not_eligible() -> None:
    for grade in (CustomerGrade.INVALID, CustomerGrade.WATCH):
        result = LLMLeadGradingService.apply_hard_rules(
            grading_output(recommended_grade=grade.value, touch_queue_allowed=True),
            source_risk_level=ChannelRiskLevel.MEDIUM,
            review_status=StagingReviewStatus.PENDING_REVIEW,
            has_evidence=True,
            has_contact=True,
            do_not_contact=False,
        )

        assert result.recommended_grade == grade
        assert result.queue_status == StagingQueueStatus.NOT_ELIGIBLE
        assert result.touch_queue_allowed is False


def test_high_unverified_lead_is_blocked_even_if_llm_recommends_b() -> None:
    result = LLMLeadGradingService.apply_hard_rules(
        grading_output(recommended_grade="B", touch_queue_allowed=True),
        source_risk_level=ChannelRiskLevel.HIGH,
        review_status=StagingReviewStatus.NEEDS_SECONDARY_VERIFICATION,
        has_evidence=True,
        has_contact=True,
        do_not_contact=False,
    )

    assert result.recommended_grade == CustomerGrade.B
    assert result.queue_status == StagingQueueStatus.BLOCKED
    assert result.touch_queue_allowed is False
    assert "high_unverified_blocked" in result.risk_flags


def test_c_grade_requires_compliance_review_and_flag_even_if_llm_omits_it() -> None:
    result = LLMLeadGradingService.apply_hard_rules(
        grading_output(
            recommended_grade="C",
            next_action="handoff_to_export_sales",
            suggested_handoff_team="export_sales",
            compliance_review_required=False,
            risk_flags=[],
        ),
        source_risk_level=ChannelRiskLevel.MEDIUM,
        review_status=StagingReviewStatus.PENDING_REVIEW,
        has_evidence=True,
        has_contact=True,
        do_not_contact=False,
    )

    assert result.recommended_grade == CustomerGrade.C
    assert result.requires_compliance_review is True
    assert result.queue_status == StagingQueueStatus.ELIGIBLE
    assert "c_grade_requires_compliance_review" in result.risk_flags


def test_recommended_reason_must_reference_evidence() -> None:
    output = grading_output(evidence_refs=[])

    try:
        LLMLeadGradingService.validate_grading_output(
            output,
            expected_source_url="https://dealer.example/contact",
        )
    except ValueError as exc:
        assert "推荐原因必须引用证据" in str(exc)
    else:
        raise AssertionError("Grading output without evidence refs should be rejected")


def test_equivalent_evidence_ref_source_url_normalization_is_accepted_and_canonicalized() -> None:
    output = grading_output()
    output["evidence_refs"][0]["source_url"] = "HTTPS://DEALER.EXAMPLE/contact/"

    normalized = LLMLeadGradingService.validate_grading_output(
        output,
        expected_source_url="https://dealer.example/contact",
    )

    assert normalized["evidence_refs"][0]["source_url"] == "https://dealer.example/contact"


def test_unknown_grade_and_next_action_are_safely_normalized_when_contact_exists() -> None:
    output = grading_output(
        recommended_grade="Interested Dealer",
        next_action="call dealer tomorrow",
        suggested_handoff_team="sales team",
        touch_queue_allowed=True,
    )

    normalized = LLMLeadGradingService.validate_grading_output(
        output,
        expected_source_url="https://dealer.example/contact",
        has_contact=True,
    )
    result = LLMLeadGradingService.apply_hard_rules(
        normalized,
        source_risk_level=ChannelRiskLevel.MEDIUM,
        review_status=StagingReviewStatus.PENDING_REVIEW,
        has_evidence=True,
        has_contact=True,
        do_not_contact=False,
    )

    assert normalized["recommended_grade"] == CustomerGrade.B.value
    assert normalized["next_action"] == "handoff_to_customer_service"
    assert normalized["suggested_handoff_team"] == "customer_service"
    assert normalized["audit"]["llm_reported_recommended_grade"] == "Interested Dealer"
    assert normalized["audit"]["recommended_grade_canonicalized"] is True
    assert normalized["audit"]["llm_reported_next_action"] == "call dealer tomorrow"
    assert normalized["audit"]["next_action_canonicalized"] is True
    assert normalized["audit"]["llm_reported_suggested_handoff_team"] == "sales team"
    assert normalized["audit"]["suggested_handoff_team_canonicalized"] is True
    assert result.recommended_grade == CustomerGrade.B


def test_unknown_grade_and_next_action_fall_back_to_watch_when_contact_is_missing() -> None:
    output = grading_output(
        recommended_grade="Interested Dealer",
        next_action="call dealer tomorrow",
        suggested_handoff_team="sales team",
        touch_queue_allowed=True,
    )

    normalized = LLMLeadGradingService.validate_grading_output(
        output,
        expected_source_url="https://dealer.example/contact",
        has_contact=False,
    )

    assert normalized["recommended_grade"] == CustomerGrade.WATCH.value
    assert normalized["next_action"] == "watch_later"
    assert normalized["suggested_handoff_team"] == "lead_ops"


def test_do_not_contact_overrides_llm_touch_recommendation() -> None:
    result = LLMLeadGradingService.apply_hard_rules(
        grading_output(recommended_grade="B", touch_queue_allowed=True),
        source_risk_level=ChannelRiskLevel.MEDIUM,
        review_status=StagingReviewStatus.PENDING_REVIEW,
        has_evidence=True,
        has_contact=True,
        do_not_contact=True,
    )

    assert result.queue_status == StagingQueueStatus.NOT_ELIGIBLE
    assert result.touch_queue_allowed is False
    assert "do_not_contact_blocked" in result.risk_flags


def test_llm_lead_grading_api_contract_is_registered() -> None:
    main_py = (API_ROOT / "app" / "main.py").read_text(encoding="utf-8")
    api_file = API_ROOT / "app" / "api" / "llm_lead_grading.py"

    assert api_file.exists()
    assert "llm_lead_grading_router" in main_py
    assert '@router.post("/run"' in api_file.read_text(encoding="utf-8")
