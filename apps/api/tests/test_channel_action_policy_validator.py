from app.models.enums import ChannelRiskLevel, SourceUsageType
from app.services.channel_risk import ChannelActionPolicyValidator


def test_globally_forbidden_actions_are_blocked() -> None:
    for action in (
        "login",
        "message",
        "friend_request",
        "join_group",
        "scrape_comments",
        "scrape_followers",
        "bypass_rate_limit",
    ):
        decision = ChannelActionPolicyValidator.evaluate(
            risk_level=ChannelRiskLevel.LOW,
            requested_action=action,
            allowed_actions="read_public_page;extract_business_contact",
            forbidden_actions="",
            source_usage_type=SourceUsageType.AUTOMATIC_COLLECTION,
        )

        assert decision.allowed is False
        assert action in (decision.block_reason or "")


def test_high_channel_allows_only_public_read_actions() -> None:
    for action in ("read_public_page", "extract_business_contact", "capture_limited_evidence"):
        decision = ChannelActionPolicyValidator.evaluate(
            risk_level=ChannelRiskLevel.HIGH,
            requested_action=action,
            allowed_actions="read_public_page;extract_business_contact;capture_limited_evidence",
            forbidden_actions="message;friend_request",
            source_usage_type=SourceUsageType.PUBLIC_DISCOVERY_ONLY,
        )

        assert decision.allowed is True
        assert decision.block_reason is None


def test_high_channel_blocks_non_read_action() -> None:
    decision = ChannelActionPolicyValidator.evaluate(
        risk_level=ChannelRiskLevel.HIGH,
        requested_action="crawl_public_directory",
        allowed_actions="read_public_page;extract_business_contact;capture_limited_evidence",
        forbidden_actions="message;friend_request",
        source_usage_type=SourceUsageType.PUBLIC_DISCOVERY_ONLY,
    )

    assert decision.allowed is False
    assert "High 风险渠道只允许只读公开动作" in (decision.block_reason or "")


def test_high_channel_blocks_non_public_discovery_usage() -> None:
    decision = ChannelActionPolicyValidator.evaluate(
        risk_level=ChannelRiskLevel.HIGH,
        requested_action="read_public_page",
        allowed_actions="read_public_page",
        forbidden_actions="message;friend_request",
        source_usage_type=SourceUsageType.AUTOMATIC_COLLECTION,
    )

    assert decision.allowed is False
    assert "High 渠道必须使用 public_discovery_only" in (decision.block_reason or "")


def test_action_not_in_allowed_actions_is_blocked() -> None:
    decision = ChannelActionPolicyValidator.evaluate(
        risk_level=ChannelRiskLevel.MEDIUM,
        requested_action="crawl_public_directory",
        allowed_actions="read_public_page;extract_business_contact",
        forbidden_actions="message;friend_request",
        source_usage_type=SourceUsageType.AUTOMATIC_COLLECTION,
    )

    assert decision.allowed is False
    assert "不在渠道允许动作列表" in (decision.block_reason or "")


def test_requested_action_matching_forbidden_actions_is_blocked() -> None:
    decision = ChannelActionPolicyValidator.evaluate(
        risk_level=ChannelRiskLevel.LOW,
        requested_action="bulk_scrape_directory",
        allowed_actions="read_public_page;bulk_scrape_directory",
        forbidden_actions="bulk_scrape_directory;login",
        source_usage_type=SourceUsageType.AUTOMATIC_COLLECTION,
    )

    assert decision.allowed is False
    assert "命中渠道禁止动作" in (decision.block_reason or "")


def test_channel_risk_api_accepts_source_usage_type() -> None:
    schema_file = "apps/api/app/schemas/channel_risk.py"
    with open(schema_file, encoding="utf-8") as file:
        schema = file.read()

    assert "source_usage_type" in schema
    assert "public_discovery_only" in schema


def test_blocked_action_path_records_risk_event() -> None:
    service_file = "apps/api/app/services/channel_risk.py"
    with open(service_file, encoding="utf-8") as file:
        service = file.read()

    assert "_record_blocked_audit" in service
    assert "AuditRiskLogService" in service
    assert "record_risk_event" in service
    assert 'event_type="rule_block"' in service
