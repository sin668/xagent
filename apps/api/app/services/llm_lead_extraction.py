from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import CandidateUrl
from app.models.enums import AITaskType, ChannelRiskLevel, CustomerGrade, CustomerType
from app.services.audit_risk import AuditRiskLogService
from app.services.failed_cases import FailedCaseService
from app.services.rag_prompt_context import RAGPromptContextService
from app.services.raw_collection import RawCollectionService
from app.services.staging_leads import StagingLeadService


@dataclass(frozen=True)
class LLMLeadExtractionResult:
    staging_lead: object


class LLMLeadExtractionService:
    PROMPT_VERSION = "lead-extraction-v1"
    DEFAULT_MODEL_NAME = "Unknown"
    REQUIRED_CONTACT_KEYS = ("emails", "phones", "whatsapp", "telegram", "wechat", "website_forms")

    def __init__(self, session: Session) -> None:
        self.session = session
        self.raw_collection_service = RawCollectionService(session)
        self.staging_service = StagingLeadService(session)
        self.audit_service = AuditRiskLogService(session)
        self.failed_case_service = FailedCaseService(session)
        self.rag_context_service = RAGPromptContextService(session)

    @classmethod
    def normalize_customer_type(cls, value: object) -> str:
        if value is None:
            return CustomerType.UNKNOWN.value
        normalized = str(value).strip().lower()
        if not normalized:
            return CustomerType.UNKNOWN.value
        normalized_key = normalized.replace("-", "_")
        normalized_space = normalized_key.replace("_", " ")
        aliases = {
            "未知": CustomerType.UNKNOWN.value,
            "unknown": CustomerType.UNKNOWN.value,
            "n/a": CustomerType.UNKNOWN.value,
            "none": CustomerType.UNKNOWN.value,
            "local_dealer_secondary_dealer": CustomerType.LOCAL_DEALER_SECONDARY_DEALER.value,
            "local dealer secondary dealer": CustomerType.LOCAL_DEALER_SECONDARY_DEALER.value,
            "dealer": CustomerType.LOCAL_DEALER_SECONDARY_DEALER.value,
            "dealership": CustomerType.LOCAL_DEALER_SECONDARY_DEALER.value,
            "car dealer": CustomerType.LOCAL_DEALER_SECONDARY_DEALER.value,
            "auto dealer": CustomerType.LOCAL_DEALER_SECONDARY_DEALER.value,
            "secondary dealer": CustomerType.LOCAL_DEALER_SECONDARY_DEALER.value,
            "local dealer": CustomerType.LOCAL_DEALER_SECONDARY_DEALER.value,
            "dealership_directory": CustomerType.DEALERSHIP_DIRECTORY.value,
            "dealership directory": CustomerType.DEALERSHIP_DIRECTORY.value,
            "dealer_directory": CustomerType.DEALERSHIP_DIRECTORY.value,
            "dealer directory": CustomerType.DEALERSHIP_DIRECTORY.value,
            "directory": CustomerType.DEALERSHIP_DIRECTORY.value,
            "marketplace": CustomerType.MARKETPLACE.value,
            "auto_marketplace": CustomerType.MARKETPLACE.value,
            "auto marketplace": CustomerType.MARKETPLACE.value,
            "classifieds": CustomerType.MARKETPLACE.value,
            "personal_buyer": CustomerType.PERSONAL_BUYER.value,
            "personal buyer": CustomerType.PERSONAL_BUYER.value,
            "individual": CustomerType.PERSONAL_BUYER.value,
            "private buyer": CustomerType.PERSONAL_BUYER.value,
            "kol_auto_blogger": CustomerType.KOL_AUTO_BLOGGER.value,
            "kol auto blogger": CustomerType.KOL_AUTO_BLOGGER.value,
            "blogger": CustomerType.KOL_AUTO_BLOGGER.value,
            "auto blogger": CustomerType.KOL_AUTO_BLOGGER.value,
            "non_target": CustomerType.NON_TARGET.value,
            "non target": CustomerType.NON_TARGET.value,
            "invalid": CustomerType.NON_TARGET.value,
        }
        candidate = aliases.get(normalized_key) or aliases.get(normalized_space) or normalized_key
        try:
            CustomerType(candidate)
        except ValueError:
            return CustomerType.UNKNOWN.value
        return candidate

    @classmethod
    def normalize_extraction_output(cls, output: dict) -> dict:
        normalized = deepcopy(output or {})
        normalized.setdefault("schema_version", "poc-ai-output-v1")
        normalized.setdefault("task_type", "lead_extraction")
        normalized.setdefault("risk_blocked", False)
        normalized.setdefault("risk_block_reason", None)
        normalized.setdefault("source", {})
        normalized.setdefault("lead", {})
        normalized.setdefault("audit", {})

        lead = normalized["lead"]
        lead["customer_name"] = (lead.get("customer_name") or "Unknown").strip() or "Unknown"
        lead["country"] = (lead.get("country") or "Unknown").strip() or "Unknown"
        lead["city"] = (lead.get("city") or "Unknown").strip() or "Unknown"
        reported_customer_type = lead.get("customer_type")
        lead["customer_type"] = cls.normalize_customer_type(reported_customer_type)
        if str(reported_customer_type or "").strip() and str(reported_customer_type).strip() != lead["customer_type"]:
            audit = normalized.setdefault("audit", {})
            audit["llm_reported_customer_type"] = reported_customer_type
            audit["customer_type_canonicalized"] = True
        lead["activity_signal"] = lead.get("activity_signal") or "Unknown"
        lead["scale_signal"] = lead.get("scale_signal") or "Unknown"
        lead["import_used_relevance"] = lead.get("import_used_relevance") or "unknown"
        lead["source_evidence"] = lead.get("source_evidence") or []
        lead["missing_fields"] = lead.get("missing_fields") or []

        contacts = lead.get("contacts") or {}
        lead["contacts"] = {
            key: [str(item).strip() for item in contacts.get(key, []) if str(item).strip()]
            for key in cls.REQUIRED_CONTACT_KEYS
        }

        audit = normalized["audit"]
        audit["model"] = audit.get("model") or cls.DEFAULT_MODEL_NAME
        audit["prompt_version"] = audit.get("prompt_version") or cls.PROMPT_VERSION
        audit["input_saved"] = bool(audit.get("input_saved", True))
        audit["output_saved"] = bool(audit.get("output_saved", True))
        audit["executed_at"] = audit.get("executed_at") or datetime.utcnow().isoformat()
        return normalized

    @classmethod
    def validate_extraction_output(
        cls,
        output: dict,
        *,
        public_text: str,
        expected_source_url: str,
        channel_risk_level: str | ChannelRiskLevel,
    ) -> dict:
        normalized = cls.normalize_extraction_output(output)
        risk = ChannelRiskLevel(channel_risk_level)

        if normalized.get("schema_version") != "poc-ai-output-v1":
            raise ValueError("LLM 输出 schema_version 不正确。")
        if normalized.get("task_type") != "lead_extraction":
            raise ValueError("LLM 输出 task_type 必须为 lead_extraction。")

        source = normalized["source"]
        if not cls.source_urls_match(source.get("source_url"), expected_source_url):
            raise ValueError("LLM 输出 source_url 与候选来源不一致。")
        source["source_url"] = expected_source_url
        if risk in {ChannelRiskLevel.HIGH, ChannelRiskLevel.FORBIDDEN}:
            raise ValueError("High/Forbidden 来源不得写入 staging，仅允许政策复核或人工小样本。")
        if normalized.get("risk_blocked"):
            raise ValueError(normalized.get("risk_block_reason") or "LLM 输出已标记风险阻断。")

        lead = normalized["lead"]
        try:
            CustomerType(lead["customer_type"])
        except ValueError as exc:
            raise ValueError("LLM 输出 customer_type 不在允许枚举内。") from exc

        evidence_items = lead.get("source_evidence") or []
        if not evidence_items:
            raise ValueError("LLM 输出缺少来源证据，不得写入 staging。")
        for item in evidence_items:
            if not isinstance(item, dict) or not item.get("evidence_text") or not cls.source_urls_match(item.get("source_url"), expected_source_url):
                raise ValueError("LLM 来源证据必须包含 evidence_text 且 source_url 与候选来源一致。")
            item["source_url"] = expected_source_url

        public_text_lower = public_text.lower()
        for value in cls.iter_contact_values(lead.get("contacts") or {}):
            if value.lower() not in public_text_lower:
                raise ValueError(f"联系方式不在公开文本中，不得写入 staging：{value}")
        if lead["customer_name"] == "Unknown" and not cls.iter_contact_values(lead.get("contacts") or {}):
            raise ValueError("LLM 输出缺少客户名称和联系方式，不得写入 staging。")
        return normalized

    @classmethod
    def source_urls_match(cls, value: str | None, expected_source_url: str) -> bool:
        if not value:
            return False
        return cls.normalize_source_url(value) == cls.normalize_source_url(expected_source_url)

    @staticmethod
    def normalize_source_url(value: str) -> str:
        parsed = urlsplit(str(value).strip())
        scheme = (parsed.scheme or "https").lower()
        netloc = parsed.netloc.lower()
        path = parsed.path or "/"
        if path != "/":
            path = path.rstrip("/")
        query = urlencode(sorted(parse_qsl(parsed.query, keep_blank_values=True)), doseq=True)
        return urlunsplit((scheme, netloc, path, query, ""))

    @classmethod
    def iter_contact_values(cls, contacts: dict) -> list[str]:
        values: list[str] = []
        for key in cls.REQUIRED_CONTACT_KEYS:
            values.extend(str(item).strip() for item in contacts.get(key, []) if str(item).strip())
        return values

    @staticmethod
    def contacts_to_staging(contacts: dict, *, source_url: str) -> list[dict]:
        mapping = {
            "emails": "email",
            "phones": "phone",
            "whatsapp": "whatsapp",
            "telegram": "telegram",
            "wechat": "other",
            "website_forms": "website_form",
        }
        items: list[dict] = []
        for source_key, method_type in mapping.items():
            for value in contacts.get(source_key, []):
                items.append({"method_type": method_type, "value": value, "source_url": source_url})
        return items

    @staticmethod
    def evidence_to_text(source_evidence: list[dict]) -> str:
        parts = []
        for item in source_evidence:
            claim = item.get("claim") or "evidence"
            evidence_text = item.get("evidence_text") or ""
            parts.append(f"{claim}: {evidence_text}")
        return "；".join(parts)

    @staticmethod
    def truncate_for_column(value: str | None, max_length: int) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip()
        if not normalized:
            return None
        return normalized[:max_length]

    @classmethod
    def build_staging_payload(
        cls,
        output: dict,
        *,
        public_text: str,
        expected_source_url: str,
        channel_risk_level: str | ChannelRiskLevel,
    ) -> dict:
        normalized = cls.validate_extraction_output(
            output,
            public_text=public_text,
            expected_source_url=expected_source_url,
            channel_risk_level=channel_risk_level,
        )
        lead = normalized["lead"]
        return {
            "customer_name": cls.truncate_for_column(lead["customer_name"], 255) or "Unknown",
            "country": cls.truncate_for_column(lead["country"], 80) or "Unknown",
            "city": None if lead["city"] == "Unknown" else cls.truncate_for_column(lead["city"], 120),
            "customer_type": lead["customer_type"],
            "contacts_json": cls.contacts_to_staging(lead["contacts"], source_url=expected_source_url),
            "activity_level": cls.truncate_for_column(lead["activity_signal"], 80),
            "scale_signal": lead["scale_signal"],
            "import_used_car_relevance": cls.truncate_for_column(lead["import_used_relevance"], 120),
            "source_evidence": cls.evidence_to_text(lead["source_evidence"]),
            "recommended_grade": CustomerGrade.WATCH,
            "recommended_reason": "等待 LLM 分级校验；本任务仅完成公开文本抽取。",
            "missing_fields": lead["missing_fields"],
        }

    @staticmethod
    def build_extraction_audit_input(
        *,
        candidate_url_id: UUID,
        source_url: str,
        public_text: str,
        page_snapshot_id: UUID | None = None,
        rag_context: dict | None = None,
        agent_task_run_id: UUID | str | None = None,
    ) -> dict:
        payload = {
            "candidate_url_id": str(candidate_url_id),
            "source_url": source_url,
            "public_text_excerpt": public_text[:2000],
            "rag_context": rag_context
            or {
                "context_status": "empty_context",
                "knowledge_item_refs": [],
                "context_text": "",
            },
        }
        if agent_task_run_id is not None:
            payload["agent_task_run_id"] = str(agent_task_run_id)
        if page_snapshot_id is not None:
            payload["page_snapshot_id"] = str(page_snapshot_id)
        return payload

    def run_extraction(
        self,
        *,
        candidate_url_id: UUID,
        llm_output_json: dict,
        agent_task_run_id: UUID | str | None = None,
    ) -> LLMLeadExtractionResult:
        candidate = self.session.get(CandidateUrl, candidate_url_id)
        if candidate is None:
            raise ValueError("candidate URL 不存在。")
        snapshot = self.raw_collection_service.latest_page_snapshot_for_candidate(candidate.id)
        public_text = snapshot.text_excerpt or ""
        rag_context = self.rag_context_service.safe_build_context(
            task_type=AITaskType.LEAD_EXTRACTION,
            query=f"{candidate.discovery_reason}\n{public_text[:800]}",
            country=None,
            channel=candidate.source_platform.value,
            language="zh",
        )
        try:
            normalized_output = self.validate_extraction_output(
                llm_output_json,
                public_text=public_text,
                expected_source_url=candidate.url,
                channel_risk_level=candidate.source_risk_level,
            )
            staging_payload = self.build_staging_payload(
                normalized_output,
                public_text=public_text,
                expected_source_url=candidate.url,
                channel_risk_level=candidate.source_risk_level,
            )
        except ValueError as exc:
            failure_reason = str(exc)
            self.audit_service.record_ai_audit(
                task_type=AITaskType.LEAD_EXTRACTION,
                model_name=(llm_output_json.get("audit") or {}).get("model") or self.DEFAULT_MODEL_NAME,
                prompt_version=(llm_output_json.get("audit") or {}).get("prompt_version") or self.PROMPT_VERSION,
                channel_name=candidate.source_platform.value,
                output_json=llm_output_json,
                source_urls=[candidate.url],
                input_payload=self.build_extraction_audit_input(
                    candidate_url_id=candidate.id,
                    source_url=candidate.url,
                    public_text=public_text,
                    rag_context=rag_context,
                    agent_task_run_id=agent_task_run_id,
                ),
                risk_blocked=True,
                risk_block_reason=failure_reason,
            )
            self.failed_case_service.record_failed_case(
                case_type=FailedCaseService.classify_failure_reason(failure_reason),
                source_url=candidate.url,
                risk_level=candidate.source_risk_level,
                related_task_type=AITaskType.LEAD_EXTRACTION.value,
                related_object_type="candidate_url",
                related_object_id=str(candidate.id),
                failure_reason=failure_reason,
                evidence_note="LLM 抽取输出未通过 schema、证据、风险或反编造校验。",
                raw_input_ref=str(candidate.id),
                raw_output_json=llm_output_json,
                model_name=(llm_output_json.get("audit") or {}).get("model") or self.DEFAULT_MODEL_NAME,
                prompt_version=(llm_output_json.get("audit") or {}).get("prompt_version") or self.PROMPT_VERSION,
            )
            raise

        staging_lead = self.staging_service.create_staging_lead(
            candidate_url_id=candidate.id,
            source_risk_level=candidate.source_risk_level,
            **staging_payload,
        )
        self.audit_service.record_ai_audit(
            task_type=AITaskType.LEAD_EXTRACTION,
            model_name=(normalized_output.get("audit") or {}).get("model") or self.DEFAULT_MODEL_NAME,
            prompt_version=(normalized_output.get("audit") or {}).get("prompt_version") or self.PROMPT_VERSION,
            channel_name=candidate.source_platform.value,
            output_json=normalized_output,
            source_urls=[candidate.url],
            input_payload=self.build_extraction_audit_input(
                candidate_url_id=candidate.id,
                source_url=candidate.url,
                page_snapshot_id=snapshot.id,
                public_text=public_text,
                rag_context=rag_context,
                agent_task_run_id=agent_task_run_id,
            ),
            risk_blocked=False,
        )
        return LLMLeadExtractionResult(staging_lead=staging_lead)
