from sqlalchemy import insert, select
from sqlalchemy.dialects import postgresql

from app.db.base import Base
from app.models import (
    CustomerFollowup,
    CustomerVehicleIntent,
    LeadCleanupRun,
    LeadCleanupSuggestion,
    LeadEnrichmentFieldCandidate,
    LeadEnrichmentResult,
)
from app.models.enums import (
    CustomerFollowupTeam,
    CustomerFollowupType,
    CustomerVehicleIntentSourceType,
    CustomerVehicleIntentStatus,
    LeadCleanupRunStatus,
    LeadCleanupSuggestionReviewStatus,
    LeadCleanupSuggestionType,
    LeadEnrichmentFieldReviewStatus,
    LeadEnrichmentFieldSourceType,
    LeadEnrichmentResultStatus,
    LeadEnrichmentType,
)


def test_phase3_models_are_loaded_into_base_metadata() -> None:
    table_names = set(Base.metadata.tables.keys())

    for table_name in (
        "lead_enrichment_results",
        "lead_enrichment_field_candidates",
        "lead_cleanup_runs",
        "lead_cleanup_suggestions",
        "customer_vehicle_intents",
        "customer_followups",
    ):
        assert table_name in table_names


def test_phase3_models_keep_staging_and_core_boundaries_explicit() -> None:
    enrichment_columns = set(Base.metadata.tables["lead_enrichment_results"].columns.keys())
    field_candidate_columns = set(Base.metadata.tables["lead_enrichment_field_candidates"].columns.keys())
    cleanup_suggestion_columns = set(Base.metadata.tables["lead_cleanup_suggestions"].columns.keys())
    customer_columns = set(Base.metadata.tables["customers"].columns.keys())

    assert "customer_id" not in enrichment_columns
    assert "customer_id" not in field_candidate_columns
    assert "customer_id" not in cleanup_suggestion_columns
    assert "vehicle_intents_json" not in customer_columns
    assert "followups_json" not in customer_columns
    assert "customer_id" in set(Base.metadata.tables["customer_vehicle_intents"].columns.keys())
    assert "customer_id" in set(Base.metadata.tables["customer_followups"].columns.keys())


def test_phase3_foreign_key_contracts_are_explicit() -> None:
    expected_fk_targets = {
        "lead_enrichment_results": {"staging_leads.id", "agent_task_runs.id"},
        "lead_enrichment_field_candidates": {"lead_enrichment_results.id", "staging_leads.id"},
        "lead_cleanup_runs": {"llm_prompt_templates.id"},
        "lead_cleanup_suggestions": {"lead_cleanup_runs.id", "staging_leads.id"},
        "customer_vehicle_intents": {"customers.id"},
        "customer_followups": {"customers.id"},
    }

    for table_name, expected_targets in expected_fk_targets.items():
        actual_targets = {
            f"{fk.column.table.name}.{fk.column.name}"
            for column in Base.metadata.tables[table_name].columns
            for fk in column.foreign_keys
        }
        assert expected_targets.issubset(actual_targets), table_name


def test_phase3_enums_keep_frozen_business_values() -> None:
    assert {item.value for item in LeadEnrichmentType} == {"ai_deep_research", "manual_supplement"}
    assert {item.value for item in LeadEnrichmentResultStatus} == {
        "pending",
        "running",
        "succeeded",
        "failed",
        "cancelled",
    }
    assert {item.value for item in LeadEnrichmentFieldSourceType} == {
        "ai_public_source",
        "manual_public_info",
        "manual_customer_reply",
        "manual_business_note",
        "unknown",
    }
    assert {item.value for item in LeadEnrichmentFieldReviewStatus} == {
        "pending",
        "accepted",
        "rejected",
        "needs_review",
    }
    assert {item.value for item in LeadCleanupRunStatus} == {"pending", "running", "succeeded", "failed", "cancelled"}
    assert {item.value for item in LeadCleanupSuggestionType} == {
        "strong_duplicate",
        "possible_duplicate",
        "merge_contact_method",
        "merge_source_evidence",
        "restore_from_watch",
        "confirm_invalid",
        "mark_abandoned",
        "needs_manual_review",
    }
    assert {item.value for item in LeadCleanupSuggestionReviewStatus} == {"pending", "approved", "rejected", "executed"}
    assert {item.value for item in CustomerVehicleIntentSourceType} == {
        "manual_customer_reply",
        "manual_business_note",
        "ai_enrichment_accepted",
        "imported",
        "unknown",
    }
    assert {item.value for item in CustomerVehicleIntentStatus} == {
        "active",
        "pending_confirmation",
        "fulfilled",
        "archived",
    }
    assert {item.value for item in CustomerFollowupTeam} == {
        "customer_service",
        "sales",
        "export",
        "compliance",
        "operations",
    }
    assert {item.value for item in CustomerFollowupType} == {
        "manual_call",
        "manual_message",
        "email",
        "customer_reply",
        "internal_note",
        "compliance_review",
    }


def test_phase3_core_tables_can_compile_minimal_postgresql_sql() -> None:
    statements = [
        insert(LeadEnrichmentResult).values(
            staging_lead_id="11111111-1111-1111-1111-111111111111",
            enrichment_type=LeadEnrichmentType.AI_DEEP_RESEARCH,
            triggered_by="operator-a",
            status=LeadEnrichmentResultStatus.PENDING,
            input_snapshot_json={},
            evidence_links=[],
            missing_fields=[],
        ),
        insert(LeadEnrichmentFieldCandidate).values(
            enrichment_result_id="11111111-1111-1111-1111-111111111111",
            staging_lead_id="22222222-2222-2222-2222-222222222222",
            field_name="city",
            candidate_value="Moscow",
            source_type=LeadEnrichmentFieldSourceType.AI_PUBLIC_SOURCE,
            evidence_note="公开来源证据。",
            review_status=LeadEnrichmentFieldReviewStatus.PENDING,
        ),
        insert(LeadCleanupRun).values(
            trigger_source="scheduled_agent",
            status=LeadCleanupRunStatus.PENDING,
            input_filter_json={},
        ),
        insert(LeadCleanupSuggestion).values(
            cleanup_run_id="11111111-1111-1111-1111-111111111111",
            staging_lead_id="22222222-2222-2222-2222-222222222222",
            suggestion_type=LeadCleanupSuggestionType.NEEDS_MANUAL_REVIEW,
            reason="需要人工复核。",
            evidence_json={},
            recommended_action="人工复核。",
            review_status=LeadCleanupSuggestionReviewStatus.PENDING,
        ),
        insert(CustomerVehicleIntent).values(
            customer_id="11111111-1111-1111-1111-111111111111",
            source_type=CustomerVehicleIntentSourceType.MANUAL_CUSTOMER_REPLY,
            status=CustomerVehicleIntentStatus.ACTIVE,
            created_by="sales-a",
        ),
        insert(CustomerFollowup).values(
            customer_id="11111111-1111-1111-1111-111111111111",
            owner_id="sales-a",
            team=CustomerFollowupTeam.SALES,
            followup_type=CustomerFollowupType.MANUAL_CALL,
            content="人工跟进记录。",
            triggered_dnc=False,
            triggered_compliance_review=False,
            created_by="sales-a",
        ),
        select(CustomerFollowup).where(CustomerFollowup.team == CustomerFollowupTeam.SALES),
    ]

    for statement in statements:
        assert str(statement.compile(dialect=postgresql.dialect()))
