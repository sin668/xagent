from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from langgraph.graph import END, StateGraph

from app.adapters.api_contract import ApiContractBoundary
from app.schemas.lead_cleanup import CleanupAgentOutput, CleanupSuggestionOutput
from app.services.agent_logging import run_logged_node
from app.services.llm_client import LLMClient
from app.services.llm_prompt_repository import LLMPromptRepository, LLMPromptTemplateNotFound
from app.tools.duplicate_detector import DuplicateDetector


LEAD_CLEANUP_NODE_SEQUENCE = (
    "load_watch_invalid",
    "detect_duplicates",
    "classify_invalid_reason",
    "find_restore_candidates",
    "review_cleanup_with_llm",
    "write_cleanup_suggestions",
    "wait_human_review",
)

FORBIDDEN_CLEANUP_ACTIONS = {"auto_execute_cleanup", "delete_leads", "restore_invalid"}
VALID_SUGGESTION_TYPES = {
    "strong_duplicate",
    "possible_duplicate",
    "merge_contact_method",
    "merge_source_evidence",
    "restore_from_watch",
    "confirm_invalid",
    "mark_abandoned",
    "needs_manual_review",
}
SUGGESTION_TYPE_ALIASES = {
    "keep_watch": "needs_manual_review",
    "keep_invalid": "needs_manual_review",
    "keep_as_watch": "needs_manual_review",
    "keep_as_invalid": "needs_manual_review",
    "manual_review": "needs_manual_review",
    "review_manually": "needs_manual_review",
    "keep": "needs_manual_review",
    "dedup": "possible_duplicate",
    "dedupe": "possible_duplicate",
    "deduplicate": "possible_duplicate",
    "duplicate": "possible_duplicate",
    "merge_duplicate": "possible_duplicate",
    "merge_duplicates": "possible_duplicate",
    "potential_duplicate": "possible_duplicate",
    "suspected_duplicate": "possible_duplicate",
    "确认无效": "confirm_invalid",
    "无效": "confirm_invalid",
    "标记无效": "confirm_invalid",
    "确认无效并隐藏": "confirm_invalid",
    "隐藏无效": "confirm_invalid",
    "恢复": "restore_from_watch",
    "恢复线索": "restore_from_watch",
    "恢复观察": "restore_from_watch",
    "保持观察": "needs_manual_review",
    "保留观察": "needs_manual_review",
    "人工复核": "needs_manual_review",
    "需要人工复核": "needs_manual_review",
    "疑似重复": "possible_duplicate",
    "去重": "possible_duplicate",
    "重复": "possible_duplicate",
    "合并重复": "possible_duplicate",
}


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


class LLMLeadCleanupReviewer:
    def __init__(self, *, llm_client: LLMClient | None = None, prompt_repository: LLMPromptRepository | None = None) -> None:
        self.llm_client = llm_client or LLMClient()
        self.prompt_repository = prompt_repository or LLMPromptRepository()
        self.last_audit: dict[str, Any] = {}

    def review(self, leads: list[dict[str, Any]]) -> list[dict[str, Any]]:
        task_type = "LEAD_CLEANUP"
        model = self.llm_client._model_for_task(task_type)
        try:
            prompt = self.prompt_repository.load_active_default(
                task_type=task_type,
                provider=self.llm_client.settings.llm_provider,
                model=model,
            )
        except LLMPromptTemplateNotFound as exc:
            self.last_audit = {
                "used": False,
                "provider": self.llm_client.settings.llm_provider,
                "model": model,
                "error": {"type": exc.error_type, "message": str(exc)},
            }
            raise
        result = self.llm_client.generate_json(
            task_type=task_type,
            system_prompt=prompt.system_prompt,
            user_prompt=prompt.render_user_prompt({"leads": leads}),
            output_schema=prompt.output_schema_json,
        )
        self.last_audit = {
            "used": result.error is None,
            "provider": result.provider,
            "model": result.model,
            "token_usage": result.token_usage,
            **prompt.audit,
        }
        if result.error:
            self.last_audit["error"] = result.error
            return []
        output = result.output_json if isinstance(result.output_json, dict) else {}
        suggestions = output.get("suggestions") if isinstance(output.get("suggestions"), list) else []
        return [item for item in suggestions if isinstance(item, dict)]


