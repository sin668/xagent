from uuid import UUID

from app.runtime.mock_runtime import MockAgentRuntime


def test_mock_runtime_runs_deep_enrichment_graph_and_returns_schema_output() -> None:
    runtime = MockAgentRuntime()

    output = runtime.run_deep_enrichment(
        agent_run_id="11111111-1111-1111-1111-111111111111",
        staging_lead_id="22222222-2222-2222-2222-222222222222",
        lead_snapshot={
            "customer_name": "Ru Auto City",
            "country": "Russia",
            "city": "Moscow",
            "contacts_json": [],
            "source_evidence": "公开官网展示车商名称。",
        },
        missing_fields=["contacts_json"],
    )

    assert output["schema_version"] == "phase3.agent.deep_enrichment.v1"
    assert UUID(output["agent_run_id"])
    assert output["audit"]["writes_core_tables"] is False
    assert output["audit"]["output_table"] == "lead_enrichment_field_candidates"


def test_mock_runtime_runs_lead_cleanup_graph_and_returns_schema_output() -> None:
    runtime = MockAgentRuntime()

    output = runtime.run_lead_cleanup(
        cleanup_run_id="33333333-3333-3333-3333-333333333333",
        leads=[
            {
                "staging_lead_id": "44444444-4444-4444-4444-444444444444",
                "customer_name": "Ru Auto City",
                "city": "Moscow",
                "recommended_grade": "Invalid",
                "invalid_reason": "非车辆销售客户。",
            }
        ],
    )

    assert output["schema_version"] == "phase3.agent.lead_cleanup.v1"
    assert UUID(output["cleanup_run_id"])
    assert output["audit"]["writes_core_tables"] is False
    assert output["audit"]["output_table"] == "lead_cleanup_suggestions"
    assert output["suggestions"][0]["review_status"] == "pending"
