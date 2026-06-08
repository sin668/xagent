from types import SimpleNamespace
from uuid import uuid4

from pydantic import ValidationError

from app.models.enums import ChannelRiskLevel, CustomerGrade, CustomerType, StagingQueueStatus, StagingReviewStatus
from app.schemas.customer_promotion import CustomerPromotionEligibilityResponse
from app.services.customer_promotion import CustomerPromotionEligibilityService


def build_lead(**overrides):
    candidate = overrides.pop(
        "candidate_url",
        SimpleNamespace(
            id=uuid4(),
            url="https://dealer.example.ru",
            source_risk_level=ChannelRiskLevel.LOW,
        ),
    )
    payload = {
        "id": uuid4(),
        "candidate_url": candidate,
        "customer_name": "Auto City Moscow",
        "country": "Russia",
        "city": "Moscow",
        "customer_type": CustomerType.UNKNOWN,
        "contacts_json": [{"type": "email", "value": "sales@dealer.example.ru"}],
        "activity_level": None,
        "scale_signal": None,
        "import_used_car_relevance": None,
        "source_evidence": "官网公开展示车辆销售和邮箱。",
        "recommended_grade": CustomerGrade.B,
        "review_status": StagingReviewStatus.PENDING_REVIEW,
        "queue_status": StagingQueueStatus.PENDING_REVIEW,
        "requires_compliance_review": False,
    }
    payload.update(overrides)
    return SimpleNamespace(**payload)


def test_eligibility_response_schema_preserves_pending_optional_fields() -> None:
    response = CustomerPromotionEligibilityResponse(
        staging_lead_id=uuid4(),
        can_promote=True,
        status="ready",
        reasons=["满足平衡准入"],
        missing_required_fields=[],
        pending_optional_fields=["customer_type", "scale_signal", "vehicle_intents"],
        requires_compliance_review=False,
        source_url="https://dealer.example.ru",
    )

    assert response.can_promote is True
    assert response.pending_optional_fields == ["customer_type", "scale_signal", "vehicle_intents"]


def test_eligibility_response_requires_status_and_reason_lists() -> None:
    try:
        CustomerPromotionEligibilityResponse(
            staging_lead_id=uuid4(),
            can_promote=True,
            status="ready",
        )
    except ValidationError as exc:
        assert "reasons" in str(exc)
        assert "missing_required_fields" in str(exc)
        assert "pending_optional_fields" in str(exc)
    else:
        raise AssertionError("eligibility response should require explicit reason lists")


def test_balanced_eligibility_allows_missing_optional_fields_as_pending_supplement() -> None:
    lead = build_lead(customer_type=CustomerType.UNKNOWN, scale_signal=None, import_used_car_relevance=None)

    result = CustomerPromotionEligibilityService.evaluate(lead, has_do_not_contact_match=False)

    assert result.can_promote is True
    assert result.status == "ready"
    assert result.missing_required_fields == []
    assert "满足平衡准入" in result.reasons
    assert "customer_type" in result.pending_optional_fields
    assert "scale_signal" in result.pending_optional_fields
    assert "vehicle_intents" in result.pending_optional_fields
    assert result.requires_compliance_review is False


def test_eligibility_blocks_missing_required_name_country_city_contact_and_evidence() -> None:
    lead = build_lead(
        customer_name="Unknown",
        country="Unknown",
        city=None,
        contacts_json=[],
        source_evidence="",
        candidate_url=SimpleNamespace(id=uuid4(), url="", source_risk_level=ChannelRiskLevel.LOW),
    )

    result = CustomerPromotionEligibilityService.evaluate(lead, has_do_not_contact_match=False)

    assert result.can_promote is False
    assert result.status == "blocked"
    assert result.missing_required_fields == ["customer_name", "country_or_city", "contact_method", "source_url", "source_evidence"]
    assert "缺少客户名称" in result.reasons
    assert "缺少国家/城市" in result.reasons
    assert "缺少至少一个联系方式" in result.reasons
    assert "缺少来源链接" in result.reasons
    assert "缺少来源证据" in result.reasons


def test_eligibility_blocks_forbidden_high_unreviewed_watch_invalid_and_dnc() -> None:
    forbidden = CustomerPromotionEligibilityService.evaluate(
        build_lead(candidate_url=SimpleNamespace(id=uuid4(), url="https://blocked.example", source_risk_level=ChannelRiskLevel.FORBIDDEN)),
        has_do_not_contact_match=False,
    )
    high_unreviewed = CustomerPromotionEligibilityService.evaluate(
        build_lead(
            candidate_url=SimpleNamespace(id=uuid4(), url="https://high.example", source_risk_level=ChannelRiskLevel.HIGH),
            review_status=StagingReviewStatus.NEEDS_SECONDARY_VERIFICATION,
        ),
        has_do_not_contact_match=False,
    )
    watch = CustomerPromotionEligibilityService.evaluate(
        build_lead(recommended_grade=CustomerGrade.WATCH, queue_status=StagingQueueStatus.NOT_ELIGIBLE),
        has_do_not_contact_match=False,
    )
    invalid = CustomerPromotionEligibilityService.evaluate(
        build_lead(recommended_grade=CustomerGrade.INVALID, queue_status=StagingQueueStatus.NOT_ELIGIBLE),
        has_do_not_contact_match=False,
    )
    dnc = CustomerPromotionEligibilityService.evaluate(build_lead(), has_do_not_contact_match=True)

    assert forbidden.can_promote is False
    assert "Forbidden 来源不得作为客户晋级关键来源" in forbidden.reasons
    assert high_unreviewed.can_promote is False
    assert "High 来源未完成二次复核" in high_unreviewed.reasons
    assert watch.can_promote is False
    assert "Watch 不得晋级客户或进入触达队列" in watch.reasons
    assert invalid.can_promote is False
    assert "Invalid 不得晋级客户或进入触达队列" in invalid.reasons
    assert dnc.can_promote is False
    assert "命中勿扰客户" in dnc.reasons


def test_c_grade_eligibility_requires_compliance_review_flag_but_can_pass_minimum_gate() -> None:
    lead = build_lead(recommended_grade=CustomerGrade.C, requires_compliance_review=True)

    result = CustomerPromotionEligibilityService.evaluate(lead, has_do_not_contact_match=False)

    assert result.can_promote is True
    assert result.requires_compliance_review is True
    assert "C 级客户报价/合同前必须合规复核" in result.reasons
