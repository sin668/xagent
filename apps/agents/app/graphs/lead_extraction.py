from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from langgraph.graph import END, StateGraph

from app.adapters.api_contract import ApiContractBoundary
from app.schemas.lead_extraction import (
    ExtractedLeadField,
    FieldEvidence,
    LeadExtractionAgentOutput,
    LeadExtractionCandidate,
    LeadExtractionFieldName,
)
from app.services.agent_logging import run_logged_node
from app.services.llm_client import LLMClient


LEAD_EXTRACTION_NODE_SEQUENCE = (
    "load_source_content",
    "extract_candidate_fields",
    "map_field_evidence",
    "validate_required_evidence",
    "output_shadow_staging_lead",
)

FIELD_NAMES: tuple[LeadExtractionFieldName, ...] = (
    "company_name",
    "email",
    "phone",
    "country",
    "city",
    "vehicle_interest",
    "export_intent",
    "website",
)

EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")
PHONE_PATTERN = re.compile(r"\+\d{1,3}[\d\s().-]{7,}\d")
URL_PATTERN = re.compile(r"https?://[^\s,。)]+")


@dataclass(slots=True)
class LeadExtractionGraphState:
    extraction_run_id: str
    source_url: str
    source_content: str
    agent_mode: str = "shadow"
    raw_fields: dict[str, str | None] = field(default_factory=dict)
    field_evidence: dict[str, dict[str, str] | None] = field(default_factory=dict)
    candidate: LeadExtractionCandidate | None = None
    validation_errors: list[str] = field(default_factory=list)
    audit: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class LeadExtractionGraphResult:
    output: LeadExtractionAgentOutput
    executed_nodes: list[str]


