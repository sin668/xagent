from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from langgraph.graph import END, StateGraph

from app.adapters.api_contract import ApiContractBoundary
from app.schemas.lead_extraction import (
    ExtractedContact,
    ExtractedLeadField,
    FieldEvidence,
    LeadExtractionAgentOutput,
    LeadExtractionCandidate,
    LeadExtractionFieldName,
)
from app.services.agent_logging import run_logged_node
from app.services.llm_client import LLMClient
from app.services.llm_prompt_repository import LLMPromptRepository, LLMPromptTemplateNotFound


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
    raw_candidate_payloads: list[dict[str, Any]] = field(default_factory=list)
    field_evidence: dict[str, dict[str, str] | None] = field(default_factory=dict)
    candidate_evidence_payloads: list[dict[str, dict[str, str] | None]] = field(default_factory=list)
    candidate: LeadExtractionCandidate | None = None
    candidates: list[LeadExtractionCandidate] = field(default_factory=list)
    validation_errors: list[str] = field(default_factory=list)
    audit: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class LeadExtractionGraphResult:
    output: LeadExtractionAgentOutput
    executed_nodes: list[str]


class LLMLeadFieldExtractor:
    def __init__(self, *, llm_client: LLMClient | None = None, prompt_repository: LLMPromptRepository | None = None) -> None:
        self.llm_client = llm_client or LLMClient()
        self.prompt_repository = prompt_repository or LLMPromptRepository()
        self.last_audit: dict[str, Any] = {}

    def extract(self, *, source_url: str, source_content: str) -> dict[str, Any]:
        task_type = "LEAD_EXTRACTION"
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
            user_prompt=prompt.render_user_prompt({"source_url": source_url, "source_content": source_content}),
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
            return {}
        output = result.output_json if isinstance(result.output_json, dict) else {}
        leads = output.get("leads")
        if isinstance(leads, list):
            return {"leads": [item for item in leads if isinstance(item, dict)]}
        fields = output.get("fields") if isinstance(output.get("fields"), dict) else {}
        extracted: dict[str, str | None] = {}
        for field_name in FIELD_NAMES:
            value = fields.get(field_name)
            extracted[field_name] = str(value).strip() if value not in (None, "") else None
        contacts = output.get("contacts")
        if isinstance(contacts, list):
            extracted["contacts"] = [item for item in contacts if isinstance(item, dict)]  # type: ignore[assignment]
        return extracted


