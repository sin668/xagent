from pathlib import Path

from app.models.enums import ChannelPlanStatus, ChannelRiskLevel, SourceUsageType
from app.services.channel_discovery_agent import ChannelDiscoveryAgentService


API_ROOT = Path(__file__).resolve().parents[1]


class DummyPlan:
    def __init__(
        self,
        *,
        country="Russia",
        city="Moscow",
        channel_name="Yandex Maps",
        channel_type="maps",
        risk_level=ChannelRiskLevel.MEDIUM,
        source_usage_type=SourceUsageType.AUTOMATIC_COLLECTION,
        keywords=None,
        daily_url_limit=3,
        status=ChannelPlanStatus.ENABLED,
    ):
        self.id = "11111111-1111-1111-1111-111111111111"
        self.country = country
        self.city = city
        self.channel_name = channel_name
        self.channel_type = channel_type
        self.risk_level = risk_level
        self.source_usage_type = source_usage_type
        self.keywords = keywords or ["автосалон", "used cars"]
        self.daily_url_limit = daily_url_limit
        self.status = status


def test_discovery_specs_respect_daily_url_limit_and_explain_keyword_city_channel() -> None:
    plan = DummyPlan(daily_url_limit=2, keywords=["автосалон", "авто из Китая", "trade-in"])

    specs = ChannelDiscoveryAgentService.build_discovery_specs(plan)

    assert len(specs) == 2
    assert all("Moscow" in spec.discovery_reason for spec in specs)
    assert all("maps" in spec.discovery_reason for spec in specs)
    assert specs[0].keyword == "автосалон"
    assert specs[1].keyword == "авто из Китая"


def test_forbidden_plan_is_rejected_before_task_generation() -> None:
    plan = DummyPlan(risk_level=ChannelRiskLevel.FORBIDDEN)

    try:
        ChannelDiscoveryAgentService.validate_plan_for_discovery(plan)
    except ValueError as exc:
        assert "Forbidden 计划不允许执行渠道发现" in str(exc)
    else:
        raise AssertionError("Forbidden plan should not run discovery")


def test_plan_with_forbidden_action_terms_is_rejected_at_agent_runtime() -> None:
    plan = DummyPlan(keywords=["авто", "auto dm", "friend request"])

    try:
        ChannelDiscoveryAgentService.validate_plan_for_discovery(plan)
    except ValueError as exc:
        assert "自动私信、加好友、登录采集" in str(exc)
    else:
        raise AssertionError("Agent runtime should reject forbidden action terms")


def test_high_plan_is_forced_to_public_discovery_only() -> None:
    plan = DummyPlan(
        channel_name="VK",
        channel_type="social",
        risk_level=ChannelRiskLevel.HIGH,
        source_usage_type=SourceUsageType.PUBLIC_DISCOVERY_ONLY,
    )

    policy = ChannelDiscoveryAgentService.resolve_discovery_policy(plan)

    assert policy.task_type == "high_risk_public_discovery"
    assert policy.source_usage_type == SourceUsageType.PUBLIC_DISCOVERY_ONLY
    assert policy.queue_eligible is False


def test_high_plan_rejects_non_public_discovery_usage() -> None:
    plan = DummyPlan(
        channel_name="VK",
        channel_type="social",
        risk_level=ChannelRiskLevel.HIGH,
        source_usage_type=SourceUsageType.AUTOMATIC_COLLECTION,
    )

    try:
        ChannelDiscoveryAgentService.resolve_discovery_policy(plan)
    except ValueError as exc:
        assert "High 计划只允许 public_discovery_only" in str(exc)
    else:
        raise AssertionError("High plan should reject automatic discovery")


def test_discovery_task_text_does_not_contain_social_outreach_actions() -> None:
    plan = DummyPlan(channel_name="Official websites", channel_type="official_website")

    task_text = ChannelDiscoveryAgentService.build_task_text(plan)

    forbidden_generated_actions = ("自动私信", "自动加好友", "加好友", "入群", "auto dm", "friend request", "join group")
    assert not any(term in task_text.allowed_actions.lower() for term in forbidden_generated_actions)
    assert "公开页面" in task_text.allowed_actions


def test_channel_discovery_api_contract_is_registered() -> None:
    main_py = (API_ROOT / "app" / "main.py").read_text(encoding="utf-8")
    api_file = API_ROOT / "app" / "api" / "channel_discovery.py"

    assert api_file.exists()
    assert "channel_discovery_router" in main_py
    assert '@router.post("/run"' in api_file.read_text(encoding="utf-8")
