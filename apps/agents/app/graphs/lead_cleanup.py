from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from langgraph.graph import END, StateGraph

from app.adapters.api_contract import ApiContractBoundary
from app.schemas.lead_cleanup import CleanupAgentOutput, CleanupSuggestionOutput
from app.tools.duplicate_detector import DuplicateDetector


LEAD_CLEANUP_NODE_SEQUENCE = (
    "load_watch_invalid",
    "detect_duplicates",
    "classify_invalid_reason",
    "find_restore_candidates",
    "write_cleanup_suggestions",
    "wait_human_review",
)

FORBIDDEN_CLEANUP_ACTIONS = {"auto_execute_cleanup", "delete_leads", "restore_invalid"}


@dataclass(slots=True)
class LeadCleanupGraphState:
    cleanup_run_id: UUID | str
    leads: list[dict[str, Any]]
    requested_actions: list[str] = field(default_factory=list)
    target_leads: list[dict[str, Any]] = field(default_factory=list)
    raw_suggestions: list[dict[str, Any]] = field(default_factory=list)
    suggestions: list[CleanupSuggestionOutput] = field(default_factory=list)
    blocked_items: list[dict] = field(default_factory=list)
    audit: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class LeadCleanupGraphResult:
    output: CleanupAgentOutput
    executed_nodes: list[str]


class LeadCleanupGraphRunner:
    def __init__(
        self,
        *,
        duplicate_detector: DuplicateDetector | None = None,
        boundary: ApiContractBoundary | None = None,
    ) -> None:
        self.duplicate_detector = duplicate_detector or DuplicateDetector()
        self.boundary = boundary or ApiContractBoundary()
        self.executed_nodes: list[str] = []
        self.compiled_graph = self._build_graph()

    def _build_graph(self):
        graph = StateGraph(LeadCleanupGraphState)
        for node_name in LEAD_CLEANUP_NODE_SEQUENCE:
            graph.add_node(node_name, getattr(self, node_name))
        graph.set_entry_point(LEAD_CLEANUP_NODE_SEQUENCE[0])
        for index, node_name in enumerate(LEAD_CLEANUP_NODE_SEQUENCE):
            next_index = index + 1
            graph.add_edge(
                node_name,
                LEAD_CLEANUP_NODE_SEQUENCE[next_index] if next_index < len(LEAD_CLEANUP_NODE_SEQUENCE) else END,
            )
        return graph.compile()

    def mark(self, node_name: str) -> None:
        self.executed_nodes.append(node_name)

    def load_watch_invalid(self, state: LeadCleanupGraphState) -> LeadCleanupGraphState:
        self.mark("load_watch_invalid")
        if FORBIDDEN_CLEANUP_ACTIONS & set(state.requested_actions):
            raise ValueError("不允许自动执行、删除线索或自动恢复 Invalid")

        state.target_leads = [
            lead
            for lead in state.leads
            if str(lead.get("recommended_grade") or "").lower() in {"watch", "invalid"}
        ]
        state.audit.update(
            {
                "loaded_watch_invalid": len(state.target_leads),
                "auto_execute_cleanup": False,
                "auto_delete_leads": False,
                "auto_restore_invalid": False,
            }
        )
        return state

    def detect_duplicates(self, state: LeadCleanupGraphState) -> LeadCleanupGraphState:
        self.mark("detect_duplicates")
        state.raw_suggestions.extend(self.duplicate_detector.find_duplicates(state.target_leads))
        return state

    def classify_invalid_reason(self, state: LeadCleanupGraphState) -> LeadCleanupGraphState:
        self.mark("classify_invalid_reason")
        for lead in state.target_leads:
            if str(lead.get("recommended_grade") or "").lower() != "invalid":
                continue
            invalid_reason = str(lead.get("invalid_reason") or "Unknown")
            state.raw_suggestions.append(
                {
                    "staging_lead_id": lead.get("staging_lead_id"),
                    "suggestion_type": "confirm_invalid",
                    "target_lead_id": None,
                    "confidence_score": 0.8,
                    "reason": "线索当前为 Invalid，需要人工确认无效原因是否仍成立。",
                    "evidence_json": {
                        "invalid_reason": invalid_reason,
                        "customer_name": lead.get("customer_name") or "Unknown",
                    },
                    "recommended_action": "人工确认无效原因后保留清洗结论",
                }
            )
        return state

    def find_restore_candidates(self, state: LeadCleanupGraphState) -> LeadCleanupGraphState:
        self.mark("find_restore_candidates")
        for lead in state.target_leads:
            if str(lead.get("recommended_grade") or "").lower() != "watch":
                continue
            restore_signal = bool(lead.get("restore_signal") or lead.get("new_evidence"))
            if not restore_signal:
                continue
            state.raw_suggestions.append(
                {
                    "staging_lead_id": lead.get("staging_lead_id"),
                    "suggestion_type": "restore_from_watch",
                    "target_lead_id": None,
                    "confidence_score": 0.76,
                    "reason": "Watch 线索出现新的公开证据，建议人工复核是否恢复跟进。",
                    "evidence_json": {
                        "restore_signal": True,
                        "new_evidence": lead.get("new_evidence"),
                        "source_evidence": lead.get("source_evidence"),
                    },
                    "recommended_action": "人工复核新证据后决定是否恢复线索",
                }
            )
        return state

    def write_cleanup_suggestions(self, state: LeadCleanupGraphState) -> LeadCleanupGraphState:
        self.mark("write_cleanup_suggestions")
        output_table = self.boundary.validate_output_table("lead_cleanup_suggestions")
        state.suggestions = [CleanupSuggestionOutput(**item) for item in state.raw_suggestions]
        state.audit.update(
            {
                "writes_core_tables": False,
                "output_table": output_table,
                "written_tables": [output_table],
                "suggestion_count": len(state.suggestions),
            }
        )
        return state

    def wait_human_review(self, state: LeadCleanupGraphState) -> LeadCleanupGraphState:
        self.mark("wait_human_review")
        state.audit["wait_human_review"] = True
        state.audit["review_status"] = "pending"
        return state

    def run(self, state: LeadCleanupGraphState) -> LeadCleanupGraphResult:
        invoked_state = self.compiled_graph.invoke(state)
        state = self._state_from_graph_result(invoked_state)
        output = CleanupAgentOutput(
            schema_version="phase3.agent.lead_cleanup.v1",
            cleanup_run_id=state.cleanup_run_id,
            suggestions=state.suggestions,
            blocked_items=state.blocked_items,
            audit=state.audit,
        )
        return LeadCleanupGraphResult(output=output, executed_nodes=list(self.executed_nodes))

    def _state_from_graph_result(self, result: LeadCleanupGraphState | dict[str, Any]) -> LeadCleanupGraphState:
        if isinstance(result, LeadCleanupGraphState):
            return result
        return LeadCleanupGraphState(
            cleanup_run_id=result["cleanup_run_id"],
            leads=list(result.get("leads") or []),
            requested_actions=list(result.get("requested_actions") or []),
            target_leads=list(result.get("target_leads") or []),
            raw_suggestions=list(result.get("raw_suggestions") or []),
            suggestions=[
                item if isinstance(item, CleanupSuggestionOutput) else CleanupSuggestionOutput(**item)
                for item in result.get("suggestions") or []
            ],
            blocked_items=list(result.get("blocked_items") or []),
            audit=dict(result.get("audit") or {}),
        )
