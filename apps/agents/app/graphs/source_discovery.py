from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from langgraph.graph import END, StateGraph

from app.adapters.api_contract import ApiContractBoundary
from app.schemas.source_discovery import SourceCandidateOutput, SourceDiscoveryAgentOutput
from app.services.agent_logging import run_logged_node


SOURCE_DISCOVERY_NODE_SEQUENCE = (
    "load_channel_strategy",
    "build_discovery_queries",
    "search_public_sources",
    "normalize_source_candidates",
    "classify_channel_risk",
    "dedupe_candidates",
    "validate_source_evidence",
    "output_shadow_candidates",
)

FORBIDDEN_SOURCE_DISCOVERY_ACTIONS = {"login_collect", "private_data_collect", "anti_scraping_bypass", "auto_insert_sources"}
LOW_RISK_SOURCE_TYPES = {"official_website", "marketplace"}
MEDIUM_RISK_SOURCE_TYPES = {"public_directory", "unknown"}
HIGH_RISK_SOURCE_TYPES = {"public_social"}


@dataclass(slots=True)
class SourceDiscoveryGraphState:
    discovery_run_id: str
    market: str
    channel_strategy: dict[str, Any]
    agent_mode: str = "shadow"
    seed_urls: list[str] = field(default_factory=list)
    requested_actions: list[str] = field(default_factory=list)
    search_results: list[dict[str, Any]] = field(default_factory=list)
    discovery_queries: list[str] = field(default_factory=list)
    raw_candidates: list[dict[str, Any]] = field(default_factory=list)
    normalized_candidates: list[dict[str, Any]] = field(default_factory=list)
    deduped_candidates: list[dict[str, Any]] = field(default_factory=list)
    candidates: list[SourceCandidateOutput] = field(default_factory=list)
    blocked_items: list[dict[str, Any]] = field(default_factory=list)
    audit: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SourceDiscoveryGraphResult:
    output: SourceDiscoveryAgentOutput
    executed_nodes: list[str]


class EmptySourceSearchTool:
    def search(self, queries: list[str]) -> list[dict[str, Any]]:
        return []


