from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from app.models.enums import ChannelRiskLevel, CustomerGrade, SourcePlatform, StagingReviewStatus
from app.services.dashboard import DashboardService


API_ROOT = Path(__file__).resolve().parents[1]


def item(**kwargs):
    return SimpleNamespace(**kwargs)


def dt(value: str) -> datetime:
    return datetime.fromisoformat(value)


def test_roi_metrics_from_records_include_ai_cost_tokens_and_review_efficiency() -> None:
    cost_entries = [
        item(cost_type="labor", amount=120, channel_name="official_website"),
        item(cost_type="ai_api", amount=20, channel_name="official_website"),
        item(cost_type="tool", amount=60, channel_name="official_website"),
    ]
    audit_logs = [
        item(
            id=uuid4(),
            channel_name="official_website",
            risk_blocked=False,
            input_tokens=100,
            output_tokens=50,
            total_tokens=150,
            cost_amount=1.5,
            output_json={"result": "ok"},
            created_at=dt("2026-05-29T09:00:00"),
        ),
        item(
            id=uuid4(),
            channel_name="official_website",
            risk_blocked=True,
            input_tokens=80,
            output_tokens=20,
            total_tokens=100,
            cost_amount=0.5,
            output_json={"result": "blocked"},
            created_at=dt("2026-05-29T10:00:00"),
        ),
    ]
    low_candidate = item(
        source_platform=SourcePlatform.OFFICIAL_WEBSITE,
        source_risk_level=ChannelRiskLevel.LOW,
    )
    staging_leads = [
        item(
            id=uuid4(),
            candidate_url=low_candidate,
            created_at=dt("2026-05-29T08:00:00"),
            updated_at=dt("2026-05-29T11:00:00"),
            review_status=StagingReviewStatus.APPROVED,
        ),
        item(
            id=uuid4(),
            candidate_url=low_candidate,
            created_at=dt("2026-05-29T08:30:00"),
            updated_at=dt("2026-05-29T08:50:00"),
            review_status=StagingReviewStatus.PENDING_REVIEW,
        ),
    ]
    core_sources = [
        (
            item(id=uuid4(), grade=CustomerGrade.B, do_not_contact=False, created_at=dt("2026-05-29T12:00:00")),
            item(platform=SourcePlatform.OFFICIAL_WEBSITE, channel_risk_level=ChannelRiskLevel.LOW, collected_at=dt("2026-05-29T12:00:00")),
        ),
        (
            item(id=uuid4(), grade=CustomerGrade.C, do_not_contact=False, created_at=dt("2026-05-29T13:00:00")),
            item(platform=SourcePlatform.OFFICIAL_WEBSITE, channel_risk_level=ChannelRiskLevel.LOW, collected_at=dt("2026-05-29T13:00:00")),
        ),
    ]
    outreach_records = [item(sent_at=dt("2026-05-29T14:00:00"), channel="email")]

    dashboard = DashboardService.roi_metrics_from_records(
        cost_entries=cost_entries,
        audit_logs=audit_logs,
        staging_leads=staging_leads,
        core_sources=core_sources,
        outreach_records=outreach_records,
        date_from="2026-05-29",
        date_to="2026-05-29",
        channel="official_website",
    )

    summary = dashboard["summary"]
    assert summary["total_cost"] == 200
    assert summary["llm_call_count"] == 2
    assert summary["llm_failure_count"] == 1
    assert summary["llm_failure_rate"] == 0.5
    assert summary["llm_token_count"] == 250
    assert summary["llm_cost_total"] == 2.0
    assert summary["review_completed_count"] == 1
    assert summary["avg_review_duration_hours"] == 3.0
    assert summary["ai_cost_per_effective_lead"] == 1.0
    assert summary["reply_count"] == 1
    assert summary["cost_per_reply"] == 200.0


def test_roi_metrics_api_contract_mentions_ai_cost_fields() -> None:
    api_file = API_ROOT / "app" / "api" / "dashboard.py"
    schemas_file = API_ROOT / "app" / "schemas" / "dashboard.py"

    assert '@router.get("/roi-metrics"' in api_file.read_text(encoding="utf-8")
    assert "llm_call_count" in schemas_file.read_text(encoding="utf-8")
