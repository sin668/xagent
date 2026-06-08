from pathlib import Path

from pydantic import ValidationError
from sqlalchemy import insert, select
from sqlalchemy.dialects import postgresql

from app.db.base import Base
from app.models import LeadEnrichmentResult
from app.models.enums import LeadEnrichmentResultStatus, LeadEnrichmentType
from app.schemas.lead_enrichment_result import LeadEnrichmentResultCreate, LeadEnrichmentResultUpdate


API_ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = API_ROOT / "alembic" / "versions" / "20260604_0024_create_lead_enrichment_results.py"


def test_lead_enrichment_results_migration_declares_required_table_and_fields() -> None:
    assert MIGRATION_PATH.exists()
    migration = MIGRATION_PATH.read_text(encoding="utf-8")

    assert 'revision = "20260604_0024"' in migration
    assert 'down_revision = "20260603_0023"' in migration
    assert '"lead_enrichment_results"' in migration
    for field_name in (
        "staging_lead_id",
        "enrichment_type",
        "triggered_by",
        "status",
        "input_snapshot_json",
        "output_json",
        "evidence_links",
        "confidence_score",
        "missing_fields",
        "recommended_action",
        "agent_task_run_id",
        "created_at",
        "updated_at",
    ):
        assert field_name in migration
    assert "customer_id" not in migration
    assert '"customers"' not in migration


def test_lead_enrichment_result_model_is_registered_for_alembic_metadata() -> None:
    table_names = set(Base.metadata.tables.keys())
    models_init = (API_ROOT / "app" / "models" / "__init__.py").read_text(encoding="utf-8")

    assert "lead_enrichment_results" in table_names
    assert "LeadEnrichmentResult" in models_init
    assert "LeadEnrichmentType" in models_init
    assert "LeadEnrichmentResultStatus" in models_init


def test_lead_enrichment_result_metadata_keeps_staging_separate_from_customers() -> None:
    columns = set(Base.metadata.tables["lead_enrichment_results"].columns.keys())

    assert "staging_lead_id" in columns
    assert "agent_task_run_id" in columns
    assert "customer_id" not in columns


def test_lead_enrichment_type_and_status_enums_are_strict() -> None:
    assert LeadEnrichmentType.AI_DEEP_RESEARCH.value == "ai_deep_research"
    assert LeadEnrichmentType.MANUAL_SUPPLEMENT.value == "manual_supplement"
    assert LeadEnrichmentResultStatus.PENDING.value == "pending"
    assert LeadEnrichmentResultStatus.SUCCEEDED.value == "succeeded"
    assert LeadEnrichmentResultStatus.FAILED.value == "failed"
    assert LeadEnrichmentResultStatus.CANCELLED.value == "cancelled"

    try:
        LeadEnrichmentResultCreate(
            staging_lead_id="11111111-1111-1111-1111-111111111111",
            enrichment_type="auto_promote",
            triggered_by="operator-a",
        )
    except ValidationError as exc:
        assert "enrichment_type" in str(exc)
    else:
        raise AssertionError("LeadEnrichmentResultCreate should reject unknown enrichment_type")


def test_lead_enrichment_result_schema_preserves_unknowns_and_json_defaults() -> None:
    payload = LeadEnrichmentResultCreate(
        staging_lead_id="11111111-1111-1111-1111-111111111111",
        enrichment_type=LeadEnrichmentType.AI_DEEP_RESEARCH,
        triggered_by="operator-a",
        input_snapshot_json={"customer_name": "Unknown"},
        output_json={"city": None},
        evidence_links=["https://example.com/public-source"],
        missing_fields=["email"],
        recommended_action="manual_review",
        confidence_score=0.72,
    )

    assert payload.status == LeadEnrichmentResultStatus.PENDING
    assert payload.input_snapshot_json == {"customer_name": "Unknown"}
    assert payload.output_json == {"city": None}
    assert payload.evidence_links == ["https://example.com/public-source"]
    assert payload.missing_fields == ["email"]


def test_lead_enrichment_result_schema_rejects_invalid_confidence_score() -> None:
    try:
        LeadEnrichmentResultUpdate(confidence_score=1.2)
    except ValidationError as exc:
        assert "confidence_score" in str(exc)
    else:
        raise AssertionError("confidence_score above 1 should be rejected")


def test_lead_enrichment_result_can_compile_minimal_insert_and_select_sql() -> None:
    statement = insert(LeadEnrichmentResult).values(
        staging_lead_id="11111111-1111-1111-1111-111111111111",
        enrichment_type=LeadEnrichmentType.AI_DEEP_RESEARCH,
        triggered_by="operator-a",
        status=LeadEnrichmentResultStatus.PENDING,
        input_snapshot_json={"customer_name": "Unknown"},
        output_json={"contacts": []},
        evidence_links=[],
        missing_fields=["email"],
        recommended_action="manual_review",
    )
    query = select(LeadEnrichmentResult).where(LeadEnrichmentResult.status == LeadEnrichmentResultStatus.PENDING)

    compiled_insert = str(statement.compile(dialect=postgresql.dialect()))
    compiled_query = str(query.compile(dialect=postgresql.dialect()))

    assert "INSERT INTO lead_enrichment_results" in compiled_insert
    assert "SELECT" in compiled_query
    assert "lead_enrichment_results" in compiled_query
