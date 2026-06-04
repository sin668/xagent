from pathlib import Path

from app.models.enums import ChannelPlanStatus, RiskEventSeverity
from app.services.audit_risk import AuditRiskLogService
from app.services.channel_plans import ChannelPlanService
from app.services.raw_collection import RawCollectionService


API_ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = API_ROOT / "alembic" / "versions" / "20260529_0016_channel_pause_risk_events.py"


def test_channel_pause_migration_adds_risk_event_plan_fields() -> None:
    assert MIGRATION_PATH.exists()
    migration = MIGRATION_PATH.read_text(encoding="utf-8")

    assert 'revision = "20260529_0016"' in migration
    assert 'down_revision = "20260529_0015"' in migration
    assert '"risk_events"' in migration
    assert "channel_plan_id" in migration
    assert "pause_suggested" in migration
    assert "resolution_note" in migration
    assert "resolved_by" in migration


def test_paused_or_archived_plan_blocks_new_collection_task() -> None:
    for status in (ChannelPlanStatus.PAUSED, ChannelPlanStatus.ARCHIVED):
        try:
            RawCollectionService.validate_plan_allows_new_task(status)
        except ValueError as exc:
            assert "暂停或归档渠道无法启动新任务" in str(exc)
        else:
            raise AssertionError("paused/archived plan should block new task")


def test_enabled_plan_allows_new_collection_task() -> None:
    RawCollectionService.validate_plan_allows_new_task(ChannelPlanStatus.ENABLED)


def test_resume_paused_channel_requires_resolution_note() -> None:
    try:
        ChannelPlanService.validate_resume_resolution_note(
            old_status=ChannelPlanStatus.PAUSED,
            new_status=ChannelPlanStatus.ENABLED,
            resolution_note="",
        )
    except ValueError as exc:
        assert "恢复渠道必须记录处理说明" in str(exc)
    else:
        raise AssertionError("resuming paused channel should require resolution note")


def test_complaint_ban_or_policy_risk_suggests_channel_pause() -> None:
    for event_type, reason in (
        ("complaint", "客户投诉"),
        ("account_ban", "账号封禁"),
        ("policy_violation", "平台违规风险"),
    ):
        assert (
            AuditRiskLogService.should_suggest_channel_pause(
                event_type=event_type,
                severity=RiskEventSeverity.MEDIUM,
                block_reason=reason,
            )
            is True
        )


def test_high_or_critical_risk_suggests_channel_pause() -> None:
    assert (
        AuditRiskLogService.should_suggest_channel_pause(
            event_type="rule_block",
            severity=RiskEventSeverity.HIGH,
            block_reason="High 风险动作阻断",
        )
        is True
    )


def test_low_rule_block_does_not_suggest_pause_by_default() -> None:
    assert (
        AuditRiskLogService.should_suggest_channel_pause(
            event_type="rule_block",
            severity=RiskEventSeverity.LOW,
            block_reason="普通规则阻断",
        )
        is False
    )


def test_risk_event_api_contract_exists() -> None:
    api_path = API_ROOT / "app" / "api" / "risk_events.py"
    assert api_path.exists()
    api_text = api_path.read_text(encoding="utf-8")

    assert '@router.post("",' in api_text
    assert '@router.get("",' in api_text
    assert '@router.post("/{event_id}/resolve",' in api_text
