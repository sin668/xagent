from pathlib import Path

from sqlalchemy import inspect

from app.models.email_reply_draft import EmailReplyDraft
from app.models.enums import KnowledgeUsageOutcome
from app.models.knowledge import KnowledgeItem


API_ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = API_ROOT / "alembic" / "versions" / "20260605_0033_create_knowledge_usage_quality.py"


def test_phase5_knowledge_usage_outcome_enum_defines_reply_quality_events() -> None:
    assert KnowledgeUsageOutcome.RETRIEVED == "retrieved"
    assert KnowledgeUsageOutcome.ADOPTED == "adopted"
    assert KnowledgeUsageOutcome.EDITED == "edited"
    assert KnowledgeUsageOutcome.REJECTED == "rejected"
    assert KnowledgeUsageOutcome.CUSTOMER_REPLIED == "customer_replied"
    assert KnowledgeUsageOutcome.BOUNCED == "bounced"
    assert KnowledgeUsageOutcome.SUGGEST_DEPRECATE == "suggest_deprecate"


def test_phase5_knowledge_usage_model_records_retrieval_context_and_outcomes() -> None:
    from app.models import KnowledgeUsageRecord

    columns = inspect(KnowledgeUsageRecord).columns

    for column_name in (
        "id",
        "knowledge_item_id",
        "knowledge_version",
        "email_reply_draft_id",
        "retrieval_query",
        "similarity_score",
        "rank",
        "filters_json",
        "outcome",
        "adopted",
        "edit_distance_ratio",
        "caused_bounce",
        "customer_replied",
        "suggest_deprecate",
        "suggest_deprecate_reason",
        "created_at",
        "updated_at",
    ):
        assert column_name in columns

    assert columns["knowledge_item_id"].nullable is False
    assert columns["knowledge_version"].nullable is False
    assert columns["filters_json"].nullable is False
    assert columns["similarity_score"].nullable is True
    assert columns["outcome"].index is True
    assert columns["suggest_deprecate"].index is True

    assert hasattr(KnowledgeItem, "usage_records")
    assert hasattr(EmailReplyDraft, "knowledge_usage_records")


def test_phase5_knowledge_quality_model_supports_aggregated_metrics() -> None:
    from app.models import KnowledgeQualityMetric

    columns = inspect(KnowledgeQualityMetric).columns

    for column_name in (
        "id",
        "knowledge_item_id",
        "knowledge_version",
        "period_start",
        "period_end",
        "retrieval_count",
        "adoption_count",
        "adoption_rate",
        "average_edit_distance_ratio",
        "bounce_count",
        "bounce_rate",
        "customer_reply_count",
        "customer_reply_rate",
        "suggest_deprecate",
        "suggest_deprecate_reason",
        "calculated_at",
    ):
        assert column_name in columns

    assert columns["retrieval_count"].nullable is False
    assert columns["adoption_rate"].nullable is False
    assert columns["bounce_rate"].nullable is False
    assert columns["customer_reply_rate"].nullable is False
    assert columns["suggest_deprecate"].index is True
    assert hasattr(KnowledgeItem, "quality_metrics")


def test_phase5_knowledge_usage_quality_migration_declares_contracts() -> None:
    assert MIGRATION_PATH.exists()
    migration = MIGRATION_PATH.read_text(encoding="utf-8")

    assert 'revision = "20260605_0033"' in migration
    assert 'down_revision = "20260605_0032"' in migration
    assert '"knowledge_usage_records"' in migration
    assert '"knowledge_quality_metrics"' in migration
    assert "knowledgeusageoutcome" in migration

    for column_name in (
        "knowledge_item_id",
        "knowledge_version",
        "email_reply_draft_id",
        "similarity_score",
        "filters_json",
        "outcome",
        "adopted",
        "edit_distance_ratio",
        "retrieval_count",
        "adoption_rate",
        "bounce_rate",
        "customer_reply_rate",
        "suggest_deprecate",
    ):
        assert column_name in migration

    assert "knowledge_items.id" in migration
    assert "email_reply_drafts.id" in migration
    assert "drop_table" in migration
