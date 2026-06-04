from pathlib import Path

from app.models.enums import ChannelRiskLevel, CollectionTaskStatus, PageSnapshotReadStatus, SourceUsageType
from app.services.channel_risk import ChannelActionPolicyValidator
from app.services.raw_collection import RawCollectionService


API_ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = API_ROOT / "alembic" / "versions" / "20260529_0015_high_risk_public_discovery_isolation.py"


def test_high_risk_isolation_migration_adds_required_fields() -> None:
    assert MIGRATION_PATH.exists()
    migration = MIGRATION_PATH.read_text(encoding="utf-8")

    assert 'revision = "20260529_0015"' in migration
    assert 'down_revision = "20260529_0014"' in migration
    assert '"collection_tasks"' in migration
    assert "max_sample_size" in migration
    assert '"candidate_urls"' in migration
    assert "queue_eligible" in migration


def test_high_risk_public_discovery_task_defaults() -> None:
    defaults = RawCollectionService.resolve_task_defaults(
        task_type="high_risk_public_discovery",
        risk_level=ChannelRiskLevel.HIGH,
        requested_usage_type=None,
        max_sample_size=None,
    )

    assert defaults.source_usage_type == SourceUsageType.PUBLIC_DISCOVERY_ONLY
    assert defaults.max_sample_size == RawCollectionService.DEFAULT_HIGH_RISK_MAX_SAMPLE_SIZE


def test_high_risk_public_discovery_requires_high_risk_level() -> None:
    try:
        RawCollectionService.resolve_task_defaults(
            task_type="high_risk_public_discovery",
            risk_level=ChannelRiskLevel.MEDIUM,
            requested_usage_type=None,
            max_sample_size=None,
        )
    except ValueError as exc:
        assert "high_risk_public_discovery 必须使用 High 风险等级" in str(exc)
    else:
        raise AssertionError("high_risk_public_discovery should require High risk")


def test_high_risk_candidate_defaults_to_not_queue_eligible() -> None:
    assert RawCollectionService.default_queue_eligible(ChannelRiskLevel.HIGH) is False
    assert RawCollectionService.default_queue_eligible(ChannelRiskLevel.MEDIUM) is True


def test_high_risk_candidate_requires_secondary_verification() -> None:
    assert RawCollectionService.requires_secondary_verification(ChannelRiskLevel.HIGH) is True


def test_high_task_outreach_actions_are_blocked() -> None:
    decision = ChannelActionPolicyValidator.evaluate(
        risk_level=ChannelRiskLevel.HIGH,
        requested_action="message",
        allowed_actions="read_public_page;extract_business_contact;capture_limited_evidence",
        forbidden_actions="message;friend_request;join_group;scrape_comments;scrape_followers",
        source_usage_type=SourceUsageType.PUBLIC_DISCOVERY_ONLY,
    )

    assert decision.allowed is False
    assert "message" in (decision.block_reason or "")


def test_high_task_captcha_or_login_wall_blocks_task() -> None:
    for read_status in ("captcha", "login_wall"):
        assert (
            RawCollectionService.task_status_after_snapshot(
                task_type="high_risk_public_discovery",
                risk_level=ChannelRiskLevel.HIGH,
                read_status=read_status,
            )
            == CollectionTaskStatus.BLOCKED
        )


def test_high_task_success_snapshot_does_not_block_task() -> None:
    assert (
        RawCollectionService.task_status_after_snapshot(
            task_type="high_risk_public_discovery",
            risk_level=ChannelRiskLevel.HIGH,
            read_status=PageSnapshotReadStatus.SUCCESS,
        )
        is None
    )
