from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from app.adapters.api_contract import ApiContractBoundary
from app.schemas.deep_enrichment import DeepEnrichmentAgentOutput, FieldCandidateOutput
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


class NullLLMExtractor:
    def extract(self, state: DeepEnrichmentGraphState) -> list[dict]:
        return []


class DeepEnrichmentGraphRunner:
    def __init__(self, *, search_tool=None, llm_extractor=None, boundary: ApiContractBoundary | None = None) -> None:
        self.search_tool = search_tool or EmptyPublicSearchTool()
        self.llm_extractor = llm_extractor or NullLLMExtractor()
        self.boundary = boundary or ApiContractBoundary()
        self.executed_nodes: list[str] = []

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
        return state

    def validate_evidence(self, state: DeepEnrichmentGraphState) -> DeepEnrichmentGraphState:
        self.mark("validate_evidence")
        state.field_candidates = [FieldCandidateOutput(**item) for item in filter_candidates_with_evidence(state.raw_candidates)]
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
        for node_name in DEEP_ENRICHMENT_NODE_SEQUENCE:
            state = getattr(self, node_name)(state)
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
