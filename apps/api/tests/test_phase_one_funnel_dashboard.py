from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from app.models.enums import ChannelRiskLevel, CustomerGrade, SourcePlatform
from app.services.dashboard import DashboardService


API_ROOT = Path(__file__).resolve().parents[1]


def item(**kwargs):
    return SimpleNamespace(**kwargs)


def dt(value: str) -> datetime:
    return datetime.fromisoformat(value)


def test_phase_one_funnel_counts_daily_target_core_and_touchable_effective_leads() -> None:
    candidates = [
        item(
            id=uuid4(),
            created_at=dt("2026-05-29T08:00:00"),
            source_platform=SourcePlatform.OFFICIAL_WEBSITE,
            source_risk_level=ChannelRiskLevel.LOW,
        )
        for _ in range(100)
    ]
    high_candidate = item(
        id=uuid4(),
        created_at=dt("2026-05-29T09:00:00"),
        source_platform=SourcePlatform.YOUTUBE,
        source_risk_level=ChannelRiskLevel.HIGH,
    )
    candidates.append(high_candidate)

    low_candidate = candidates[0]
    staging_leads = [
        item(id=uuid4(), created_at=dt("2026-05-29T10:00:00"), candidate_url=low_candidate),
        item(id=uuid4(), created_at=dt("2026-05-29T11:00:00"), candidate_url=high_candidate),
    ]

    customer_b = item(id=uuid4(), grade=CustomerGrade.B, do_not_contact=False, created_at=dt("2026-05-29T12:00:00"))
    customer_c = item(id=uuid4(), grade=CustomerGrade.C, do_not_contact=False, created_at=dt("2026-05-29T13:00:00"))
    customer_high = item(id=uuid4(), grade=CustomerGrade.B, do_not_contact=False, created_at=dt("2026-05-29T14:00:00"))
    customer_dnc = item(id=uuid4(), grade=CustomerGrade.C, do_not_contact=True, created_at=dt("2026-05-29T15:00:00"))
    core_sources = [
        (
            customer_b,
            item(platform=SourcePlatform.OFFICIAL_WEBSITE, channel_risk_level=ChannelRiskLevel.LOW, collected_at=dt("2026-05-29T12:00:00")),
        ),
        (
            customer_c,
            item(platform=SourcePlatform.OFFICIAL_WEBSITE, channel_risk_level=ChannelRiskLevel.LOW, collected_at=dt("2026-05-29T13:00:00")),
        ),
        (
            customer_high,
            item(platform=SourcePlatform.YOUTUBE, channel_risk_level=ChannelRiskLevel.HIGH, collected_at=dt("2026-05-29T14:00:00")),
        ),
        (
            customer_dnc,
            item(platform=SourcePlatform.OFFICIAL_WEBSITE, channel_risk_level=ChannelRiskLevel.LOW, collected_at=dt("2026-05-29T15:00:00")),
        ),
    ]

    dashboard = DashboardService.phase_one_funnel_from_records(
        candidates=candidates,
        staging_leads=staging_leads,
        core_sources=core_sources,
        date_from="2026-05-29",
        date_to="2026-05-29",
        daily_candidate_target=100,
    )

    assert dashboard["summary"]["candidate_url_count"] == 101
    assert dashboard["summary"]["candidate_target_completion_rate"] == 1.01
    assert dashboard["summary"]["staging_lead_count"] == 2
    assert dashboard["summary"]["core_customer_count"] == 4
    assert dashboard["summary"]["core_valid_lead_count"] == 4
    assert dashboard["summary"]["touchable_effective_lead_count"] == 2
    assert dashboard["summary"]["high_readonly_excluded_count"] == 1
    assert dashboard["summary"]["do_not_contact_excluded_count"] == 1
    assert dashboard["daily"][0]["date"] == "2026-05-29"
    assert dashboard["daily"][0]["candidate_target_met"] is True


def test_phase_one_funnel_supports_channel_and_risk_filters() -> None:
    candidates = [
        item(id=uuid4(), created_at=dt("2026-05-29T08:00:00"), source_platform=SourcePlatform.OFFICIAL_WEBSITE, source_risk_level=ChannelRiskLevel.LOW),
        item(id=uuid4(), created_at=dt("2026-05-29T09:00:00"), source_platform=SourcePlatform.YANDEX_MAPS, source_risk_level=ChannelRiskLevel.MEDIUM),
    ]

    dashboard = DashboardService.phase_one_funnel_from_records(
        candidates=candidates,
        staging_leads=[],
        core_sources=[],
        channel="official_website",
        risk_level="Low",
        daily_candidate_target=100,
    )

    assert dashboard["summary"]["candidate_url_count"] == 1
    assert dashboard["channels"][0]["channel_name"] == "official_website"
    assert dashboard["channels"][0]["risk_level"] == "Low"


def test_phase_one_funnel_api_contract_exists() -> None:
    api_file = API_ROOT / "app" / "api" / "dashboard.py"
    schemas_file = API_ROOT / "app" / "schemas" / "dashboard.py"

    assert '@router.get("/phase-one-funnel"' in api_file.read_text(encoding="utf-8")
    assert "PhaseOneFunnelDashboardResponse" in schemas_file.read_text(encoding="utf-8")
