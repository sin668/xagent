import importlib
import json
from pathlib import Path


def test_langgraph_studio_config_exposes_all_phase4_graphs() -> None:
    config_path = Path(__file__).resolve().parents[1] / "langgraph.json"

    assert config_path.exists()
    config = json.loads(config_path.read_text(encoding="utf-8"))

    assert config["dependencies"] == ["."]
    assert config["graphs"] == {
        "deep_enrichment": "app.studio.graphs:deep_enrichment_graph",
        "lead_cleanup": "app.studio.graphs:lead_cleanup_graph",
        "source_discovery": "app.studio.graphs:source_discovery_graph",
        "lead_extraction_grading": "app.studio.graphs:lead_extraction_grading_graph",
    }
    assert config["env"] == ".env"


def test_langgraph_studio_graph_targets_are_importable_compiled_graphs() -> None:
    config_path = Path(__file__).resolve().parents[1] / "langgraph.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))

    for graph_path in config["graphs"].values():
        module_name, attr_name = graph_path.split(":", maxsplit=1)
        module = importlib.import_module(module_name)
        graph = getattr(module, attr_name)

        assert hasattr(graph, "invoke")
        assert hasattr(graph, "get_graph")
