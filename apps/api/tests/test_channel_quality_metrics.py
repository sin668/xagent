from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from app.models.enums import ChannelRiskLevel, CustomerGrade, RiskEventSeverity, StagingReviewStatus, SourcePlatform
from app.services.dashboard import DashboardService


API_ROOT = Path(__file__).resolve().parents[1]


def item(**kwargs):
    return SimpleNamespace(**kwargs)


def dt(value: str) -> datetime:
    return datetime.fromisoformat(value)


def candidate(platform, risk, *, requires_secondary=False, queue_eligible=True):
    return item(
        id=uuid4(),
        created_at=dt("2026-05-29T08:00:00"),
        source_platform=platform,
        source_risk_level=risk,
        requires_secondary_verification=requires_secondary,
        queue_eligible=queue_eligible,
    )


def staging(candidate_url, grade, *, contacts=True, evidence=True, review_status=StagingReviewStatus.PENDING_REVIEW, dedupe_key=None):
    return item(
        id=uuid4(),
        created_at=dt("2026-05-29T10:00:00"),
        candidate_url=candidate_url,
        recommended_grade=grade,
        contacts_json=[{"method_type": "email", "value": "sales@example.ru"}] if contacts else [],
        source_evidence="公开证据" if evidence else "",
        review_status=review_status,
        dedupe_key=dedupe_key or str(uuid4()),
    )


def test_channel_quality_metrics_cover_rates_duplicates_and_risk_events() -> None:
    low_candidate = candidate(SourcePlatform.OFFICIAL_WEBSITE, ChannelRiskLevel.LOW)
    high_candidate_pending = candidate(SourcePlatform.YOUTUBE, ChannelRiskLevel.HIGH, requires_secondary=True, queue_eligible=False)
    high_candidate_passed = candidate(SourcePlatform.YOUTUBE, ChannelRiskLevel.HIGH, requires_secondary=True, queue_eligible=False)

    staging_leads = [
        staging(low_candidate, CustomerGrade.B, dedupe_key="same-key"),
        staging(low_candidate, CustomerGrade.C, evidence=False, dedupe_key="same-key"),
        staging(low_candidate, CustomerGrade.INVALID, contacts=False),
        staging(high_candidate_pending, CustomerGrade.WATCH, review_status=StagingReviewStatus.NEEDS_SECONDARY_VERIFICATION),
        staging(high_candidate_passed, CustomerGrade.B, review_status=StagingReviewStatus.APPROVED),
    ]
    core_sources = [
        (
            item(id=uuid4(), grade=CustomerGrade.B, do_not_contact=False, created_at=dt("2026-05-29T12:00:00")),
            item(platform=SourcePlatform.OFFICIAL_WEBSITE, channel_risk_level=ChannelRiskLevel.LOW, collected_at=dt("2026-05-29T12:00:00")),
        )
    ]
    risk_events = [
        item(
            channel=SourcePlatform.OFFICIAL_WEBSITE.value,
            risk_level=ChannelRiskLevel.LOW,
            severity=RiskEventSeverity.MEDIUM,
            pause_suggested=True,
            created_at=dt("2026-05-29T13:00:00"),
        )
    ]

    dashboard = DashboardService.channel_quality_from_records(
        candidates=[low_candidate, high_candidate_pending, high_candidate_passed],
        staging_leads=staging_leads,
        core_sources=core_sources,
        risk_events=risk_events,
    )
    official = next(item for item in dashboard["channels"] if item["channel_name"] == "official_website")
    youtube = next(item for item in dashboard["channels"] if item["channel_name"] == "youtube")

    assert official["risk_category"] == "Low"
    assert official["staging_lead_count"] == 3
    assert official["bc_grade_count"] == 2
    assert official["bc_rate"] == 2 / 3
    assert official["invalid_watch_count"] == 1
    assert official["contact_completeness_rate"] == 2 / 3
    assert official["evidence_completeness_rate"] == 2 / 3
    assert official["duplicate_count"] == 1
    assert official["duplicate_rate"] == 1 / 3
    assert official["risk_event_count"] == 1
    assert official["pause_suggested_count"] == 1

    assert youtube["risk_category"] == "High"
    assert youtube["high_secondary_review_required_count"] == 2
    assert youtube["high_secondary_review_passed_count"] == 1
    assert youtube["high_secondary_review_pass_rate"] == 0.5
    assert youtube["quality_conclusion"] == "policy_research"


def test_channel_quality_api_contract_exists() -> None:
    api_file = API_ROOT / "app" / "api" / "dashboard.py"
    schemas_file = API_ROOT / "app" / "schemas" / "dashboard.py"

    assert '@router.get("/channel-quality"' in api_file.read_text(encoding="utf-8")
    assert "ChannelQualityDashboardResponse" in schemas_file.read_text(encoding="utf-8")
