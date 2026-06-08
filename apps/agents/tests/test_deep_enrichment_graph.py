from uuid import UUID

from app.graphs.deep_enrichment import (
    DEEP_ENRICHMENT_NODE_SEQUENCE,
    DeepEnrichmentGraphRunner,
    DeepEnrichmentGraphState,
)


class MockSearchTool:
    def search(self, keywords):
        return [
            {
                "url": "https://dealer.example.ru/contact",
                "title": "Auto City contact",
                "text": "Auto City Moscow Email sales@example.ru. Used cars from China.",
            }
        ]


class MockLLMExtractor:
    def extract(self, state):
        return [
            {
                "field_name": "contacts_json",
                "candidate_value": [{"type": "email", "value": "sales@example.ru"}],
                "source_type": "ai_public_source",
                "source_url": "https://dealer.example.ru/contact",
                "evidence_note": "公开官网联系方式页面展示邮箱。",
                "confidence_score": 0.84,
            },
            {
                "field_name": "vehicle_intents",
                "candidate_value": [],
                "source_type": "ai_public_source",
                "source_url": "https://dealer.example.ru/contact",
                "evidence_note": "公开页面未展示明确意向车型，按空数组保留缺失。",
                "confidence_score": 0.3,
            },
            {
                "field_name": "business_status",
                "candidate_value": "Unknown",
                "source_type": "ai_public_source",
                "source_url": "https://dealer.example.ru/contact",
                "evidence_note": "公开页面未展示经营状况，按 Unknown 保留缺失。",
                "confidence_score": 0.2,
            },
        ]


def test_deep_enrichment_graph_declares_required_node_sequence() -> None:
    assert DEEP_ENRICHMENT_NODE_SEQUENCE == (
        "load_lead",
        "build_keywords",
        "search_public_sources",
        "read_public_pages",
        "extract_candidates",
        "validate_evidence",
        "write_enrichment_candidates",
        "recommend_action",
    )


def test_deep_enrichment_graph_runner_uses_compiled_langgraph() -> None:
    runner = DeepEnrichmentGraphRunner(search_tool=MockSearchTool(), llm_extractor=MockLLMExtractor())

    assert runner.compiled_graph is not None


def test_deep_enrichment_graph_runs_with_mock_search_and_llm_without_core_writes() -> None:
    runner = DeepEnrichmentGraphRunner(search_tool=MockSearchTool(), llm_extractor=MockLLMExtractor())
    state = DeepEnrichmentGraphState(
        agent_run_id="11111111-1111-1111-1111-111111111111",
        staging_lead_id="22222222-2222-2222-2222-222222222222",
        lead_snapshot={
            "customer_name": "Auto City",
            "country": "Russia",
            "city": "Moscow",
            "contacts_json": [],
            "source_evidence": "公开官网展示车商名称。",
        },
        missing_fields=["contacts_json", "vehicle_intents", "business_status"],
    )

    result = runner.run(state)

    assert result.output.schema_version == "phase3.agent.deep_enrichment.v1"
    assert isinstance(result.output.agent_run_id, UUID)
    assert isinstance(result.output.staging_lead_id, UUID)
    assert result.executed_nodes == list(DEEP_ENRICHMENT_NODE_SEQUENCE)
    assert result.output.recommended_next_action == "manual_review"
    assert result.output.missing_fields == ["vehicle_intents", "business_status"]
    assert len(result.output.field_candidates) == 3
    assert result.output.field_candidates[0].field_name == "contacts_json"
    assert result.output.field_candidates[1].candidate_value == []
    assert result.output.field_candidates[2].candidate_value == "Unknown"
    assert result.output.audit["writes_core_tables"] is False
    assert result.output.audit["output_table"] == "lead_enrichment_field_candidates"
    assert "customers" not in result.output.audit.get("written_tables", [])
    assert result.output.audit["source_urls"] == ["https://dealer.example.ru/contact"]


def test_deep_enrichment_graph_blocks_forbidden_search_actions() -> None:
    runner = DeepEnrichmentGraphRunner(search_tool=MockSearchTool(), llm_extractor=MockLLMExtractor())
    state = DeepEnrichmentGraphState(
        agent_run_id="11111111-1111-1111-1111-111111111111",
        staging_lead_id="22222222-2222-2222-2222-222222222222",
        lead_snapshot={"customer_name": "Auto City", "city": "Moscow"},
        missing_fields=["contacts_json"],
        requested_actions=["auto_dm", "friend_request"],
    )

    try:
        runner.run(state)
    except ValueError as exc:
        assert "不允许自动私信、加好友、登录采集或反爬规避" in str(exc)
    else:
        raise AssertionError("Deep Enrichment graph must reject forbidden search actions")
