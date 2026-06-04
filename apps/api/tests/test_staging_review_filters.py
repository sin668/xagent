from pathlib import Path

from app.models.enums import ChannelRiskLevel, CustomerGrade, StagingReviewStatus
from app.services.staging_leads import StagingLeadService


API_ROOT = Path(__file__).resolve().parents[1]


def test_staging_lead_filter_api_contract_exists() -> None:
    api_text = (API_ROOT / "app" / "api" / "staging_leads.py").read_text(encoding="utf-8")

    for query_name in [
        "review_status",
        "recommended_grade",
        "queue_status",
        "source_risk_level",
        "has_contact",
        "requires_secondary_verification",
    ]:
        assert query_name in api_text


def test_staging_lead_response_includes_review_list_fields() -> None:
    schema_text = (API_ROOT / "app" / "schemas" / "staging_leads.py").read_text(encoding="utf-8")

    for field in [
        "source_url",
        "source_risk_level",
        "has_contact",
        "evidence_status",
        "risk_markers",
        "requires_secondary_verification",
    ]:
        assert field in schema_text


def test_has_contact_detects_non_empty_contact_value() -> None:
    assert StagingLeadService.has_contact([{"type": "email", "value": "dealer@example.com"}]) is True
    assert StagingLeadService.has_contact([{"type": "email", "value": ""}]) is False
    assert StagingLeadService.has_contact([]) is False


def test_evidence_status_requires_source_evidence() -> None:
    assert StagingLeadService.evidence_status("官网公开邮箱") == "present"
    assert StagingLeadService.evidence_status("") == "missing"
    assert StagingLeadService.evidence_status(None) == "missing"


def test_risk_markers_include_high_watch_invalid_and_missing_contact() -> None:
    markers = StagingLeadService.risk_markers(
        source_risk_level=ChannelRiskLevel.HIGH,
        recommended_grade=CustomerGrade.WATCH,
        review_status=StagingReviewStatus.NEEDS_SECONDARY_VERIFICATION,
        has_contact=False,
        has_evidence=False,
    )

    assert "High 二次复核" in markers
    assert "Watch 不进入触达" in markers
    assert "缺联系方式" in markers
    assert "缺来源证据" in markers


def test_filter_summary_presets_match_mobile_review_tabs() -> None:
    presets = StagingLeadService.review_filter_presets()

    assert presets["pending_review"]["review_status"] == "pending_review"
    assert presets["bc"]["recommended_grade"] == ["B", "C"]
    assert presets["high_secondary"]["source_risk_level"] == "High"
    assert presets["high_secondary"]["requires_secondary_verification"] is True
    assert presets["missing_contact"]["has_contact"] is False
    assert presets["watch_invalid"]["recommended_grade"] == ["Watch", "Invalid"]
