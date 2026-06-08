from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from langgraph.graph import END, StateGraph

from app.adapters.api_contract import ApiContractBoundary
from app.schemas.deep_enrichment import DeepEnrichmentAgentOutput, FieldCandidateOutput
from app.services.agent_logging import run_logged_node
from app.services.llm_client import LLMClient
from app.tools.evidence_validator import filter_candidates_with_evidence
from app.tools.public_search import EmptyPublicSearchTool, validate_public_search_actions


DEEP_ENRICHMENT_NODE_SEQUENCE = (
    "load_lead",
    "build_keywords",
    "search_public_sources",
    "read_public_pages",
    "extract_candidates",
    "validate_evidence",
    "write_enrichment_candidates",
    "recommend_action",
)


@dataclass(slots=True)
class DeepEnrichmentGraphState:
    agent_run_id: UUID | str
    staging_lead_id: UUID | str
    lead_snapshot: dict[str, Any]
    missing_fields: list[str] = field(default_factory=list)
    requested_actions: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    public_sources: list[dict] = field(default_factory=list)
    page_snapshots: list[dict] = field(default_factory=list)
    raw_candidates: list[dict] = field(default_factory=list)
    field_candidates: list[FieldCandidateOutput] = field(default_factory=list)
    recommended_next_action: str = "manual_review"
    audit: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class DeepEnrichmentGraphResult:
    output: DeepEnrichmentAgentOutput
    executed_nodes: list[str]


class LLMDeepEnrichmentExtractor:
    def __init__(self, *, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client or LLMClient()
        self.last_audit: dict[str, Any] = {}

    def extract(self, state: DeepEnrichmentGraphState) -> list[dict]:
        result = self.llm_client.generate_json(
            task_type="DEEP_ENRICHMENT",
            system_prompt=(
                "你是线索深挖补全 Agent。只从公开页面快照抽取候选字段。"
                "缺失字段返回空数组，禁止编造；每个候选必须包含 source_url 和 evidence_note。"
            ),
            user_prompt=(
                f"线索快照：{state.lead_snapshot}\n"
                f"缺失字段：{state.missing_fields}\n"
                f"公开页面快照：{state.page_snapshots}"
            ),
            output_schema={
                "type": "object",
                "properties": {
                    "field_candidates": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "field_name": {"type": "string"},
                                "candidate_value": {},
                                "source_type": {"type": "string"},
                                "source_url": {"type": ["string", "null"]},
                                "evidence_note": {"type": "string"},
                                "confidence_score": {"type": ["number", "null"]},
                            },
                            "required": ["field_name", "candidate_value", "source_type", "source_url", "evidence_note"],
                        },
                    }
                },
                "required": ["field_candidates"],
            },
        )
        self.last_audit = {
            "used": result.error is None,
            "provider": result.provider,
            "model": result.model,
            "token_usage": result.token_usage,
        }
        if result.error:
            self.last_audit["error"] = result.error
            return []
        output = result.output_json if isinstance(result.output_json, dict) else {}
        candidates = output.get("field_candidates") if isinstance(output.get("field_candidates"), list) else []
        return [item for item in candidates if isinstance(item, dict)]