class LeadExtractionGraphRunner:
    agent_type = "lead_extraction"

    def __init__(
        self,
        *,
        llm_field_extractor: LLMLeadFieldExtractor | None = None,
        prompt_repository: LLMPromptRepository | None = None,
        boundary: ApiContractBoundary | None = None,
    ) -> None:
        self.llm_field_extractor = llm_field_extractor or LLMLeadFieldExtractor(prompt_repository=prompt_repository)
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
        if state.agent_mode not in {"active", "shadow"}:
            raise ValueError("Lead Extraction agent_mode 只允许 active 或 shadow。")
        if not state.source_content.strip():
            raise ValueError("Lead Extraction 需要输入公开来源文本或来源内容。")
        state.audit.update({"agent_mode": state.agent_mode, "source_url": state.source_url})
        self.set_node_summary(state, "load_source_content", {"content_length": len(state.source_content)})
        return state

    def extract_candidate_fields(self, state: LeadExtractionGraphState) -> LeadExtractionGraphState:
        self.mark("extract_candidate_fields")
        text = self.normalize_text(state.source_content)
        emails = self.all_matches(EMAIL_PATTERN, text)
        phones = self.extract_phones(text)
        rule_fields: dict[str, str | None] = {
            "company_name": self.extract_company_name(text),
            "email": emails[0] if emails else None,
            "phone": phones[0] if phones else None,
            "country": self.extract_country(text),
            "city": self.extract_city(text),
            "vehicle_interest": self.extract_vehicle_interest(text),
            "export_intent": self.extract_export_intent(text),
            "website": self.first_match(URL_PATTERN, text) or state.source_url,
        }
        rule_contacts = [
            *[{"contact_type": "email", "value": value} for value in emails],
            *[{"contact_type": "phone", "value": value} for value in phones],
        ]
        llm_output = self.llm_field_extractor.extract(source_url=state.source_url, source_content=state.source_content)
        state.audit["llm_field_extractor"] = dict(self.llm_field_extractor.last_audit)
        state.raw_candidate_payloads = self.normalize_candidate_payloads(llm_output, rule_fields, rule_contacts)
        state.raw_fields = dict(state.raw_candidate_payloads[0]["fields"]) if state.raw_candidate_payloads else {}
        self.set_node_summary(
            state,
            "extract_candidate_fields",
            {
                "candidate_count": len(state.raw_candidate_payloads),
                "contact_count": sum(len(item.get("contacts") or []) for item in state.raw_candidate_payloads),
                "filled_field_count": len([value for value in state.raw_fields.values() if value]),
            },
        )
        return state

    def map_field_evidence(self, state: LeadExtractionGraphState) -> LeadExtractionGraphState:
        self.mark("map_field_evidence")
        text = self.normalize_text(state.source_content)
        state.candidate_evidence_payloads = []
        for payload in state.raw_candidate_payloads:
            evidence_payload = {}
            fields = payload.get("fields") if isinstance(payload.get("fields"), dict) else {}
            for field_name in FIELD_NAMES:
                value = fields.get(field_name)
                evidence_payload[field_name] = self.find_evidence(text, value)
            state.candidate_evidence_payloads.append(evidence_payload)
        state.field_evidence = dict(state.candidate_evidence_payloads[0]) if state.candidate_evidence_payloads else {}
        self.set_node_summary(
            state,
            "map_field_evidence",
            {"evidence_count": sum(1 for payload in state.candidate_evidence_payloads for item in payload.values() if item)},
        )
        return state

    def validate_required_evidence(self, state: LeadExtractionGraphState) -> LeadExtractionGraphState:
        self.mark("validate_required_evidence")
        state.validation_errors = []
        state.candidates = []
        for index, payload in enumerate(state.raw_candidate_payloads):
            raw_fields = payload.get("fields") if isinstance(payload.get("fields"), dict) else {}
            evidence_payload = (
                state.candidate_evidence_payloads[index]
                if index < len(state.candidate_evidence_payloads)
                else {}
            )
            fields: dict[str, ExtractedLeadField] = {}
            for field_name in FIELD_NAMES:
                value = raw_fields.get(field_name)
                evidence = evidence_payload.get(field_name)
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
            contacts = self.build_contacts(
                payload.get("contacts") if isinstance(payload.get("contacts"), list) else [],
                text=self.normalize_text(state.source_content),
            )
            state.candidates.append(LeadExtractionCandidate(source_url=state.source_url, **fields, contacts=contacts))
        state.candidate = state.candidates[0] if state.candidates else None
        self.set_node_summary(
            state,
            "validate_required_evidence",
            {"candidate_count": len(state.candidates), "validation_error_count": len(state.validation_errors)},
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
                "candidate_count": len(state.candidates),
                "source_urls": [state.source_url],
            }
        )
        self.set_node_summary(
            state,
            "output_shadow_staging_lead",
            {"candidate_count": len(state.candidates)},
        )
        return state

    def run(self, state: LeadExtractionGraphState) -> LeadExtractionGraphResult:
        invoked_state = self.compiled_graph.invoke(state)
        state = self._state_from_graph_result(invoked_state)
        output = LeadExtractionAgentOutput(
            schema_version="phase4.agent.lead_extraction.v1",
            extraction_run_id=state.extraction_run_id,
            agent_mode=state.agent_mode,
            candidates=state.candidates,
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
            raw_candidate_payloads=list(result.get("raw_candidate_payloads") or []),
            field_evidence=dict(result.get("field_evidence") or {}),
            candidate_evidence_payloads=list(result.get("candidate_evidence_payloads") or []),
            candidate=(
                result["candidate"]
                if isinstance(result.get("candidate"), LeadExtractionCandidate)
                else LeadExtractionCandidate(**result["candidate"])
                if result.get("candidate")
                else None
            ),
            candidates=[
                item if isinstance(item, LeadExtractionCandidate) else LeadExtractionCandidate(**item)
                for item in list(result.get("candidates") or [])
            ],
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
    def all_matches(pattern: re.Pattern[str], text: str) -> list[str]:
        return LeadExtractionGraphRunner.unique([match.group(0).rstrip(".") for match in pattern.finditer(text)])

    @staticmethod
    def extract_phone(text: str) -> str | None:
        match = PHONE_PATTERN.search(text)
        return " ".join(match.group(0).split()) if match else None

    @staticmethod
    def extract_phones(text: str) -> list[str]:
        return LeadExtractionGraphRunner.unique([" ".join(match.group(0).split()) for match in PHONE_PATTERN.finditer(text)])

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

    @classmethod
    def normalize_candidate_payloads(
        cls,
        llm_output: dict[str, Any],
        rule_fields: dict[str, str | None],
        rule_contacts: list[dict[str, str]],
    ) -> list[dict[str, Any]]:
        leads = llm_output.get("leads") if isinstance(llm_output.get("leads"), list) else None
        if leads:
            payloads = []
            for lead in leads:
                fields = lead.get("fields") if isinstance(lead.get("fields"), dict) else lead
                normalized_fields = {
                    field_name: cls.clean_value(fields.get(field_name)) or rule_fields.get(field_name)
                    for field_name in FIELD_NAMES
                }
                lead_contacts = lead.get("contacts") if isinstance(lead.get("contacts"), list) else []
                payloads.append(
                    {
                        "fields": normalized_fields,
                        "contacts": cls.merge_contacts(
                            cls.contacts_from_fields(normalized_fields),
                            cls.normalize_raw_contacts(lead_contacts),
                        ),
                    }
                )
            return payloads

        llm_fields = {
            field_name: cls.clean_value(llm_output.get(field_name)) or rule_fields.get(field_name)
            for field_name in FIELD_NAMES
        }
        llm_contacts = llm_output.get("contacts") if isinstance(llm_output.get("contacts"), list) else []
        return [
            {
                "fields": llm_fields,
                "contacts": cls.merge_contacts(
                    cls.normalize_raw_contacts(llm_contacts),
                    rule_contacts,
                    cls.contacts_from_fields(llm_fields),
                ),
            }
        ]

    @staticmethod
    def clean_value(value: object) -> str | None:
        if value in (None, ""):
            return None
        cleaned = str(value).strip()
        return cleaned or None

    @classmethod
    def contacts_from_fields(cls, fields: dict[str, str | None]) -> list[dict[str, str]]:
        contacts = []
        if fields.get("email"):
            contacts.append({"contact_type": "email", "value": str(fields["email"])})
        if fields.get("phone"):
            contacts.append({"contact_type": "phone", "value": str(fields["phone"])})
        return contacts

    @classmethod
    def normalize_raw_contacts(cls, contacts: list[Any]) -> list[dict[str, str]]:
        normalized = []
        for contact in contacts:
            if not isinstance(contact, dict):
                continue
            contact_type = cls.normalize_contact_type(contact.get("contact_type") or contact.get("type"))
            value = cls.clean_value(contact.get("value"))
            if not contact_type or not value:
                continue
            normalized.append(
                {
                    "contact_type": str(contact_type).strip().lower(),
                    "value": value,
                    "usage": str(contact.get("usage") or "source_public_contact"),
                }
            )
        return normalized

    @staticmethod
    def normalize_contact_type(value: object) -> str:
        normalized = str(value or "").strip().lower()
        return {
            "vkontakte": "vk",
            "вконтакте": "vk",
            "odnoklassniki": "ok",
            "одноклассники": "ok",
        }.get(normalized, normalized)

    @classmethod
    def merge_contacts(cls, *groups: list[dict[str, str]]) -> list[dict[str, str]]:
        merged = []
        seen: set[tuple[str, str]] = set()
        for group in groups:
            for contact in group:
                contact_type = str(contact.get("contact_type") or contact.get("type") or "").strip().lower()
                value = cls.clean_value(contact.get("value"))
                if not contact_type or not value:
                    continue
                key = (contact_type, value.lower())
                if key in seen:
                    continue
                seen.add(key)
                merged.append({"contact_type": contact_type, "value": value, "usage": contact.get("usage") or "source_public_contact"})
        return merged

    @classmethod
    def build_contacts(cls, raw_contacts: list[Any], *, text: str) -> list[ExtractedContact]:
        contacts = []
        for raw_contact in cls.normalize_raw_contacts(raw_contacts):
            value = raw_contact["value"]
            evidence = cls.find_evidence(text, value)
            contacts.append(
                ExtractedContact(
                    contact_type=raw_contact["contact_type"],
                    value=value,
                    usage=raw_contact.get("usage") or "source_public_contact",
                    evidence=FieldEvidence(**evidence) if evidence else None,
                )
            )
        return contacts

    @staticmethod
    def unique(values: list[str]) -> list[str]:
        result = []
        seen = set()
        for value in values:
            normalized = value.strip()
            key = normalized.lower()
            if not normalized or key in seen:
                continue
            seen.add(key)
            result.append(normalized)
        return result