class SourceDiscoveryGraphRunner:
    agent_type = "source_discovery"

    def __init__(self, *, search_tool=None, boundary: ApiContractBoundary | None = None) -> None:
        self.search_tool = search_tool or EmptySourceSearchTool()
        self.boundary = boundary or ApiContractBoundary()
        self.executed_nodes: list[str] = []
        self.compiled_graph = self._build_graph()

    def _build_graph(self):
        graph = StateGraph(SourceDiscoveryGraphState)
        for node_name in SOURCE_DISCOVERY_NODE_SEQUENCE:
            graph.add_node(
                node_name,
                lambda state, node_name=node_name: run_logged_node(
                    agent_type=self.agent_type,
                    node_name=node_name,
                    func=getattr(self, node_name),
                    state=state,
                ),
            )
        graph.set_entry_point(SOURCE_DISCOVERY_NODE_SEQUENCE[0])
        for index, node_name in enumerate(SOURCE_DISCOVERY_NODE_SEQUENCE):
            next_index = index + 1
            graph.add_edge(
                node_name,
                SOURCE_DISCOVERY_NODE_SEQUENCE[next_index] if next_index < len(SOURCE_DISCOVERY_NODE_SEQUENCE) else END,
            )
        return graph.compile()

    def mark(self, node_name: str) -> None:
        self.executed_nodes.append(node_name)

    @staticmethod
    def set_node_summary(state: SourceDiscoveryGraphState, node_name: str, summary: dict[str, Any]) -> None:
        state.audit.setdefault("node_summaries", {})[node_name] = summary

    def load_channel_strategy(self, state: SourceDiscoveryGraphState) -> SourceDiscoveryGraphState:
        self.mark("load_channel_strategy")
        if state.agent_mode != "shadow":
            raise ValueError("Source Discovery 第四阶段只允许 shadow_run。")
        if FORBIDDEN_SOURCE_DISCOVERY_ACTIONS & set(state.requested_actions):
            raise ValueError("Source Discovery 不允许登录采集、私有数据采集、反爬规避或自动写入来源池。")
        state.audit.update({"agent_mode": "shadow", "market": state.market})
        self.set_node_summary(state, "load_channel_strategy", {"agent_mode": "shadow"})
        return state

    def build_discovery_queries(self, state: SourceDiscoveryGraphState) -> SourceDiscoveryGraphState:
        self.mark("build_discovery_queries")
        strategy = state.channel_strategy or {}
        keywords = [str(item).strip() for item in strategy.get("keywords") or [] if str(item).strip()]
        segments = [str(item).strip() for item in strategy.get("target_segments") or [] if str(item).strip()]
        base_terms = keywords or segments or ["used cars dealer"]
        state.discovery_queries = [f"{state.market} {term}".strip() for term in base_terms]
        self.set_node_summary(state, "build_discovery_queries", {"query_count": len(state.discovery_queries)})
        return state

    def search_public_sources(self, state: SourceDiscoveryGraphState) -> SourceDiscoveryGraphState:
        self.mark("search_public_sources")
        seed_candidates = [
            {
                "url": url,
                "title": url,
                "snippet": "Seed URL from apps/api source discovery shadow input.",
                "source_type": "official_website",
                "discovery_query": "seed_url",
            }
            for url in state.seed_urls
        ]
        searched = list(state.search_results or self.search_tool.search(state.discovery_queries))
        state.raw_candidates = [*seed_candidates, *searched]
        self.set_node_summary(state, "search_public_sources", {"raw_candidate_count": len(state.raw_candidates)})
        return state

    def normalize_source_candidates(self, state: SourceDiscoveryGraphState) -> SourceDiscoveryGraphState:
        self.mark("normalize_source_candidates")
        state.normalized_candidates = [
            {
                **item,
                "normalized_url": self.normalize_url(str(item.get("url") or "")),
                "source_type": self.normalize_source_type(str(item.get("source_type") or "unknown")),
                "evidence_summary": self.evidence_summary(item),
            }
            for item in state.raw_candidates
        ]
        self.set_node_summary(state, "normalize_source_candidates", {"normalized_count": len(state.normalized_candidates)})
        return state

    def classify_channel_risk(self, state: SourceDiscoveryGraphState) -> SourceDiscoveryGraphState:
        self.mark("classify_channel_risk")
        risk_counts: dict[str, int] = {}
        for item in state.normalized_candidates:
            item["risk_level"] = self.classify_risk(item)
            risk_counts[item["risk_level"]] = risk_counts.get(item["risk_level"], 0) + 1
        self.set_node_summary(state, "classify_channel_risk", {"risk_counts": risk_counts})
        return state

    def dedupe_candidates(self, state: SourceDiscoveryGraphState) -> SourceDiscoveryGraphState:
        self.mark("dedupe_candidates")
        seen: set[str] = set()
        state.deduped_candidates = []
        state.blocked_items = []
        for item in state.normalized_candidates:
            normalized_url = item.get("normalized_url")
            if not normalized_url or normalized_url in seen:
                if normalized_url:
                    state.blocked_items.append(
                        {
                            "url": item.get("url"),
                            "normalized_url": normalized_url,
                            "source_type": item.get("source_type"),
                            "risk_level": item.get("risk_level"),
                            "reason": "duplicate_source",
                        }
                    )
                continue
            seen.add(normalized_url)
            state.deduped_candidates.append(item)
        self.set_node_summary(
            state,
            "dedupe_candidates",
            {
                "duplicate_count": len([item for item in state.blocked_items if item.get("reason") == "duplicate_source"]),
                "deduped_count": len(state.deduped_candidates),
            },
        )
        return state

    def validate_source_evidence(self, state: SourceDiscoveryGraphState) -> SourceDiscoveryGraphState:
        self.mark("validate_source_evidence")
        state.candidates = []
        for item in state.deduped_candidates:
            blocked_reason = self.blocked_reason(item)
            if blocked_reason:
                state.blocked_items.append(
                    {
                        "url": item.get("url"),
                        "normalized_url": item.get("normalized_url"),
                        "source_type": item.get("source_type"),
                        "risk_level": item.get("risk_level"),
                        "reason": blocked_reason,
                    }
                )
                continue
            risk_level = item["risk_level"]
            state.candidates.append(
                SourceCandidateOutput(
                    url=item["url"],
                    normalized_url=item["normalized_url"],
                    source_type=item["source_type"],
                    risk_level=risk_level,
                    evidence_summary=item["evidence_summary"],
                    discovery_query=item.get("discovery_query"),
                    review_status="needs_manual_review" if risk_level == "high" else "shadow_only",
                )
            )
        self.set_node_summary(
            state,
            "validate_source_evidence",
            {"valid_candidate_count": len(state.candidates), "blocked_item_count": len(state.blocked_items)},
        )
        return state

    def output_shadow_candidates(self, state: SourceDiscoveryGraphState) -> SourceDiscoveryGraphState:
        self.mark("output_shadow_candidates")
        output_table = self.boundary.validate_output_table("shadow_source_candidates")
        state.audit.update(
            {
                "writes_core_tables": False,
                "output_table": output_table,
                "written_tables": [output_table],
                "candidate_count": len(state.candidates),
                "blocked_item_count": len(state.blocked_items),
                "source_urls": [candidate.url for candidate in state.candidates],
            }
        )
        self.set_node_summary(
            state,
            "output_shadow_candidates",
            {"candidate_count": len(state.candidates), "blocked_item_count": len(state.blocked_items)},
        )
        return state

    def run(self, state: SourceDiscoveryGraphState) -> SourceDiscoveryGraphResult:
        invoked_state = self.compiled_graph.invoke(state)
        state = self._state_from_graph_result(invoked_state)
        output = SourceDiscoveryAgentOutput(
            schema_version="phase4.agent.source_discovery.v1",
            discovery_run_id=state.discovery_run_id,
            agent_mode="shadow",
            candidates=state.candidates,
            blocked_items=state.blocked_items,
            audit=state.audit,
        )
        return SourceDiscoveryGraphResult(output=output, executed_nodes=list(self.executed_nodes))

    def _state_from_graph_result(self, result: SourceDiscoveryGraphState | dict[str, Any]) -> SourceDiscoveryGraphState:
        if isinstance(result, SourceDiscoveryGraphState):
            return result
        return SourceDiscoveryGraphState(
            discovery_run_id=result["discovery_run_id"],
            market=result["market"],
            channel_strategy=dict(result.get("channel_strategy") or {}),
            agent_mode=result.get("agent_mode") or "shadow",
            seed_urls=list(result.get("seed_urls") or []),
            requested_actions=list(result.get("requested_actions") or []),
            search_results=list(result.get("search_results") or []),
            discovery_queries=list(result.get("discovery_queries") or []),
            raw_candidates=list(result.get("raw_candidates") or []),
            normalized_candidates=list(result.get("normalized_candidates") or []),
            deduped_candidates=list(result.get("deduped_candidates") or []),
            candidates=[
                item if isinstance(item, SourceCandidateOutput) else SourceCandidateOutput(**item)
                for item in result.get("candidates") or []
            ],
            blocked_items=list(result.get("blocked_items") or []),
            audit=dict(result.get("audit") or {}),
        )

    @staticmethod
    def normalize_url(url: str) -> str:
        stripped = url.strip()
        if not stripped:
            return ""
        if "://" not in stripped:
            stripped = f"https://{stripped}"
        parts = urlsplit(stripped)
        scheme = (parts.scheme or "https").lower()
        netloc = parts.netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        path = parts.path.rstrip("/")
        return urlunsplit((scheme, netloc, path, "", ""))

    @staticmethod
    def normalize_source_type(source_type: str) -> str:
        normalized = source_type.strip().lower()
        if normalized in LOW_RISK_SOURCE_TYPES or normalized in MEDIUM_RISK_SOURCE_TYPES or normalized in HIGH_RISK_SOURCE_TYPES:
            return normalized
        if normalized in {"private_platform", "login_required"}:
            return "unknown"
        return "unknown"

    @staticmethod
    def evidence_summary(item: dict[str, Any]) -> str:
        snippet = str(item.get("snippet") or item.get("text") or "").strip()
        title = str(item.get("title") or "").strip()
        return snippet or title

    @staticmethod
    def classify_risk(item: dict[str, Any]) -> str:
        text = f"{item.get('url') or ''} {item.get('title') or ''} {item.get('snippet') or ''}".lower()
        if "login" in text or "captcha" in text or "private" in text:
            return "forbidden"
        source_type = item.get("source_type")
        if source_type in HIGH_RISK_SOURCE_TYPES:
            return "high"
        if source_type in MEDIUM_RISK_SOURCE_TYPES:
            return "medium"
        if source_type in LOW_RISK_SOURCE_TYPES:
            return "low"
        return "medium"

    @staticmethod
    def blocked_reason(item: dict[str, Any]) -> str | None:
        if not item.get("normalized_url"):
            return "missing_url"
        if not item.get("evidence_summary"):
            return "missing_evidence_summary"
        if item.get("risk_level") == "forbidden":
            return "forbidden_source"
        return None