class LLMLeadFieldExtractor:
    def __init__(self, *, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client or LLMClient()
        self.last_audit: dict[str, Any] = {}

    def extract(self, *, source_url: str, source_content: str) -> dict[str, str | None]:
        result = self.llm_client.generate_json(
            task_type="LEAD_EXTRACTION",
            system_prompt=(
                "你是公开网页线索抽取 Agent。只从输入文本抽取字段；缺失字段必须返回 null，禁止编造。"
                "输出字段只能包含 company_name、email、phone、country、city、vehicle_interest、export_intent、website。"
            ),
            user_prompt=f"来源链接：{source_url}\n公开文本：\n{source_content}",
            output_schema={
                "type": "object",
                "properties": {
                    "fields": {
                        "type": "object",
                        "properties": {field_name: {"type": ["string", "null"]} for field_name in FIELD_NAMES},
                    }
                },
                "required": ["fields"],
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
            return {}
        output = result.output_json if isinstance(result.output_json, dict) else {}
        fields = output.get("fields") if isinstance(output.get("fields"), dict) else {}
        extracted: dict[str, str | None] = {}
        for field_name in FIELD_NAMES:
            value = fields.get(field_name)
            extracted[field_name] = str(value).strip() if value not in (None, "") else None
        return extracted


class LeadExtractionGraphRunner:
    agent_type = "lead_extraction"

    def __init__(
        self,
        *,
        llm_field_extractor: LLMLeadFieldExtractor | None = None,
        boundary: ApiContractBoundary | None = None,
    ) -> None:
        self.llm_field_extractor = llm_field_extractor or LLMLeadFieldExtractor()
        self.boundary = boundary or ApiContractBoundary()
        self.executed_nodes: list[str] = []
        self.compiled_graph = self._build_graph()

    def _build_graph(self):
        graph = StateGraph(LeadExtractionGraphState)
        for node_name in LEAD_EXTRACTION_NODE_SEQUENCE:
            graph.add_node(
                node_name,
                lambda state, node_name=node_name: run_logged_node(
                    agent_type=self.agent_type,
                    node_name=node_name,
                    func=getattr(self, node_name),
                    state=state,
                ),
            )
        graph.set_entry_point(LEAD_EXTRACTION_NODE_SEQUENCE[0])
        for index, node_name in enumerate(LEAD_EXTRACTION_NODE_SEQUENCE):
            next_index = index + 1
            graph.add_edge(
                node_name,
                LEAD_EXTRACTION_NODE_SEQUENCE[next_index] if next_index < len(LEAD_EXTRACTION_NODE_SEQUENCE) else END,
            )
        return graph.compile()

    def mark(self, node_name: str) -> None:
        self.executed_nodes.append(node_name)

    @staticmethod
    def set_node_summary(state: LeadExtractionGraphState, node_name: str, summary: dict[str, Any]) -> None:
        state.audit.setdefault("node_summaries", {})[node_name] = summary

    def load_source_content(self, state: LeadExtractionGraphState) -> LeadExtractionGraphState:
        self.mark("load_source_content")
        if state.agent_mode != "shadow":
            raise ValueError("Lead Extraction 第四阶段只允许 shadow_run。")
        if not state.source_content.strip():
            raise ValueError("Lead Extraction 需要输入公开来源文本或来源内容。")
        state.audit.update({"agent_mode": "shadow", "source_url": state.source_url})
        self.set_node_summary(state, "load_source_content", {"content_length": len(state.source_content)})
        return state

    def extract_candidate_fields(self, state: LeadExtractionGraphState) -> LeadExtractionGraphState:
        self.mark("extract_candidate_fields")
        text = self.normalize_text(state.source_content)
        rule_fields: dict[str, str | None] = {
            "company_name": self.extract_company_name(text),
            "email": self.first_match(EMAIL_PATTERN, text),
            "phone": self.extract_phone(text),
            "country": self.extract_country(text),
            "city": self.extract_city(text),
            "vehicle_interest": self.extract_vehicle_interest(text),
            "export_intent": self.extract_export_intent(text),
            "website": self.first_match(URL_PATTERN, text) or state.source_url,
        }
        llm_fields = self.llm_field_extractor.extract(source_url=state.source_url, source_content=state.source_content)
        state.audit["llm_field_extractor"] = dict(self.llm_field_extractor.last_audit)
        state.raw_fields = {
            field_name: llm_fields.get(field_name) or rule_fields.get(field_name)
            for field_name in FIELD_NAMES
        }
        self.set_node_summary(
            state,
            "extract_candidate_fields",
            {"filled_field_count": len([value for value in state.raw_fields.values() if value])},
        )
        return state

    def map_field_evidence(self, state: LeadExtractionGraphState) -> LeadExtractionGraphState:
        self.mark("map_field_evidence")
        text = self.normalize_text(state.source_content)
        state.field_evidence = {}
        for field_name in FIELD_NAMES:
            value = state.raw_fields.get(field_name)
            state.field_evidence[field_name] = self.find_evidence(text, value)
        self.set_node_summary(
            state,
            "map_field_evidence",
            {"evidence_count": len([item for item in state.field_evidence.values() if item])},
        )
        return state

    def validate_required_evidence(self, state: LeadExtractionGraphState) -> LeadExtractionGraphState:
        self.mark("validate_required_evidence")
        fields: dict[str, ExtractedLeadField] = {}
        state.validation_errors = []
        for field_name in FIELD_NAMES:
            value = state.raw_fields.get(field_name)
            evidence = state.field_evidence.get(field_name)
            try:
                fields[field_name] = ExtractedLeadField(
                    field_name=field_name,
                    value=value,
                    evidence=FieldEvidence(**evidence) if value and evidence else None,
                    missing_reason=None if value else f"源文本未提供 {field_name}。",
                )
            except ValueError as exc:
                state.validation_errors.append(str(exc))
                fields[field_name] = ExtractedLeadField(
                    field_name=field_name,
                    value=None,
                    missing_reason=f"字段 {field_name} 未通过证据校验。",
                )

        state.candidate = LeadExtractionCandidate(source_url=state.source_url, **fields)
        self.set_node_summary(
            state,
            "validate_required_evidence",
            {"validation_error_count": len(state.validation_errors)},
        )
        return state

    def output_shadow_staging_lead(self, state: LeadExtractionGraphState) -> LeadExtractionGraphState:
        self.mark("output_shadow_staging_lead")
        output_table = self.boundary.validate_output_table("shadow_staging_lead_candidates")
        state.audit.update(
            {
                "writes_core_tables": False,
                "output_table": output_table,
                "written_tables": [output_table],
                "candidate_count": 1 if state.candidate else 0,
                "source_urls": [state.source_url],
            }
        )
        self.set_node_summary(
            state,
            "output_shadow_staging_lead",
            {"candidate_count": 1 if state.candidate else 0},
        )
        return state

    def run(self, state: LeadExtractionGraphState) -> LeadExtractionGraphResult:
        invoked_state = self.compiled_graph.invoke(state)
        state = self._state_from_graph_result(invoked_state)
        output = LeadExtractionAgentOutput(
            schema_version="phase4.agent.lead_extraction.v1",
            extraction_run_id=state.extraction_run_id,
            agent_mode="shadow",
            candidates=[state.candidate] if state.candidate else [],
            validation_errors=state.validation_errors,
            audit=state.audit,
        )
        return LeadExtractionGraphResult(output=output, executed_nodes=list(self.executed_nodes))

    def _state_from_graph_result(self, result: LeadExtractionGraphState | dict[str, Any]) -> LeadExtractionGraphState:
        if isinstance(result, LeadExtractionGraphState):
            return result
        return LeadExtractionGraphState(
            extraction_run_id=result["extraction_run_id"],
            source_url=result["source_url"],
            source_content=result["source_content"],
            agent_mode=result.get("agent_mode") or "shadow",
            raw_fields=dict(result.get("raw_fields") or {}),
            field_evidence=dict(result.get("field_evidence") or {}),
            candidate=(
                result["candidate"]
                if isinstance(result.get("candidate"), LeadExtractionCandidate)
                else LeadExtractionCandidate(**result["candidate"])
                if result.get("candidate")
                else None
            ),
            validation_errors=list(result.get("validation_errors") or []),
            audit=dict(result.get("audit") or {}),
        )

    @staticmethod
    def normalize_text(text: str) -> str:
        return " ".join(text.split())

    @staticmethod
    def first_match(pattern: re.Pattern[str], text: str) -> str | None:
        match = pattern.search(text)
        return match.group(0).rstrip(".") if match else None

    @staticmethod
    def extract_phone(text: str) -> str | None:
        match = PHONE_PATTERN.search(text)
        return " ".join(match.group(0).split()) if match else None

    @staticmethod
    def extract_company_name(text: str) -> str | None:
        match = re.search(r"([A-Z][A-Za-z0-9& .'-]{2,80}?)(?:\s+exports|\s+sells|\s+is\s+)", text)
        return match.group(1).strip(" .") if match else None

    @staticmethod
    def extract_country(text: str) -> str | None:
        known_countries = ("United Arab Emirates", "Russia", "Kazakhstan", "Georgia", "China")
        for country in known_countries:
            if country.lower() in text.lower():
                return country
        return None

    @staticmethod
    def extract_city(text: str) -> str | None:
        match = re.search(r"(?:Located in|location[:：]?)\s+([A-Z][A-Za-z .'-]+?)(?:,|\.|$)", text)
        return match.group(1).strip(" .") if match else None

    @staticmethod
    def extract_vehicle_interest(text: str) -> str | None:
        vehicle_names = []
        for name in ("Toyota Land Cruiser", "Lexus LX", "Mercedes-Benz G-Class", "BMW X7", "Range Rover"):
            if name.lower() in text.lower():
                vehicle_names.append(name)
        return ", ".join(vehicle_names) if vehicle_names else None

    @staticmethod
    def extract_export_intent(text: str) -> str | None:
        match = re.search(r"(arrange export documentation and shipping)", text, flags=re.IGNORECASE)
        return match.group(1) if match else None

    @staticmethod
    def find_evidence(text: str, value: str | None) -> dict[str, str] | None:
        if not value:
            return None
        value_index = text.lower().find(value.lower())
        if value_index < 0 and "," in value:
            for part in [item.strip() for item in value.split(",") if item.strip()]:
                value_index = text.lower().find(part.lower())
                if value_index >= 0:
                    value = part
                    break
        if value_index < 0:
            return None
        start = max(0, value_index - 80)
        end = min(len(text), value_index + len(value) + 120)
        return {"reference": "source_content", "quote": text[start:end].strip()}
