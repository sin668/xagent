from pathlib import Path

from app.graphs import build_placeholder_graph


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_agent_project_declares_langgraph_and_test_dependencies() -> None:
    pyproject = (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert 'name = "vehicle-leads-agents"' in pyproject
    assert "langgraph" in pyproject.lower()
    assert "pytest" in pyproject.lower()
    assert 'include = ["app*"]' in pyproject


def test_agent_project_has_required_package_boundaries() -> None:
    for relative_path in (
        "app/__init__.py",
        "app/graphs/__init__.py",
        "app/schemas/__init__.py",
        "app/tools/__init__.py",
        "app/adapters/__init__.py",
        "tests/__init__.py",
    ):
        assert (PROJECT_ROOT / relative_path).exists()


def test_placeholder_graph_contract_is_explicit_and_side_effect_free() -> None:
    graph = build_placeholder_graph()

    assert graph["name"] == "phase3_langgraph_placeholder"
    assert graph["runtime"] == "langgraph"
    assert graph["implemented"] is False
    assert graph["writes_core_tables"] is False
    assert graph["allowed_outputs"] == ["lead_enrichment_field_candidates", "lead_cleanup_suggestions"]
    assert "no_auto_outreach" in graph["compliance_guards"]
    assert "no_direct_core_writes" in graph["compliance_guards"]
