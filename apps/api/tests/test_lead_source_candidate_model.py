from pathlib import Path

from pydantic import ValidationError

from app.models.enums import (
    ChannelRiskLevel,
    LeadSourceCandidateExtractionStatus,
    LeadSourceCandidateReviewStatus,
    SourcePlatform,
)
from app.services.lead_source_candidate_rules import LeadSourceCandidateRules


API_ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = API_ROOT / "alembic" / "versions" / "20260602_0022_create_lead_source_candidates.py"
LEAD_SOURCE_MODEL_PATH = API_ROOT / "app" / "models" / "lead_source.py"


def test_lead_source_candidates_migration_declares_required_table_and_fields() -> None:
    assert MIGRATION_PATH.exists()
    migration = MIGRATION_PATH.read_text(encoding="utf-8")

    assert 'revision = "20260602_0022"' in migration
    assert 'down_revision = "20260602_0021"' in migration
    assert '"lead_source_candidates"' in migration
    for field_name in (
        "source_url",
        "normalized_domain",
        "platform",
        "channel_name",
        "country",
        "city",
        "risk_level",
        "review_status",
        "approved_for_extraction",
        "reviewer_id",
        "review_note",
        "reviewed_at",
        "discovery_method",
        "discovery_query",
        "discovery_reason",
        "evidence_note",
        "evidence_links",
        "llm_provider",
        "llm_model",
        "llm_output_json",
        "confidence_score",
        "extraction_status",
        "last_extracted_at",
        "next_retry_at",
        "retry_count",
        "dedupe_key",
        "duplicate_of_id",
        "is_duplicate",
        "created_by_task_run_id",
        "created_at",
        "updated_at",
    ):
        assert field_name in migration
    assert "customer_id" not in migration


def test_lead_source_candidate_model_and_schema_are_registered() -> None:
    models_init = (API_ROOT / "app" / "models" / "__init__.py").read_text(encoding="utf-8")
    schema_file = API_ROOT / "app" / "schemas" / "lead_source_candidate.py"

    assert "LeadSourceCandidate" in models_init
    assert schema_file.exists()


def test_formal_lead_sources_still_require_customer_id() -> None:
    lead_source_model = LEAD_SOURCE_MODEL_PATH.read_text(encoding="utf-8")

    assert "customer_id" in lead_source_model
    assert 'ForeignKey("customers.id"' in lead_source_model
    assert "nullable=False" in lead_source_model


def test_lead_source_candidate_schema_rejects_invalid_risk_level() -> None:
    from app.schemas.lead_source_candidate import LeadSourceCandidateCreate

    try:
        LeadSourceCandidateCreate(
            source_url="https://example.com/dealers",
            normalized_domain="example.com",
            platform=SourcePlatform.OFFICIAL_WEBSITE,
            channel_name="dealer_directory",
            country="Russia",
            city="Moscow",
            risk_level="UnknownRisk",
            discovery_method="keyword_search",
            discovery_query="автосалон Москва",
            discovery_reason="公开目录页",
            evidence_note="公开页面包含 dealer 和 contact 信息",
            evidence_links=["https://example.com/dealers"],
        )
    except ValidationError as exc:
        assert "risk_level" in str(exc)
    else:
        raise AssertionError("LeadSourceCandidateCreate should reject invalid risk level")


def test_low_and_medium_default_to_auto_approved_for_extraction() -> None:
    for risk_level in (ChannelRiskLevel.LOW, ChannelRiskLevel.MEDIUM):
        defaults = LeadSourceCandidateRules.resolve_defaults(risk_level)

        assert defaults.review_status == LeadSourceCandidateReviewStatus.AUTO_APPROVED
        assert defaults.approved_for_extraction is True
        assert defaults.extraction_status == LeadSourceCandidateExtractionStatus.PENDING


def test_high_defaults_to_high_risk_review_without_extraction_approval() -> None:
    defaults = LeadSourceCandidateRules.resolve_defaults(ChannelRiskLevel.HIGH)

    assert defaults.review_status == LeadSourceCandidateReviewStatus.HIGH_RISK_REVIEW
    assert defaults.approved_for_extraction is False
    assert defaults.extraction_status == LeadSourceCandidateExtractionStatus.PENDING


def test_forbidden_defaults_to_rejected_and_blocked_from_extraction() -> None:
    defaults = LeadSourceCandidateRules.resolve_defaults(ChannelRiskLevel.FORBIDDEN)

    assert defaults.review_status == LeadSourceCandidateReviewStatus.REJECTED
    assert defaults.approved_for_extraction is False
    assert defaults.extraction_status == LeadSourceCandidateExtractionStatus.BLOCKED


def test_dedupe_key_uses_normalized_domain_platform_and_url() -> None:
    first = LeadSourceCandidateRules.build_dedupe_key(
        source_url="HTTPS://Example.com/dealers/?b=2&a=1#team",
        normalized_domain="Example.com",
        platform=SourcePlatform.OFFICIAL_WEBSITE,
    )
    second = LeadSourceCandidateRules.build_dedupe_key(
        source_url="https://example.com/dealers?a=1&b=2",
        normalized_domain="example.com",
        platform=SourcePlatform.OFFICIAL_WEBSITE,
    )

    assert first == second
    assert len(first) == 64
