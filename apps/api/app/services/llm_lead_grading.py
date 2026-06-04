from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import StagingLead
from app.models.enums import (
    AITaskType,
    ChannelRiskLevel,
    CustomerGrade,
    StagingQueueStatus,
    StagingReviewStatus,
)
from app.services.audit_risk import AuditRiskLogService
from app.services.failed_cases import FailedCaseService
from app.services.llm_lead_extraction import LLMLeadExtractionService
from app.services.rag_prompt_context import RAGPromptContextService
from app.services.staging_leads import StagingLeadService


@dataclass(frozen=True)
class GradingRuleResult:
    recommended_grade: CustomerGrade
    queue_status: StagingQueueStatus
    touch_queue_allowed: bool
    requires_compliance_review: bool
    risk_flags: list[str]
    next_action: str
    suggested_handoff_team: str


@dataclass(frozen=True)
class LLMLeadGradingResult:
    staging_lead: StagingLead
    rule_result: GradingRuleResult


class LLMLeadGradingService:
    PROMPT_VERSION = "lead-grading-v1"
    DEFAULT_MODEL_NAME = "Unknown"
    NEXT_ACTIONS = {
        "enrich_more",
        "handoff_to_customer_service",
        "handoff_to_export_sales",
        "mark_invalid",
        "watch_later",
        "do_not_contact",
        "policy_review_only",
        "manual_small_sample_only",
    }
    HANDOFF_TEAMS = {"lead_ops", "customer_service", "export_sales", "compliance", "none"}

    def __init__(self, session: Session) -> None:
        self.session = session
        self.audit_service = AuditRiskLogService(session)
        self.failed_case_service = FailedCaseService(session)
        self.rag_context_service = RAGPromptContextService(session)

    @classmethod
    def normalize_grade(cls, value: object, *, has_contact: bool) -> str:
        raw = str(value or "").strip()
        normalized = raw.lower().replace("-", "_").replace(" ", "_")
        aliases = {
            "a": CustomerGrade.A.value,
            "grade_a": CustomerGrade.A.value,
            "high": CustomerGrade.A.value,
            "hot": CustomerGrade.A.value,
            "b": CustomerGrade.B.value,
            "grade_b": CustomerGrade.B.value,
            "medium": CustomerGrade.B.value,
            "interested": CustomerGrade.B.value,
            "interested_dealer": CustomerGrade.B.value,
            "qualified": CustomerGrade.B.value,
            "c": CustomerGrade.C.value,
            "grade_c": CustomerGrade.C.value,
            "low": CustomerGrade.C.value,
            "invalid": CustomerGrade.INVALID.value,
            "non_target": CustomerGrade.INVALID.value,
            "not_target": CustomerGrade.INVALID.value,
            "watch": CustomerGrade.WATCH.value,
            "watch_later": CustomerGrade.WATCH.value,
            "unknown": CustomerGrade.WATCH.value,
        }
        if not has_contact:
            explicit_without_contact = {
                "a": CustomerGrade.A.value,
                "grade_a": CustomerGrade.A.value,
                "b": CustomerGrade.B.value,
                "grade_b": CustomerGrade.B.value,
                "c": CustomerGrade.C.value,
                "grade_c": CustomerGrade.C.value,
                "invalid": CustomerGrade.INVALID.value,
                "watch": CustomerGrade.WATCH.value,
                "watch_later": CustomerGrade.WATCH.value,
            }
            return explicit_without_contact.get(normalized, CustomerGrade.WATCH.value)
        candidate = aliases.get(normalized, raw)
        try:
            return CustomerGrade(candidate).value
        except ValueError:
            return CustomerGrade.B.value if has_contact else CustomerGrade.WATCH.value

    @classmethod
    def normalize_next_action(cls, value: object, *, has_contact: bool) -> str:
        raw = str(value or "").strip()
        normalized = raw.lower().replace("-", "_").replace(" ", "_")
        aliases = {
            "handoff_to_customer_service": "handoff_to_customer_service",
            "customer_service": "handoff_to_customer_service",
            "send_to_customer_service": "handoff_to_customer_service",
            "contact_customer": "handoff_to_customer_service",
            "call_dealer_tomorrow": "handoff_to_customer_service",
            "handoff_to_export_sales": "handoff_to_export_sales",
            "export_sales": "handoff_to_export_sales",
            "sales": "handoff_to_export_sales",
            "enrich_more": "enrich_more",
            "mark_invalid": "mark_invalid",
            "watch_later": "watch_later",
            "do_not_contact": "do_not_contact",
            "policy_review_only": "policy_review_only",
            "manual_small_sample_only": "manual_small_sample_only",
        }
        if not has_contact:
            safe_without_contact = {
                "enrich_more": "enrich_more",
                "mark_invalid": "mark_invalid",
                "watch_later": "watch_later",
                "do_not_contact": "do_not_contact",
                "policy_review_only": "policy_review_only",
                "manual_small_sample_only": "manual_small_sample_only",
            }
            return safe_without_contact.get(normalized, "watch_later")
        candidate = aliases.get(normalized, raw)
        if candidate in cls.NEXT_ACTIONS:
            return candidate
        return "handoff_to_customer_service" if has_contact else "watch_later"

    @classmethod
    def normalize_handoff_team(cls, value: object, *, next_action: str, has_contact: bool) -> str:
        raw = str(value or "").strip()
        normalized = raw.lower().replace("-", "_").replace(" ", "_")
        aliases = {
            "lead_ops": "lead_ops",
            "ops": "lead_ops",
            "customer_service": "customer_service",
            "customer_support": "customer_service",
            "cs": "customer_service",
            "export_sales": "export_sales",
            "sales": "export_sales",
            "sales_team": "export_sales",
            "compliance": "compliance",
            "none": "none",
        }
        if not has_contact:
            safe_without_contact = {
                "lead_ops": "lead_ops",
                "ops": "lead_ops",
                "compliance": "compliance",
                "none": "none",
            }
            return safe_without_contact.get(normalized, "lead_ops")
        candidate = aliases.get(normalized, raw)
        if candidate in cls.HANDOFF_TEAMS:
            if next_action == "handoff_to_customer_service" and candidate == "export_sales":
                return "customer_service"
            return candidate
        if next_action == "handoff_to_export_sales":
            return "export_sales"
        return "customer_service" if has_contact else "lead_ops"

    @classmethod
    def normalize_grading_output(cls, output: dict, *, has_contact: bool = False) -> dict:
        normalized = deepcopy(output or {})
        normalized.setdefault("schema_version", "poc-ai-output-v1")
        normalized.setdefault("task_type", "lead_grading")
        normalized.setdefault("recommended_grade", CustomerGrade.WATCH.value)
        normalized.setdefault("recommended_reason", "Unknown")
        normalized.setdefault("reason_codes", [])
        normalized.setdefault("evidence_refs", [])
        normalized.setdefault("missing_fields", [])
        normalized.setdefault("next_action", "watch_later")
        normalized.setdefault("suggested_handoff_team", "lead_ops")
        normalized.setdefault("touch_queue_allowed", False)
        normalized.setdefault("touch_channel_limit", "manual_only_low_medium_risk")
        normalized.setdefault("compliance_review_required", False)
        normalized.setdefault("human_review_required", True)
        normalized.setdefault("risk_flags", [])
        normalized.setdefault("audit", {})
        audit = normalized["audit"]
        reported_grade = normalized.get("recommended_grade")
        canonical_grade = cls.normalize_grade(reported_grade, has_contact=has_contact)
        if str(reported_grade or "").strip() != canonical_grade:
            audit["llm_reported_recommended_grade"] = reported_grade
            audit["recommended_grade_canonicalized"] = True
        normalized["recommended_grade"] = canonical_grade

        reported_next_action = normalized.get("next_action")
        canonical_next_action = cls.normalize_next_action(reported_next_action, has_contact=has_contact)
        if str(reported_next_action or "").strip() != canonical_next_action:
            audit["llm_reported_next_action"] = reported_next_action
            audit["next_action_canonicalized"] = True
        normalized["next_action"] = canonical_next_action

        reported_handoff_team = normalized.get("suggested_handoff_team")
        canonical_handoff_team = cls.normalize_handoff_team(
            reported_handoff_team,
            next_action=canonical_next_action,
            has_contact=has_contact,
        )
        if str(reported_handoff_team or "").strip() != canonical_handoff_team:
            audit["llm_reported_suggested_handoff_team"] = reported_handoff_team
            audit["suggested_handoff_team_canonicalized"] = True
        normalized["suggested_handoff_team"] = canonical_handoff_team

        audit["model"] = audit.get("model") or cls.DEFAULT_MODEL_NAME
        audit["prompt_version"] = audit.get("prompt_version") or cls.PROMPT_VERSION
        audit["input_saved"] = bool(audit.get("input_saved", True))
        audit["output_saved"] = bool(audit.get("output_saved", True))
        audit["executed_at"] = audit.get("executed_at") or datetime.utcnow().isoformat()
        return normalized

    @classmethod
    def validate_grading_output(cls, output: dict, *, expected_source_url: str, has_contact: bool = False) -> dict:
        normalized = cls.normalize_grading_output(output, has_contact=has_contact)
        if normalized.get("schema_version") != "poc-ai-output-v1":
            raise ValueError("LLM 分级输出 schema_version 不正确。")
        if normalized.get("task_type") != "lead_grading":
            raise ValueError("LLM 分级输出 task_type 必须为 lead_grading。")
        try:
            CustomerGrade(normalized["recommended_grade"])
        except ValueError as exc:
            raise ValueError("LLM 分级输出 recommended_grade 不在允许枚举内。") from exc
        if normalized["next_action"] not in cls.NEXT_ACTIONS:
            raise ValueError("LLM 分级输出 next_action 不在允许枚举内。")
        if normalized["suggested_handoff_team"] not in cls.HANDOFF_TEAMS:
            raise ValueError("LLM 分级输出 suggested_handoff_team 不在允许枚举内。")

        evidence_refs = normalized.get("evidence_refs") or []
        if not evidence_refs:
            raise ValueError("推荐原因必须引用证据，evidence_refs 不得为空。")
        for item in evidence_refs:
            if (
                not isinstance(item, dict)
                or not item.get("evidence_text")
                or not LLMLeadExtractionService.source_urls_match(item.get("source_url"), expected_source_url)
            ):
                raise ValueError("推荐原因必须引用证据，且 evidence_refs.source_url 必须与来源一致。")
            item["source_url"] = expected_source_url
        return normalized

    @classmethod
    def apply_hard_rules(
        cls,
        output: dict,
        *,
        source_risk_level: str | ChannelRiskLevel,
        review_status: str | StagingReviewStatus,
        has_evidence: bool,
        has_contact: bool,
        do_not_contact: bool,
    ) -> GradingRuleResult:
        normalized = cls.normalize_grading_output(output, has_contact=has_contact)
        grade = CustomerGrade(normalized["recommended_grade"])
        risk = ChannelRiskLevel(source_risk_level)
        review = StagingReviewStatus(review_status)
        risk_flags = list(dict.fromkeys(str(item) for item in normalized.get("risk_flags", []) if str(item).strip()))
        touch_queue_allowed = bool(normalized.get("touch_queue_allowed"))
        requires_compliance_review = bool(normalized.get("compliance_review_required"))
        queue_status = StagingQueueStatus.PENDING_REVIEW

        if grade in {CustomerGrade.INVALID, CustomerGrade.WATCH}:
            touch_queue_allowed = False
            queue_status = StagingQueueStatus.NOT_ELIGIBLE
        elif grade == CustomerGrade.A:
            touch_queue_allowed = False
            queue_status = StagingQueueStatus.PENDING_REVIEW
        elif grade in {CustomerGrade.B, CustomerGrade.C} and touch_queue_allowed:
            queue_status = StagingQueueStatus.ELIGIBLE

        if grade == CustomerGrade.C:
            requires_compliance_review = True
            if "c_grade_requires_compliance_review" not in risk_flags:
                risk_flags.append("c_grade_requires_compliance_review")

        if risk in {ChannelRiskLevel.HIGH, ChannelRiskLevel.FORBIDDEN}:
            touch_queue_allowed = False
            queue_status = StagingQueueStatus.BLOCKED
            flag = "high_unverified_blocked" if risk == ChannelRiskLevel.HIGH else "forbidden_channel_blocked"
            if flag not in risk_flags:
                risk_flags.append(flag)
        elif review == StagingReviewStatus.NEEDS_SECONDARY_VERIFICATION:
            touch_queue_allowed = False
            queue_status = StagingQueueStatus.BLOCKED
            if "secondary_verification_required" not in risk_flags:
                risk_flags.append("secondary_verification_required")

        if not has_evidence:
            touch_queue_allowed = False
            queue_status = StagingQueueStatus.NOT_ELIGIBLE
            if "missing_source_evidence" not in risk_flags:
                risk_flags.append("missing_source_evidence")
        if not has_contact:
            touch_queue_allowed = False
            if queue_status == StagingQueueStatus.ELIGIBLE:
                queue_status = StagingQueueStatus.PENDING_REVIEW
            if "missing_contact" not in risk_flags:
                risk_flags.append("missing_contact")
        if do_not_contact:
            touch_queue_allowed = False
            queue_status = StagingQueueStatus.NOT_ELIGIBLE
            if "do_not_contact_blocked" not in risk_flags:
                risk_flags.append("do_not_contact_blocked")

        return GradingRuleResult(
            recommended_grade=grade,
            queue_status=queue_status,
            touch_queue_allowed=touch_queue_allowed,
            requires_compliance_review=requires_compliance_review,
            risk_flags=risk_flags,
            next_action=normalized["next_action"],
            suggested_handoff_team=normalized["suggested_handoff_team"],
        )

    @staticmethod
    def rule_result_to_dict(result: GradingRuleResult) -> dict:
        return {
            "recommended_grade": result.recommended_grade.value,
            "queue_status": result.queue_status.value,
            "touch_queue_allowed": result.touch_queue_allowed,
            "requires_compliance_review": result.requires_compliance_review,
            "risk_flags": result.risk_flags,
            "next_action": result.next_action,
            "suggested_handoff_team": result.suggested_handoff_team,
        }

    @staticmethod
    def build_grading_audit_input(
        *,
        staging_lead_id: UUID,
        source_url: str,
        do_not_contact: bool,
        rag_context: dict | None = None,
        agent_task_run_id: UUID | str | None = None,
    ) -> dict:
        payload = {
            "staging_lead_id": str(staging_lead_id),
            "source_url": source_url,
            "do_not_contact": do_not_contact,
            "rag_context": rag_context
            or {
                "context_status": "empty_context",
                "knowledge_item_refs": [],
                "context_text": "",
            },
        }
        if agent_task_run_id is not None:
            payload["agent_task_run_id"] = str(agent_task_run_id)
        return payload

    def run_grading(
        self,
        *,
        staging_lead_id: UUID,
        llm_output_json: dict,
        do_not_contact: bool = False,
        agent_task_run_id: UUID | str | None = None,
    ) -> LLMLeadGradingResult:
        lead = self.session.get(StagingLead, staging_lead_id)
        if lead is None:
            raise ValueError("staging lead 不存在。")
        candidate = lead.candidate_url
        if candidate is None:
            raise ValueError("staging lead 缺少 candidate URL。")
        rag_context = self.rag_context_service.safe_build_context(
            task_type=AITaskType.LEAD_GRADING,
            query="\n".join(
                str(item)
                for item in [
                    lead.customer_name,
                    lead.country,
                    lead.city,
                    lead.source_evidence,
                    lead.scale_signal,
                    lead.import_used_car_relevance,
                ]
                if item
            ),
            country=lead.country if lead.country != "Unknown" else None,
            channel=candidate.source_platform.value,
            language="zh",
        )
        try:
            has_contact = StagingLeadService.has_contact(lead.contacts_json)
            normalized = self.validate_grading_output(
                llm_output_json,
                expected_source_url=candidate.url,
                has_contact=has_contact,
            )
            rule_result = self.apply_hard_rules(
                normalized,
                source_risk_level=candidate.source_risk_level,
                review_status=lead.review_status,
                has_evidence=StagingLeadService.evidence_status(lead.source_evidence) == "present",
                has_contact=has_contact,
                do_not_contact=do_not_contact,
            )
        except ValueError as exc:
            failure_reason = str(exc)
            self.audit_service.record_ai_audit(
                task_type=AITaskType.LEAD_GRADING,
                model_name=(llm_output_json.get("audit") or {}).get("model") or self.DEFAULT_MODEL_NAME,
                prompt_version=(llm_output_json.get("audit") or {}).get("prompt_version") or self.PROMPT_VERSION,
                channel_name=candidate.source_platform.value,
                output_json=llm_output_json,
                source_urls=[candidate.url],
                input_payload=self.build_grading_audit_input(
                    staging_lead_id=lead.id,
                    source_url=candidate.url,
                    do_not_contact=do_not_contact,
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
                related_task_type=AITaskType.LEAD_GRADING.value,
                related_object_type="staging_lead",
                related_object_id=str(lead.id),
                failure_reason=failure_reason,
                evidence_note="LLM 分级输出未通过 schema、证据或硬规则校验。",
                raw_input_ref=str(lead.id),
                raw_output_json=llm_output_json,
                model_name=(llm_output_json.get("audit") or {}).get("model") or self.DEFAULT_MODEL_NAME,
                prompt_version=(llm_output_json.get("audit") or {}).get("prompt_version") or self.PROMPT_VERSION,
            )
            raise

        lead.recommended_grade = rule_result.recommended_grade
        lead.recommended_reason = normalized["recommended_reason"]
        lead.missing_fields = normalized.get("missing_fields") or []
        lead.queue_status = rule_result.queue_status
        lead.requires_compliance_review = rule_result.requires_compliance_review
        lead.updated_at = datetime.utcnow()
        self.audit_service.record_ai_audit(
            task_type=AITaskType.LEAD_GRADING,
            model_name=normalized["audit"]["model"],
            prompt_version=normalized["audit"]["prompt_version"],
            channel_name=candidate.source_platform.value,
            output_json={
                "llm_output": normalized,
                "rule_validation_result": self.rule_result_to_dict(rule_result),
            },
            source_urls=[candidate.url],
            input_payload=self.build_grading_audit_input(
                staging_lead_id=lead.id,
                source_url=candidate.url,
                do_not_contact=do_not_contact,
                rag_context=rag_context,
                agent_task_run_id=agent_task_run_id,
            ),
            risk_blocked=not rule_result.touch_queue_allowed,
            risk_block_reason=";".join(rule_result.risk_flags) or None,
        )
        StagingLeadService(self.session).auto_promote_if_eligible(lead, actor="llm-grading-agent")
        self.session.flush()
        return LLMLeadGradingResult(staging_lead=lead, rule_result=rule_result)
