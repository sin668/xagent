import pytest
from pydantic import ValidationError

from app.graphs.lead_grading import (
    LEAD_GRADING_NODE_SEQUENCE,
    LeadGradingGraphRunner,
    LeadGradingGraphState,
)
from app.schemas.lead_grading import LeadGradingAgentOutput


BASE_EXTRACTED_LEAD = {
    "source_url": "https://autocity.example",
    "company_name": {"field_name": "company_name", "value": "Auto City Dubai", "evidence": {"reference": "source_content", "quote": "Auto City Dubai exports vehicles."}},
    "email": {"field_name": "email", "value": "sales@autocity.example", "evidence": {"reference": "source_content", "quote": "Contact: sales@autocity.example"}},
    "phone": {"field_name": "phone", "value": "+971 50 123 4567", "evidence": {"reference": "source_content", "quote": "Contact: +971 50 123 4567"}},
    "country": {"field_name": "country", "value": "United Arab Emirates", "evidence": {"reference": "source_content", "quote": "Located in Dubai, United Arab Emirates."}},
    "city": {"field_name": "city", "value": "Dubai", "evidence": {"reference": "source_content", "quote": "Located in Dubai."}},
    "vehicle_interest": {"field_name": "vehicle_interest", "value": "Toyota Land Cruiser", "evidence": {"reference": "source_content", "quote": "Toyota Land Cruiser inventory."}},
    "export_intent": {"field_name": "export_intent", "value": "arrange export documentation and shipping", "evidence": {"reference": "source_content", "quote": "arrange export documentation and shipping"}},
    "website": {"field_name": "website", "value": "https://autocity.example", "evidence": {"reference": "source_content", "quote": "Website: https://autocity.example"}},
}


def test_lead_grading_graph_declares_required_node_sequence() -> None:
    assert LEAD_GRADING_NODE_SEQUENCE == (
        "load_extracted_lead",
        "score_lead_signals",
        "apply_hard_rules",
        "explain_grade_delta",
        "output_shadow_grading",
    )


def test_lead_grading_graph_outputs_grade_status_reason_and_rules_without_customer_promotion() -> None:
    runner = LeadGradingGraphRunner()
    state = LeadGradingGraphState(
        grading_run_id="33333333-3333-3333-3333-333333333333",
        extracted_lead=BASE_EXTRACTED_LEAD,
        agent_mode="shadow",
        existing_grade="B",
    )

    result = runner.run(state)

    assert result.output.schema_version == "phase4.agent.lead_grading.v1"
    assert result.output.grading_run_id == "33333333-3333-3333-3333-333333333333"
    assert result.output.agent_mode == "shadow"
    assert result.executed_nodes == list(LEAD_GRADING_NODE_SEQUENCE)

    suggestion = result.output.suggestions[0]
    assert suggestion.recommended_grade == "A"
    assert suggestion.status_route == "ready_for_manual_review"
    assert suggestion.confidence_score == 0.95
    assert "联系方式完整" in suggestion.reasons
    assert "出口意向明确" in suggestion.reasons
    assert "grade_delta_from_existing" in suggestion.explanations
    assert suggestion.triggered_rules == [
        "complete_contact",
        "export_intent_present",
        "vehicle_interest_present",
        "company_website_present",
    ]
    assert suggestion.auto_promote_customer is False

    assert result.output.audit["writes_core_tables"] is False
    assert result.output.audit["output_table"] == "shadow_lead_grading_suggestions"
    assert "customers" not in result.output.audit.get("written_tables", [])


@pytest.mark.parametrize(
    ("risk_flags", "expected_grade", "expected_route", "expected_rule"),
    [
        (["forbidden_source"], "Invalid", "risk_blocked", "forbidden_source"),
        (["high_risk_source"], "Watch", "needs_manual_risk_review", "high_risk_source"),
        (["do_not_contact"], "Invalid", "risk_blocked", "do_not_contact"),
        (["c_level_compliance_review"], "C", "needs_compliance_review", "c_level_compliance_review"),
        (["existing_invalid"], "Invalid", "risk_blocked", "existing_invalid"),
        (["existing_watch"], "Watch", "needs_manual_risk_review", "existing_watch"),
    ],
)
def test_lead_grading_hard_rules_override_signal_score(
    risk_flags: list[str],
    expected_grade: str,
    expected_route: str,
    expected_rule: str,
) -> None:
    runner = LeadGradingGraphRunner()
    state = LeadGradingGraphState(
        grading_run_id="33333333-3333-3333-3333-333333333333",
        extracted_lead=BASE_EXTRACTED_LEAD,
        agent_mode="shadow",
        risk_flags=risk_flags,
    )

    result = runner.run(state)
    suggestion = result.output.suggestions[0]

    assert suggestion.recommended_grade == expected_grade
    assert suggestion.status_route == expected_route
    assert expected_rule in suggestion.triggered_rules
    assert suggestion.auto_promote_customer is False
    assert result.output.audit["hard_rules_applied"] is True


def test_lead_grading_missing_evidence_routes_to_c_with_compliance_review() -> None:
    extracted_lead = {
        **BASE_EXTRACTED_LEAD,
        "email": {"field_name": "email", "value": None, "missing_reason": "源文本未提供 email。"},
        "phone": {"field_name": "phone", "value": None, "missing_reason": "源文本未提供 phone。"},
    }
    runner = LeadGradingGraphRunner()
    state = LeadGradingGraphState(
        grading_run_id="33333333-3333-3333-3333-333333333333",
        extracted_lead=extracted_lead,
        agent_mode="shadow",
    )

    result = runner.run(state)
    suggestion = result.output.suggestions[0]

    assert suggestion.recommended_grade == "C"
    assert suggestion.status_route == "needs_compliance_review"
    assert "contact_missing" in suggestion.triggered_rules
    assert "联系方式缺失" in suggestion.reasons


def test_lead_grading_accepts_active_mode() -> None:
    runner = LeadGradingGraphRunner()

    result = runner.run(
        LeadGradingGraphState(
            grading_run_id="33333333-3333-3333-3333-333333333333",
            extracted_lead=BASE_EXTRACTED_LEAD,
            agent_mode="active",
        )
    )

    assert result.output.agent_mode == "active"


def test_lead_grading_output_schema_rejects_auto_customer_promotion() -> None:
    with pytest.raises(ValidationError) as exc_info:
        LeadGradingAgentOutput.model_validate(
            {
                "schema_version": "phase4.agent.lead_grading.v1",
                "grading_run_id": "33333333-3333-3333-3333-333333333333",
                "agent_mode": "shadow",
                "suggestions": [
                    {
                        "source_url": "https://invalid.example",
                        "recommended_grade": "A",
                        "status_route": "ready_for_manual_review",
                        "confidence_score": 0.9,
                        "reasons": ["测试"],
                        "triggered_rules": ["complete_contact"],
                        "explanations": {"grade_delta_from_existing": "测试"},
                        "auto_promote_customer": True,
                    }
                ],
                "audit": {"writes_core_tables": False},
            }
        )

    assert "Lead Grading 不允许自动晋级客户" in str(exc_info.value)
