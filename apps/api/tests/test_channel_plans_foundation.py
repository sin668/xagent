from pathlib import Path

from app.models.enums import ChannelPlanStatus, ChannelRiskLevel, SourceUsageType
from app.services.channel_plans import ChannelPlanService


API_ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = API_ROOT / "alembic" / "versions" / "20260529_0014_channel_plans.py"


def test_channel_plan_migration_declares_required_table_and_fields() -> None:
    assert MIGRATION_PATH.exists()
    migration = MIGRATION_PATH.read_text(encoding="utf-8")

    assert 'revision = "20260529_0014"' in migration
    assert 'down_revision = "20260529_0013"' in migration
    assert '"channel_plans"' in migration
    assert "country" in migration
    assert "city" in migration
    assert "channel_name" in migration
    assert "channel_type" in migration
    assert "risk_level" in migration
    assert "keywords" in migration
    assert "daily_url_limit" in migration
    assert "daily_lead_limit" in migration
    assert "source_usage_type" in migration
    assert "owner" in migration


def test_channel_plan_model_and_router_are_registered() -> None:
    models_init = (API_ROOT / "app" / "models" / "__init__.py").read_text(encoding="utf-8")
    main_py = (API_ROOT / "app" / "main.py").read_text(encoding="utf-8")

    assert "ChannelPlan" in models_init
    assert "channel_plans_router" in main_py


def test_forbidden_channel_plan_cannot_be_enabled() -> None:
    try:
        ChannelPlanService.resolve_plan_policy(
            risk_level=ChannelRiskLevel.FORBIDDEN,
            status=ChannelPlanStatus.ENABLED,
            requested_usage_type=SourceUsageType.POLICY_RESEARCH,
        )
    except ValueError as exc:
        assert "Forbidden 计划不能启用" in str(exc)
    else:
        raise AssertionError("Forbidden plan should not be enabled")


def test_high_enabled_plan_must_be_public_discovery_only() -> None:
    try:
        ChannelPlanService.resolve_plan_policy(
            risk_level=ChannelRiskLevel.HIGH,
            status=ChannelPlanStatus.ENABLED,
            requested_usage_type=SourceUsageType.AUTOMATIC_COLLECTION,
        )
    except ValueError as exc:
        assert "High 计划启用时必须限定 public_discovery_only" in str(exc)
    else:
        raise AssertionError("High enabled plan should require public discovery only")


def test_high_plan_defaults_to_public_discovery_only() -> None:
    usage = ChannelPlanService.resolve_plan_policy(
        risk_level=ChannelRiskLevel.HIGH,
        status=ChannelPlanStatus.DRAFT,
        requested_usage_type=None,
    )

    assert usage == SourceUsageType.PUBLIC_DISCOVERY_ONLY


def test_low_medium_plan_defaults_to_automatic_collection() -> None:
    usage = ChannelPlanService.resolve_plan_policy(
        risk_level=ChannelRiskLevel.MEDIUM,
        status=ChannelPlanStatus.ENABLED,
        requested_usage_type=None,
    )

    assert usage == SourceUsageType.AUTOMATIC_COLLECTION


def test_daily_url_limit_is_required_and_positive() -> None:
    for limit in (None, 0, -1):
        try:
            ChannelPlanService.validate_daily_url_limit(limit)
        except ValueError as exc:
            assert "daily_url_limit 不得为空且必须大于 0" in str(exc)
        else:
            raise AssertionError("daily_url_limit should reject empty or non-positive values")


def test_forbidden_automation_actions_are_rejected() -> None:
    try:
        ChannelPlanService.validate_no_forbidden_actions(
            channel_name="VK",
            channel_type="social",
            keywords=["авто", "автоматическая рассылка", "добавить в друзья"],
        )
    except ValueError as exc:
        assert "不允许创建包含自动私信、加好友、登录采集的计划" in str(exc)
    else:
        raise AssertionError("Plan containing forbidden actions should be rejected")


def test_channel_plan_crud_api_contract_exists() -> None:
    api_file = (API_ROOT / "app" / "api" / "channel_plans.py").read_text(encoding="utf-8")

    assert '@router.post("",' in api_file
    assert '@router.get("",' in api_file
    assert '@router.get("/{plan_id:uuid}",' in api_file
    assert '@router.patch("/{plan_id:uuid}",' in api_file
    assert '@router.delete("/{plan_id:uuid}",' in api_file
