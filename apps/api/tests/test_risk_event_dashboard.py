from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from app.models.enums import ChannelPlanStatus, ChannelRiskLevel, RiskEventSeverity, RiskEventStatus
from app.services.dashboard import DashboardService


API_ROOT = Path(__file__).resolve().parents[1]


def item(**kwargs):
    return SimpleNamespace(**kwargs)


def dt(value: str) -> datetime:
    return datetime.fromisoformat(value)


def test_risk_event_dashboard_groups_open_events_and_paused_channels() -> None:
    paused_plan = item(
        id=uuid4(),
        country="俄罗斯",
        city="Moscow",
        channel_name="vkontakte",
        channel_type="social",
        risk_level=ChannelRiskLevel.HIGH,
        status=ChannelPlanStatus.PAUSED,
        owner="合规负责人",
        daily_url_limit=50,
        daily_lead_limit=10,
        keywords=["car dealer"],
        created_at=dt("2026-05-29T08:00:00"),
        updated_at=dt("2026-05-29T09:00:00"),
    )
    enabled_plan = item(
        id=uuid4(),
        country="俄罗斯",
        city="Kazan",
        channel_name="official_website",
        channel_type="website",
        risk_level=ChannelRiskLevel.LOW,
        status=ChannelPlanStatus.ENABLED,
        owner="运营",
        daily_url_limit=100,
        daily_lead_limit=20,
        keywords=["used cars"],
        created_at=dt("2026-05-29T08:00:00"),
        updated_at=dt("2026-05-29T09:00:00"),
    )

    risk_events = [
        item(
            id=uuid4(),
            channel_plan_id=paused_plan.id,
            task_id="task-1",
            agent_name="collector",
            action="auto_collect",
            channel="vkontakte",
            risk_level=ChannelRiskLevel.HIGH,
            event_type="platform_warning",
            severity=RiskEventSeverity.CRITICAL,
            resolution_status=RiskEventStatus.OPEN,
            block_reason="平台警告，出现验证码",
            pause_suggested=True,
            resolution_note=None,
            resolved_by=None,
            input_ref="input-1",
            output_ref="output-1",
            result="blocked",
            error_message=None,
            created_at=dt("2026-05-29T10:00:00"),
            resolved_at=None,
        ),
        item(
            id=uuid4(),
            channel_plan_id=enabled_plan.id,
            task_id="task-2",
            agent_name="reviewer",
            action="manual_review",
            channel="official_website",
            risk_level=ChannelRiskLevel.LOW,
            event_type="do_not_contact_breach",
            severity=RiskEventSeverity.MEDIUM,
            resolution_status=RiskEventStatus.RESOLVED,
            block_reason="勿扰客户误入触达队列",
            pause_suggested=False,
            resolution_note="已修正触达队列",
            resolved_by="alex",
            input_ref="input-2",
            output_ref="output-2",
            result="blocked",
            error_message=None,
            created_at=dt("2026-05-29T09:30:00"),
            resolved_at=dt("2026-05-29T11:00:00"),
        ),
    ]

    dashboard = DashboardService.risk_event_dashboard_from_records(
        risk_events=risk_events,
        channel_plans=[paused_plan, enabled_plan],
        date_from="2026-05-29",
        date_to="2026-05-29",
    )

    assert dashboard["summary"]["risk_event_count"] == 2
    assert dashboard["summary"]["open_risk_event_count"] == 1
    assert dashboard["summary"]["resolved_risk_event_count"] == 1
    assert dashboard["summary"]["critical_risk_event_count"] == 1
    assert dashboard["summary"]["pause_suggested_count"] == 1
    assert dashboard["summary"]["paused_channel_plan_count"] == 1
    assert dashboard["events"][0]["severity"] == "critical"
    assert dashboard["events"][0]["resolution_status"] == "open"
    assert dashboard["events"][0]["block_reason"] == "平台警告，出现验证码"
    assert dashboard["paused_channel_plans"][0]["channel_name"] == "vkontakte"
    assert dashboard["paused_channel_plans"][0]["latest_block_reason"] == "平台警告，出现验证码"
    assert dashboard["paused_channel_plans"][0]["resume_requires_resolution_note"] is True


def test_risk_event_dashboard_api_contract_exists() -> None:
    api_file = API_ROOT / "app" / "api" / "dashboard.py"
    schemas_file = API_ROOT / "app" / "schemas" / "dashboard.py"

    assert '@router.get("/risk-events"' in api_file.read_text(encoding="utf-8")
    assert "RiskEventDashboardResponse" in schemas_file.read_text(encoding="utf-8")
