from pathlib import Path

from app.models.enums import ChannelRiskLevel, SourcePlatform
from app.services.raw_collection import RawCollectionService


API_ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = API_ROOT / "alembic" / "versions" / "20260529_0010_raw_collection_tasks_candidate_urls.py"


def test_raw_collection_migration_declares_required_tables_and_constraints() -> None:
    assert MIGRATION_PATH.exists()
    migration = MIGRATION_PATH.read_text(encoding="utf-8")

    assert 'revision = "20260529_0010"' in migration
    assert 'down_revision = "20260529_0009"' in migration
    assert '"collection_tasks"' in migration
    assert '"candidate_urls"' in migration
    assert "requires_secondary_verification" in migration
    assert "forbidden_actions" in migration
    assert "url_hash" in migration
    assert "uq_candidate_urls_url_hash" in migration
    assert 'sa.ForeignKey("collection_tasks.id"' in migration


def test_raw_collection_models_are_registered_for_alembic_metadata() -> None:
    models_init = (API_ROOT / "app" / "models" / "__init__.py").read_text(encoding="utf-8")

    assert "CollectionTask" in models_init
    assert "CandidateUrl" in models_init


def test_normalized_url_hash_is_stable_for_equivalent_urls() -> None:
    first = RawCollectionService.hash_url("HTTPS://Example.com/dealers/?b=2&a=1#team")
    second = RawCollectionService.hash_url("https://example.com/dealers?a=1&b=2")

    assert first == second
    assert len(first) == 64


def test_high_risk_task_defaults_to_public_discovery_only() -> None:
    usage_type = RawCollectionService.resolve_source_usage_type(
        risk_level=ChannelRiskLevel.HIGH,
        requested_usage_type=None,
    )

    assert usage_type == "public_discovery_only"


def test_high_risk_task_rejects_non_public_discovery_usage() -> None:
    try:
        RawCollectionService.resolve_source_usage_type(
            risk_level=ChannelRiskLevel.HIGH,
            requested_usage_type="automatic_collection",
        )
    except ValueError as exc:
        assert "High 风险渠道只能 public_discovery_only" in str(exc)
    else:
        raise AssertionError("High risk task should reject automatic collection")


def test_forbidden_channel_rejects_executable_task() -> None:
    try:
        RawCollectionService.resolve_source_usage_type(
            risk_level=ChannelRiskLevel.FORBIDDEN,
            requested_usage_type="policy_research",
        )
    except ValueError as exc:
        assert "Forbidden 渠道不得创建可执行任务" in str(exc)
    else:
        raise AssertionError("Forbidden channel should reject executable tasks")


def test_candidate_secondary_verification_defaults_by_risk_level() -> None:
    assert RawCollectionService.requires_secondary_verification(ChannelRiskLevel.HIGH) is True
    assert RawCollectionService.requires_secondary_verification(ChannelRiskLevel.MEDIUM) is False
    assert RawCollectionService.requires_secondary_verification(ChannelRiskLevel.LOW) is False


def test_candidate_payload_requires_task_id() -> None:
    try:
        RawCollectionService.validate_candidate_task_id(None)
    except ValueError as exc:
        assert "candidate URL 必须关联 task_id" in str(exc)
    else:
        raise AssertionError("candidate URL without task_id should be rejected")


def test_default_source_platform_value_is_supported() -> None:
    assert SourcePlatform.SEARCH_ENGINE.value == "search_engine"
