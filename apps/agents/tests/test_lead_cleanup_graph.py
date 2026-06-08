from uuid import UUID

import pytest

from app.graphs.lead_cleanup import (
    LEAD_CLEANUP_NODE_SEQUENCE,
    LeadCleanupGraphRunner,
    LeadCleanupGraphState,
)


def test_lead_cleanup_graph_declares_required_node_sequence() -> None:
    assert LEAD_CLEANUP_NODE_SEQUENCE == (
        "load_watch_invalid",
        "detect_duplicates",
        "classify_invalid_reason",
        "find_restore_candidates",
        "review_cleanup_with_llm",
        "write_cleanup_suggestions",
        "wait_human_review",
    )


def test_lead_cleanup_graph_runner_uses_compiled_langgraph() -> None:
    runner = LeadCleanupGraphRunner()

    assert runner.compiled_graph is not None


def test_lead_cleanup_graph_generates_duplicate_suggestions_without_core_writes() -> None:
    runner = LeadCleanupGraphRunner()
    state = LeadCleanupGraphState(
        cleanup_run_id="11111111-1111-1111-1111-111111111111",
        leads=[
            {
                "staging_lead_id": "22222222-2222-2222-2222-222222222222",
                "customer_name": "Auto City",
                "city": "Moscow",
                "recommended_grade": "Watch",
                "contacts_json": [{"type": "email", "value": "sales@example.ru"}],
            },
            {
                "staging_lead_id": "33333333-3333-3333-3333-333333333333",
                "customer_name": " Auto City ",
                "city": "Moscow",
                "recommended_grade": "Invalid",
                "contacts_json": [{"type": "email", "value": "sales@example.ru"}],
                "invalid_reason": "重复线索。",
            },
        ],
    )

    result = runner.run(state)

    assert result.executed_nodes == list(LEAD_CLEANUP_NODE_SEQUENCE)
    assert result.output.schema_version == "phase3.agent.lead_cleanup.v1"
    assert isinstance(result.output.cleanup_run_id, UUID)
    duplicate = next(item for item in result.output.suggestions if item.suggestion_type == "strong_duplicate")
    assert duplicate.staging_lead_id == UUID("33333333-3333-3333-3333-333333333333")
    assert duplicate.target_lead_id == UUID("22222222-2222-2222-2222-222222222222")
    assert duplicate.review_status == "pending"
    assert duplicate.evidence_json["matched_fields"] == ["customer_name", "contact"]
    assert result.output.audit["writes_core_tables"] is False
    assert result.output.audit["output_table"] == "lead_cleanup_suggestions"
    assert result.output.audit["auto_execute_cleanup"] is False
    assert result.output.audit["auto_delete_leads"] is False
    assert result.output.audit["auto_restore_invalid"] is False


def test_lead_cleanup_graph_classifies_invalid_reason_as_pending_suggestion() -> None:
    runner = LeadCleanupGraphRunner()
    state = LeadCleanupGraphState(
        cleanup_run_id="11111111-1111-1111-1111-111111111111",
        leads=[
            {
                "staging_lead_id": "44444444-4444-4444-4444-444444444444",
                "customer_name": "Parts Service",
                "city": "Kazan",
                "recommended_grade": "Invalid",
                "contacts_json": [],
                "invalid_reason": "仅销售配件，不是整车销售客户。",
            }
        ],
    )

    result = runner.run(state)

    suggestion = next(item for item in result.output.suggestions if item.suggestion_type == "confirm_invalid")
    assert suggestion.review_status == "pending"
    assert suggestion.evidence_json["invalid_reason"] == "仅销售配件，不是整车销售客户。"
    assert suggestion.recommended_action == "人工确认无效原因后保留清洗结论"


def test_lead_cleanup_graph_finds_restore_candidates_but_does_not_restore() -> None:
    runner = LeadCleanupGraphRunner()
    state = LeadCleanupGraphState(
        cleanup_run_id="11111111-1111-1111-1111-111111111111",
        leads=[
            {
                "staging_lead_id": "55555555-5555-5555-5555-555555555555",
                "customer_name": "Siberia Auto",
                "city": "Novosibirsk",
                "recommended_grade": "Watch",
                "contacts_json": [{"type": "telegram", "value": "@siberia_auto"}],
                "source_evidence": "公开页面补充了进口二手车销售证据。",
                "restore_signal": True,
            }
        ],
    )

    result = runner.run(state)

    suggestion = next(item for item in result.output.suggestions if item.suggestion_type == "restore_from_watch")
    assert suggestion.review_status == "pending"
    assert suggestion.evidence_json["restore_signal"] is True
    assert result.output.audit["auto_restore_invalid"] is False


def test_lead_cleanup_graph_rejects_automatic_cleanup_actions() -> None:
    runner = LeadCleanupGraphRunner()
    state = LeadCleanupGraphState(
        cleanup_run_id="11111111-1111-1111-1111-111111111111",
        leads=[],
        requested_actions=["auto_execute_cleanup", "delete_leads", "restore_invalid"],
    )

    with pytest.raises(ValueError, match="不允许自动执行、删除线索或自动恢复 Invalid"):
        runner.run(state)
