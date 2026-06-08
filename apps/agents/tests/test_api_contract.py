from uuid import UUID

import pytest
from pydantic import ValidationError

from app.adapters.api_contract import ApiContractBoundary
from app.schemas.deep_enrichment import DeepEnrichmentAgentOutput, FieldCandidateOutput
from app.schemas.lead_cleanup import CleanupAgentOutput, CleanupSuggestionOutput


def test_deep_enrichment_output_maps_to_field_candidate_contract() -> None:
    output = DeepEnrichmentAgentOutput(
        schema_version="phase3.agent.deep_enrichment.v1",
        agent_run_id="11111111-1111-1111-1111-111111111111",
        staging_lead_id="22222222-2222-2222-2222-222222222222",
        field_candidates=[
            FieldCandidateOutput(
                field_name="contacts_json",
                candidate_value=[{"type": "email", "value": "sales@example.ru"}],
                source_type="ai_public_source",
                source_url="https://dealer.example.ru/contact",
                evidence_note="公开官网联系方式页面展示邮箱。",
                confidence_score=0.82,
            )
        ],
        missing_fields=["vehicle_intents"],
        recommended_next_action="manual_review",
        audit={"prompt_version": "v1", "model": "deepseek-chat"},
    )

    candidate = output.field_candidates[0]
    assert output.schema_version == "phase3.agent.deep_enrichment.v1"
    assert isinstance(output.agent_run_id, UUID)
    assert isinstance(output.staging_lead_id, UUID)
    assert candidate.review_status == "pending"
    assert candidate.field_name == "contacts_json"
    assert candidate.source_type == "ai_public_source"
    assert "accepted_by" not in candidate.model_dump()
    assert "customer_id" not in candidate.model_dump()


def test_cleanup_output_maps_to_cleanup_suggestion_contract() -> None:
    output = CleanupAgentOutput(
        schema_version="phase3.agent.lead_cleanup.v1",
        cleanup_run_id="33333333-3333-3333-3333-333333333333",
        suggestions=[
            CleanupSuggestionOutput(
                staging_lead_id="44444444-4444-4444-4444-444444444444",
                suggestion_type="possible_duplicate",
                target_lead_id="55555555-5555-5555-5555-555555555555",
                confidence_score=0.76,
                reason="客户名称和官网域名相似，需人工确认。",
                evidence_json={"matched_fields": ["customer_name", "source_domain"]},
                recommended_action="人工确认是否归并。",
            )
        ],
        blocked_items=[],
        audit={"prompt_version": "v1", "model": "deepseek-chat"},
    )

    suggestion = output.suggestions[0]
    assert output.schema_version == "phase3.agent.lead_cleanup.v1"
    assert isinstance(output.cleanup_run_id, UUID)
    assert suggestion.review_status == "pending"
    assert suggestion.suggestion_type == "possible_duplicate"
    assert "reviewer_id" not in suggestion.model_dump()
    assert "executed_by" not in suggestion.model_dump()
    assert "customer_id" not in suggestion.model_dump()


def test_agent_contract_rejects_auto_core_actions_and_outreach_flags() -> None:
    forbidden_payloads = [
        {
            "schema_version": "phase3.agent.deep_enrichment.v1",
            "agent_run_id": "11111111-1111-1111-1111-111111111111",
            "staging_lead_id": "22222222-2222-2222-2222-222222222222",
            "field_candidates": [],
            "auto_promote_customer": True,
            "audit": {"prompt_version": "v1"},
        },
        {
            "schema_version": "phase3.agent.lead_cleanup.v1",
            "cleanup_run_id": "33333333-3333-3333-3333-333333333333",
            "suggestions": [],
            "auto_execute_cleanup": True,
            "audit": {"prompt_version": "v1"},
        },
        {
            "schema_version": "phase3.agent.lead_cleanup.v1",
            "cleanup_run_id": "33333333-3333-3333-3333-333333333333",
            "suggestions": [],
            "send_outreach_message": True,
            "audit": {"prompt_version": "v1"},
        },
    ]

    for payload in forbidden_payloads:
        model = DeepEnrichmentAgentOutput if "agent_run_id" in payload else CleanupAgentOutput
        with pytest.raises(ValidationError):
            model(**payload)


def test_api_contract_boundary_allows_only_staging_and_shadow_outputs() -> None:
    boundary = ApiContractBoundary()

    assert boundary.allowed_output_tables == (
        "lead_enrichment_field_candidates",
        "lead_cleanup_suggestions",
        "shadow_source_candidates",
        "shadow_staging_lead_candidates",
        "shadow_lead_grading_suggestions",
    )
    assert boundary.forbidden_core_tables == (
        "customers",
        "lead_sources",
        "contact_methods",
        "lead_source_candidates",
        "staging_leads",
    )
    assert boundary.validate_output_table("lead_cleanup_suggestions") == "lead_cleanup_suggestions"
    assert boundary.validate_output_table("shadow_source_candidates") == "shadow_source_candidates"
    assert boundary.validate_output_table("shadow_staging_lead_candidates") == "shadow_staging_lead_candidates"
    assert boundary.validate_output_table("shadow_lead_grading_suggestions") == "shadow_lead_grading_suggestions"

    with pytest.raises(ValueError, match="Agent 项目不得直接写 core 表"):
        boundary.validate_output_table("customers")

    with pytest.raises(ValueError, match="Agent 项目不得直接写 core 表"):
        boundary.validate_output_table("lead_source_candidates")

    with pytest.raises(ValueError, match="Agent 项目不得直接写 core 表"):
        boundary.validate_output_table("staging_leads")

    with pytest.raises(ValueError, match="Agent 项目仅允许输出结构化 staging 候选"):
        boundary.validate_output_table("outreach_records")