class LeadCleanupGraphRunner:
    agent_type = "lead_cleanup"

    def __init__(
        self,
        *,
        duplicate_detector: DuplicateDetector | None = None,
        llm_reviewer: LLMLeadCleanupReviewer | None = None,
        prompt_repository: LLMPromptRepository | None = None,
        boundary: ApiContractBoundary | None = None,
    ) -> None:
        self.duplicate_detector = duplicate_detector or DuplicateDetector()
        self.llm_reviewer = llm_reviewer or LLMLeadCleanupReviewer(prompt_repository=prompt_repository)
        self.boundary = boundary or ApiContractBoundary()
        self.executed_nodes: list[str] = []
        self.compiled_graph = self._build_graph()

    def _build_graph(self):
        graph = StateGraph(LeadCleanupGraphState)
        for node_name in LEAD_CLEANUP_NODE_SEQUENCE:
            graph.add_node(
                node_name,
                lambda state, node_name=node_name: run_logged_node(
                    agent_type=self.agent_type,
                    node_name=node_name,
                    func=getattr(self, node_name),
                    state=state,
                ),
            )
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
                    "recommended_action": "确认无效并从线索池隐藏",
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
                state.raw_suggestions.append(
                    {
                        "staging_lead_id": lead.get("staging_lead_id"),
                        "suggestion_type": "needs_manual_review",
                        "target_lead_id": None,
                        "confidence_score": 0.6,
                        "reason": "Watch 线索暂无新的公开恢复证据，建议保持观察并等待人工复核。",
                        "evidence_json": {
                            "current_grade": "Watch",
                            "source_evidence": lead.get("source_evidence"),
                            "contacts_json": lead.get("contacts_json") or [],
                        },
                        "recommended_action": "保持 Watch，等待更多公开证据或人工复核",
                    }
                )
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

    def review_cleanup_with_llm(self, state: LeadCleanupGraphState) -> LeadCleanupGraphState:
        self.mark("review_cleanup_with_llm")
        state.raw_suggestions.extend(self.llm_reviewer.review(state.target_leads))
        state.audit["llm_reviewer"] = dict(getattr(self.llm_reviewer, "last_audit", {}))
        return state

    def write_cleanup_suggestions(self, state: LeadCleanupGraphState) -> LeadCleanupGraphState:
        self.mark("write_cleanup_suggestions")
        output_table = self.boundary.validate_output_table("lead_cleanup_suggestions")
        normalized_items = [self.normalize_cleanup_suggestion(item) for item in state.raw_suggestions]
        state.suggestions = [CleanupSuggestionOutput(**item) for item in normalized_items]
        state.audit.update(
            {
                "writes_core_tables": False,
                "output_table": output_table,
                "written_tables": [output_table],
                "suggestion_count": len(state.suggestions),
                "normalized_suggestion_type_count": len(
                    [
                        item
                        for item in normalized_items
                        if (item.get("evidence_json") or {}).get("normalized_from_suggestion_type")
                    ]
                ),
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

    @staticmethod
    def normalize_cleanup_suggestion(item: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(item)
        raw_type = str(normalized.get("suggestion_type") or "").strip().lower()
        if raw_type in VALID_SUGGESTION_TYPES:
            normalized["suggestion_type"] = raw_type
            return normalized

        mapped_type = SUGGESTION_TYPE_ALIASES.get(raw_type) or LeadCleanupGraphRunner.infer_suggestion_type(raw_type)
        if mapped_type is None:
            return normalized

        evidence = dict(normalized.get("evidence_json") or {})
        evidence.setdefault("normalized_from_suggestion_type", raw_type)
        normalized["suggestion_type"] = mapped_type
        normalized["evidence_json"] = evidence
        return normalized

    @staticmethod
    def infer_suggestion_type(raw_type: str) -> str | None:
        if any(token in raw_type for token in ("confirm_invalid", "invalid", "无效", "非目标")):
            return "confirm_invalid"
        if any(token in raw_type for token in ("restore", "恢复", "升级")):
            return "restore_from_watch"
        if any(token in raw_type for token in ("duplicate", "dedup", "重复", "去重", "归并", "合并")):
            return "possible_duplicate"
        if any(token in raw_type for token in ("review", "manual", "watch", "keep", "复核", "观察", "保留")):
            return "needs_manual_review"
        return None

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
