from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from langgraph.graph import END, StateGraph

from app.graphs.lead_extraction import LeadExtractionGraphRunner, LeadExtractionGraphState
from app.graphs.lead_grading import LeadGradingGraphRunner, LeadGradingGraphState
from app.schemas.lead_extraction import LeadExtractionAgentOutput
from app.schemas.lead_extraction_grading import (
    LeadExtractionGradingAgentOutput,
    LeadExtractionGradingHardRuleSummary,
)
from app.schemas.lead_grading import LeadGradingAgentOutput
from app.services.agent_logging import run_logged_node
from app.validators.lead_extraction_grading import LeadExtractionGradingValidator


LEAD_EXTRACTION_GRADING_STUDIO_NODE_SEQUENCE = (
    "run_lead_extraction_subgraph",
    "run_lead_grading_subgraph",
    "validate_combined_result",
)


@dataclass(slots=True)
class LeadExtractionGradingGraphState:
    combined_run_id: str
    extraction_run_id: str
    grading_run_id: str
    source_url: str
    source_content: str
    agent_mode: str = "shadow"
    risk_flags: list[str] = field(default_factory=list)
    existing_grade: str | None = None
    expected_contacts: dict[str, Any] = field(default_factory=dict)
    extraction_output: LeadExtractionAgentOutput | None = None
    grading_output: LeadGradingAgentOutput | None = None
    audit: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class LeadExtractionGradingGraphResult:
    output: LeadExtractionGradingAgentOutput
    executed_nodes: list[str]


class LeadExtractionGradingGraphRunner:
    def run(self, state: LeadExtractionGradingGraphState) -> LeadExtractionGradingGraphResult:
        if state.agent_mode != "shadow":
            raise ValueError("Lead Extraction/Grading 第四阶段只允许 shadow_run。")

        extraction_result = LeadExtractionGraphRunner().run(
            LeadExtractionGraphState(
                extraction_run_id=state.extraction_run_id,
                source_url=state.source_url,
                source_content=state.source_content,
                agent_mode="shadow",
            )
        )
        state.extraction_output = extraction_result.output
        candidate = extraction_result.output.candidates[0] if extraction_result.output.candidates else None
        if candidate is None:
            raise ValueError("Lead Extraction/Grading 未生成可分级的抽取候选。")

        grading_result = LeadGradingGraphRunner().run(
            LeadGradingGraphState(
                grading_run_id=state.grading_run_id,
                extracted_lead=candidate,
                agent_mode="shadow",
                risk_flags=state.risk_flags,
                existing_grade=state.existing_grade,
            )
        )
        state.grading_output = grading_result.output

        suggestion = grading_result.output.suggestions[0] if grading_result.output.suggestions else None
        hard_rule_summary = LeadExtractionGradingHardRuleSummary(
            hard_rules_applied=bool(grading_result.output.audit.get("hard_rules_applied")),
            triggered_rules=list(suggestion.triggered_rules if suggestion else []),
            risk_flags=list(state.risk_flags),
        )
        validation_summary = LeadExtractionGradingValidator().validate(
            extraction=extraction_result.output,
            grading=grading_result.output,
            source_content=state.source_content,
            risk_flags=state.risk_flags,
            expected_contacts=state.expected_contacts,
        )
        grade_delta_explanations = dict(suggestion.explanations if suggestion else {})
        executed_nodes = [
            *[f"lead_extraction.{node}" for node in extraction_result.executed_nodes],
            *[f"lead_grading.{node}" for node in grading_result.executed_nodes],
        ]
        source_urls = self.unique(
            [
                *list(extraction_result.output.audit.get("source_urls") or []),
                *list(grading_result.output.audit.get("source_urls") or []),
                state.source_url,
            ]
        )
        audit = {
            "writes_core_tables": False,
            "executed_nodes": executed_nodes,
            "failed_node": None,
            "risk_flags": list(state.risk_flags),
            "source_urls": source_urls,
            "written_tables": self.unique(
                [
                    *list(extraction_result.output.audit.get("written_tables") or []),
                    *list(grading_result.output.audit.get("written_tables") or []),
                ]
            ),
            "hard_rules_applied": hard_rule_summary.hard_rules_applied,
            "validation_summary": validation_summary,
        }
        output = LeadExtractionGradingAgentOutput(
            schema_version="phase4.agent.lead_extraction_grading.v1",
            combined_run_id=state.combined_run_id,
            agent_mode="shadow",
            extraction=extraction_result.output,
            grading=grading_result.output,
            hard_rule_summary=hard_rule_summary,
            validation_summary=validation_summary,
            grade_delta_explanations=grade_delta_explanations,
            audit=audit,
        )
        return LeadExtractionGradingGraphResult(output=output, executed_nodes=executed_nodes)

    @staticmethod
    def unique(values: list[str]) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for item in values:
            value = str(item)
            if value in seen:
                continue
            seen.add(value)
            result.append(value)
        return result