class DeepEnrichmentGraphRunner:
    agent_type = "deep_enrichment"

    def __init__(
        self,
        *,
        search_tool=None,
        llm_extractor: LLMDeepEnrichmentExtractor | None = None,
        boundary: ApiContractBoundary | None = None,
    ) -> None:
        self.search_tool = search_tool or EmptyPublicSearchTool()
        self.llm_extractor = llm_extractor or LLMDeepEnrichmentExtractor()
        self.boundary = boundary or ApiContractBoundary()
        self.executed_nodes: list[str] = []
        self.compiled_graph = self._build_graph()

    def _build_graph(self):
        graph = StateGraph(DeepEnrichmentGraphState)
        for node_name in DEEP_ENRICHMENT_NODE_SEQUENCE:
            graph.add_node(
                node_name,
                lambda state, node_name=node_name: run_logged_node(
                    agent_type=self.agent_type,
                    node_name=node_name,
                    func=getattr(self, node_name),
                    state=state,
                ),
            )
        graph.set_entry_point(DEEP_ENRICHMENT_NODE_SEQUENCE[0])
        for index, node_name in enumerate(DEEP_ENRICHMENT_NODE_SEQUENCE):
            next_index = index + 1
            graph.add_edge(
                node_name,
                DEEP_ENRICHMENT_NODE_SEQUENCE[next_index] if next_index < len(DEEP_ENRICHMENT_NODE_SEQUENCE) else END,
            )
        return graph.compile()

    def mark(self, node_name: str) -> None:
        self.executed_nodes.append(node_name)

    def load_lead(self, state: DeepEnrichmentGraphState) -> DeepEnrichmentGraphState:
        self.mark("load_lead")
        validate_public_search_actions(state.requested_actions)
        state.audit["loaded_lead"] = True
        return state

    def build_keywords(self, state: DeepEnrichmentGraphState) -> DeepEnrichmentGraphState:
        self.mark("build_keywords")
        snapshot = state.lead_snapshot
        keywords = [
            str(snapshot.get("customer_name") or "Unknown"),
            str(snapshot.get("city") or "Unknown"),
            str(snapshot.get("country") or "Unknown"),
            *state.missing_fields,
        ]
        state.keywords = [keyword for keyword in keywords if keyword and keyword != "Unknown"]
        return state

    def search_public_sources(self, state: DeepEnrichmentGraphState) -> DeepEnrichmentGraphState:
        self.mark("search_public_sources")
        state.public_sources = list(self.search_tool.search(state.keywords))
        return state

    def read_public_pages(self, state: DeepEnrichmentGraphState) -> DeepEnrichmentGraphState:
        self.mark("read_public_pages")
        state.page_snapshots = [
            {
                "source_url": item.get("url"),
                "title": item.get("title"),
                "text": item.get("text") or "",
            }
            for item in state.public_sources
        ]
        return state

    def extract_candidates(self, state: DeepEnrichmentGraphState) -> DeepEnrichmentGraphState:
        self.mark("extract_candidates")
        state.raw_candidates = list(self.llm_extractor.extract(state))
        state.audit["llm_extractor"] = dict(getattr(self.llm_extractor, "last_audit", {}))
        return state

    def validate_evidence(self, state: DeepEnrichmentGraphState) -> DeepEnrichmentGraphState:
        self.mark("validate_evidence")
        state.field_candidates = [
            FieldCandidateOutput(**item)
            for item in filter_candidates_with_evidence(state.raw_candidates)
            if self.has_page_text_evidence(state, item)
        ]
        return state

    def write_enrichment_candidates(self, state: DeepEnrichmentGraphState) -> DeepEnrichmentGraphState:
        self.mark("write_enrichment_candidates")
        output_table = self.boundary.validate_output_table("lead_enrichment_field_candidates")
        state.audit.update(
            {
                "writes_core_tables": False,
                "output_table": output_table,
                "written_tables": [output_table],
                "source_urls": sorted(
                    {
                        str(candidate.source_url)
                        for candidate in state.field_candidates
                        if candidate.source_url
                    }
                ),
            }
        )
        return state

    def recommend_action(self, state: DeepEnrichmentGraphState) -> DeepEnrichmentGraphState:
        self.mark("recommend_action")
        completed_fields = {
            candidate.field_name
            for candidate in state.field_candidates
            if candidate.candidate_value not in (None, "Unknown", [])
        }
        state.missing_fields = [field_name for field_name in state.missing_fields if field_name not in completed_fields]
        state.recommended_next_action = "manual_review" if state.field_candidates else "continue_enrichment"
        return state

    def run(self, state: DeepEnrichmentGraphState) -> DeepEnrichmentGraphResult:
        invoked_state = self.compiled_graph.invoke(state)
        state = self._state_from_graph_result(invoked_state)
        output = DeepEnrichmentAgentOutput(
            schema_version="phase3.agent.deep_enrichment.v1",
            agent_run_id=state.agent_run_id,
            staging_lead_id=state.staging_lead_id,
            field_candidates=state.field_candidates,
            missing_fields=state.missing_fields,
            recommended_next_action=state.recommended_next_action,
            audit=state.audit,
        )
        return DeepEnrichmentGraphResult(output=output, executed_nodes=list(self.executed_nodes))

    def _state_from_graph_result(self, result: DeepEnrichmentGraphState | dict[str, Any]) -> DeepEnrichmentGraphState:
        if isinstance(result, DeepEnrichmentGraphState):
            return result
        return DeepEnrichmentGraphState(
            agent_run_id=result["agent_run_id"],
            staging_lead_id=result["staging_lead_id"],
            lead_snapshot=result["lead_snapshot"],
            missing_fields=list(result.get("missing_fields") or []),
            requested_actions=list(result.get("requested_actions") or []),
            keywords=list(result.get("keywords") or []),
            public_sources=list(result.get("public_sources") or []),
            page_snapshots=list(result.get("page_snapshots") or []),
            raw_candidates=list(result.get("raw_candidates") or []),
            field_candidates=[
                item if isinstance(item, FieldCandidateOutput) else FieldCandidateOutput(**item)
                for item in result.get("field_candidates") or []
            ],
            recommended_next_action=result.get("recommended_next_action") or "manual_review",
            audit=dict(result.get("audit") or {}),
        )

    @staticmethod
    def has_page_text_evidence(state: DeepEnrichmentGraphState, candidate: dict) -> bool:
        value = str(candidate.get("candidate_value") or "").strip()
        source_url = str(candidate.get("source_url") or "").strip()
        if not value or not source_url:
            return False
        for page in state.page_snapshots:
            if str(page.get("source_url") or "").strip() != source_url:
                continue
            text = str(page.get("text") or "")
            if value.lower() in text.lower():
                return True
        return False
