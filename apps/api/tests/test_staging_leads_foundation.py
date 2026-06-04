from pathlib import Path

from app.models.enums import ChannelRiskLevel, CustomerGrade, StagingQueueStatus, StagingReviewStatus
from app.services.staging_leads import StagingLeadService


API_ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = API_ROOT / "alembic" / "versions" / "20260529_0012_staging_leads.py"


def test_staging_leads_migration_declares_required_fields() -> None:
    assert MIGRATION_PATH.exists()
    migration = MIGRATION_PATH.read_text(encoding="utf-8")

    assert 'revision = "20260529_0012"' in migration
    assert 'down_revision = "20260529_0011"' in migration
    assert '"staging_leads"' in migration
    for field in [
        "candidate_url_id",
        "customer_name",
        "country",
        "city",
        "customer_type",
        "contacts_json",
        "activity_level",
        "scale_signal",
        "import_used_car_relevance",
        "source_evidence",
        "recommended_grade",
        "recommended_reason",
        "missing_fields",
        "review_status",
        "queue_status",
        "dedupe_key",
        "requires_compliance_review",
    ]:
        assert field in migration
    assert 'sa.ForeignKey("candidate_urls.id"' in migration


def test_staging_lead_model_is_registered_for_alembic_metadata() -> None:
    models_init = (API_ROOT / "app" / "models" / "__init__.py").read_text(encoding="utf-8")

    assert "StagingLead" in models_init
    assert "StagingQueueStatus" in models_init
    assert "StagingReviewStatus" in models_init


def test_missing_fields_and_contacts_defaults_preserve_unknown_values() -> None:
    payload = StagingLeadService.normalize_payload(
        customer_name=None,
        country=None,
        city=None,
        contacts_json=None,
        missing_fields=None,
    )

    assert payload["customer_name"] == "Unknown"
    assert payload["country"] == "Unknown"
    assert payload["city"] is None
    assert payload["contacts_json"] == []
    assert payload["missing_fields"] == []


def test_invalid_and_watch_default_to_not_eligible_queue() -> None:
    assert StagingLeadService.default_queue_status(CustomerGrade.INVALID) == StagingQueueStatus.NOT_ELIGIBLE
    assert StagingLeadService.default_queue_status(CustomerGrade.WATCH) == StagingQueueStatus.NOT_ELIGIBLE
    assert StagingLeadService.default_queue_status(CustomerGrade.B) == StagingQueueStatus.PENDING_REVIEW


def test_high_source_defaults_to_needs_secondary_verification() -> None:
    assert (
        StagingLeadService.default_review_status(ChannelRiskLevel.HIGH)
        == StagingReviewStatus.NEEDS_SECONDARY_VERIFICATION
    )
    assert StagingLeadService.default_review_status(ChannelRiskLevel.LOW) == StagingReviewStatus.PENDING_REVIEW


def test_c_grade_requires_compliance_review_by_default() -> None:
    assert StagingLeadService.default_requires_compliance_review(CustomerGrade.C) is True
    assert StagingLeadService.default_requires_compliance_review(CustomerGrade.B) is False


def test_staging_lead_requires_candidate_url_id() -> None:
    try:
        StagingLeadService.validate_candidate_url_id(None)
    except ValueError as exc:
        assert "staging lead 必须关联 candidate_url_id" in str(exc)
    else:
        raise AssertionError("staging lead without candidate_url_id should be rejected")