class LeadExtractionGradingStudioGraphBuilder:
    agent_type = "lead_extraction_grading"

    def __init__(self) -> None:
        self.compiled_graph = self._build_graph()

    def _build_graph(self):
        graph = StateGraph(LeadExtractionGradingGraphState)
        for node_name in LEAD_EXTRACTION_GRADING_STUDIO_NODE_SEQUENCE:
            graph.add_node(
                node_name,
                lambda state, node_name=node_name: run_logged_node(
                    agent_type=self.agent_type,
                    node_name=node_name,
                    func=getattr(self, node_name),
                    state=state,
                ),
            )
        graph.set_entry_point(LEAD_EXTRACTION_GRADING_STUDIO_NODE_SEQUENCE[0])
        graph.add_edge("run_lead_extraction_subgraph", "run_lead_grading_subgraph")
        graph.add_edge("run_lead_grading_subgraph", "validate_combined_result")
        graph.add_edge("validate_combined_result", END)
        return graph.compile()

    def run_lead_extraction_subgraph(self, state: LeadExtractionGradingGraphState) -> LeadExtractionGradingGraphState:
        if state.agent_mode != "shadow":
            raise ValueError("Lead Extraction/Grading 第四阶段只允许 shadow_run。")
        extraction_result = LeadExtractionGraphRunner().run(
            LeadExtractionGraphState(
                extraction_run_id=state.extraction_run_id,
                source_url=state.source_url,
                source_content=state.source_content,
                agent_mode="shadow",
            )
        )
        state.extraction_output = extraction_result.output
        state.audit.setdefault("executed_nodes", []).extend(
            [f"lead_extraction.{node}" for node in extraction_result.executed_nodes]
        )
        return state

    def run_lead_grading_subgraph(self, state: LeadExtractionGradingGraphState) -> LeadExtractionGradingGraphState:
        if state.extraction_output is None or not state.extraction_output.candidates:
            raise ValueError("Lead Extraction/Grading 未生成可分级的抽取候选。")
        grading_result = LeadGradingGraphRunner().run(
            LeadGradingGraphState(
                grading_run_id=state.grading_run_id,
                extracted_lead=state.extraction_output.candidates[0],
                agent_mode="shadow",
                risk_flags=state.risk_flags,
                existing_grade=state.existing_grade,
            )
        )
        state.grading_output = grading_result.output
        state.audit.setdefault("executed_nodes", []).extend(
            [f"lead_grading.{node}" for node in grading_result.executed_nodes]
        )
        return state

    def validate_combined_result(self, state: LeadExtractionGradingGraphState) -> LeadExtractionGradingGraphState:
        if state.extraction_output is None or state.grading_output is None:
            raise ValueError("Lead Extraction/Grading 缺少抽取或分级输出。")
        state.audit["validation_summary"] = LeadExtractionGradingValidator().validate(
            extraction=state.extraction_output,
            grading=state.grading_output,
            source_content=state.source_content,
            risk_flags=state.risk_flags,
            expected_contacts=state.expected_contacts,
        )
        state.audit["writes_core_tables"] = False
        return state
