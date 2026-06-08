from pathlib import Path

from pydantic import ValidationError
from sqlalchemy import insert, select
from sqlalchemy.dialects import postgresql

from app.db.base import Base
from app.models import LeadEnrichmentFieldCandidate
from app.models.enums import LeadEnrichmentFieldReviewStatus, LeadEnrichmentFieldSourceType
from app.schemas.lead_enrichment_field_candidate import (
    LeadEnrichmentFieldCandidateCreate,
    LeadEnrichmentFieldCandidateUpdate,
)


API_ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = API_ROOT / "alembic" / "versions" / "20260604_0025_create_lead_enrichment_field_candidates.py"


def test_lead_enrichment_field_candidates_migration_declares_required_table_and_fields() -> None:
    assert MIGRATION_PATH.exists()
    migration = MIGRATION_PATH.read_text(encoding="utf-8")

    assert 'revision = "20260604_0025"' in migration
    assert 'down_revision = "20260604_0024"' in migration
    assert '"lead_enrichment_field_candidates"' in migration
    for field_name in (
        "enrichment_result_id",
        "staging_lead_id",
        "field_name",
        "candidate_value",
        "source_type",
        "source_url",
        "evidence_note",
        "confidence_score",
        "review_status",
        "accepted_by",
        "accepted_at",
        "rejected_reason",
        "created_at",
        "updated_at",
    ):
        assert field_name in migration
    assert "customer_id" not in migration
    assert '"customers"' not in migration


def test_lead_enrichment_field_candidate_model_is_registered_for_alembic_metadata() -> None:
    table_names = set(Base.metadata.tables.keys())
    models_init = (API_ROOT / "app" / "models" / "__init__.py").read_text(encoding="utf-8")

    assert "lead_enrichment_field_candidates" in table_names
    assert "LeadEnrichmentFieldCandidate" in models_init
    assert "LeadEnrichmentFieldReviewStatus" in models_init
    assert "LeadEnrichmentFieldSourceType" in models_init


def test_lead_enrichment_field_candidate_metadata_keeps_unaccepted_fields_out_of_customers() -> None:
    columns = set(Base.metadata.tables["lead_enrichment_field_candidates"].columns.keys())

    assert "enrichment_result_id" in columns
    assert "staging_lead_id" in columns
    assert "candidate_value" in columns
    assert "customer_id" not in columns
    assert Base.metadata.tables["lead_enrichment_field_candidates"].columns["review_status"].nullable is False


def test_field_candidate_review_status_supports_pending_accepted_rejected_and_needs_review() -> None:
    assert LeadEnrichmentFieldReviewStatus.PENDING.value == "pending"
    assert LeadEnrichmentFieldReviewStatus.ACCEPTED.value == "accepted"
    assert LeadEnrichmentFieldReviewStatus.REJECTED.value == "rejected"
    assert LeadEnrichmentFieldReviewStatus.NEEDS_REVIEW.value == "needs_review"


def test_field_candidate_schema_preserves_source_evidence_and_json_candidate_value() -> None:
    payload = LeadEnrichmentFieldCandidateCreate(
        enrichment_result_id="11111111-1111-1111-1111-111111111111",
        staging_lead_id="22222222-2222-2222-2222-222222222222",
        field_name="contacts_json",
        candidate_value=[{"type": "email", "value": "sales@example.com"}],
        source_type=LeadEnrichmentFieldSourceType.AI_PUBLIC_SOURCE,
        source_url="https://example.com/contact",
        evidence_note="公开页面展示销售邮箱。",
        confidence_score=0.81,
    )

    assert payload.review_status == LeadEnrichmentFieldReviewStatus.PENDING
    assert payload.candidate_value == [{"type": "email", "value": "sales@example.com"}]
    assert payload.source_url == "https://example.com/contact"
    assert payload.evidence_note == "公开页面展示销售邮箱。"


def test_field_candidate_schema_rejects_invalid_review_status_and_confidence() -> None:
    try:
        LeadEnrichmentFieldCandidateCreate(
            enrichment_result_id="11111111-1111-1111-1111-111111111111",
            staging_lead_id="22222222-2222-2222-2222-222222222222",
            field_name="city",
            candidate_value="Moscow",
            source_type=LeadEnrichmentFieldSourceType.MANUAL_PUBLIC_INFO,
            evidence_note="人工公开资料补录。",
            review_status="auto_promoted",
            confidence_score=1.3,
        )
    except ValidationError as exc:
        assert "review_status" in str(exc)
        assert "confidence_score" in str(exc)
    else:
        raise AssertionError("invalid review_status and confidence_score should be rejected")


def test_field_candidate_acceptance_update_requires_operator_for_acceptance() -> None:
    try:
        LeadEnrichmentFieldCandidateUpdate(review_status=LeadEnrichmentFieldReviewStatus.ACCEPTED)
    except ValidationError as exc:
        assert "accepted_by" in str(exc)
    else:
        raise AssertionError("accepted field candidate should require accepted_by")


def test_field_candidate_can_compile_minimal_insert_and_select_sql() -> None:
    statement = insert(LeadEnrichmentFieldCandidate).values(
        enrichment_result_id="11111111-1111-1111-1111-111111111111",
        staging_lead_id="22222222-2222-2222-2222-222222222222",
        field_name="city",
        candidate_value="Moscow",
        source_type=LeadEnrichmentFieldSourceType.AI_PUBLIC_SOURCE,
        evidence_note="公开页面展示城市。",
        confidence_score=0.7,
        review_status=LeadEnrichmentFieldReviewStatus.PENDING,
    )
    query = select(LeadEnrichmentFieldCandidate).where(
        LeadEnrichmentFieldCandidate.review_status == LeadEnrichmentFieldReviewStatus.PENDING
    )

    compiled_insert = str(statement.compile(dialect=postgresql.dialect()))
    compiled_query = str(query.compile(dialect=postgresql.dialect()))

    assert "INSERT INTO lead_enrichment_field_candidates" in compiled_insert
    assert "SELECT" in compiled_query
    assert "lead_enrichment_field_candidates" in compiled_query
