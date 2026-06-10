from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import (
    LeadCleanupRun,
    LeadCleanupSuggestion,
    LeadEnrichmentFieldCandidate,
    LeadEnrichmentResult,
    StagingLead,
)
from app.models.enums import (
    CustomerGrade,
    LeadCleanupRunStatus,
    LeadCleanupSuggestionReviewStatus,
    LeadCleanupSuggestionType,
    LeadEnrichmentFieldReviewStatus,
    LeadEnrichmentFieldSourceType,
    LeadEnrichmentResultStatus,
    LeadEnrichmentType,
    StagingQueueStatus,
    StagingReviewStatus,
)
from app.services.lead_cleanup import LeadCleanupSuggestionService
from app.services.lead_enrichment import LeadEnrichmentService
from app.services.staging_leads import StagingLeadService


class ExternalAgentBatchConsumer:
    def __init__(self, session: Session) -> None:
        self.session = session

    def consume_deep_enrichment_response(self, response: dict[str, Any]) -> dict[str, Any]:
        output = self._successful_output(response, expected_agent_type="deep_enrichment")
        batch_results = [item for item in output.get("batch_results") or [] if isinstance(item, dict)]
        if not batch_results and output.get("schema_version") == "phase3.agent.deep_enrichment.v1":
            batch_results = [{"status": "succeeded", "output": output, "staging_lead_id": output.get("staging_lead_id")}]

        processed_count = 0
        field_candidate_count = 0
        promoted_count = 0
        items: list[dict[str, Any]] = []
        for item in batch_results:
            if item.get("status") != "succeeded" or not isinstance(item.get("output"), dict):
                items.append({"status": "failed", "staging_lead_id": item.get("staging_lead_id"), "error": item.get("error")})
                continue
            result = self._consume_one_deep_enrichment(item["output"])
            processed_count += 1
            field_candidate_count += result["field_candidate_count"]
            promoted_count += 1 if result["promoted"] else 0
            items.append(result)

        return {
            "status": "succeeded",
            "processed_count": processed_count,
            "field_candidate_count": field_candidate_count,
            "promoted_count": promoted_count,
            "quality_invalidated_count": 0,
            "items": items,
        }

    def _consume_one_deep_enrichment(self, output: dict[str, Any]) -> dict[str, Any]:
        now = datetime.now(UTC)
        lead_id = UUID(str(output["staging_lead_id"]))
        lead = self.session.get(StagingLead, lead_id)
        if lead is None:
            return {"status": "failed", "staging_lead_id": str(lead_id), "error": "staging_lead_not_found", "field_candidate_count": 0, "promoted": False}

        result = LeadEnrichmentResult(
            staging_lead_id=lead.id,
            enrichment_type=LeadEnrichmentType.AI_DEEP_RESEARCH,
            triggered_by="external-deep-enrichment-scheduler",
            status=LeadEnrichmentResultStatus.SUCCEEDED,
            input_snapshot_json={"staging_lead_id": str(lead.id), "customer_name": lead.customer_name},
            output_json=output,
            evidence_links=sorted({str(item.get("source_url")).strip() for item in output.get("field_candidates") or [] if str(item.get("source_url") or "").strip()}),
            confidence_score=self._average([item.get("confidence_score") for item in output.get("field_candidates") or []]),
            missing_fields=list(output.get("missing_fields") or []),
            recommended_action=output.get("recommended_next_action") or "manual_review",
            created_at=now,
            updated_at=now,
        )
        self.session.add(result)
        self.session.flush()

        candidates = []
        enrichment_service = LeadEnrichmentService(self.session)
        for raw in output.get("field_candidates") or []:
            candidate = LeadEnrichmentFieldCandidate(
                enrichment_result_id=result.id,
                staging_lead_id=lead.id,
                field_name=raw["field_name"],
                candidate_value=raw["candidate_value"],
                source_type=LeadEnrichmentFieldSourceType(raw.get("source_type") or LeadEnrichmentFieldSourceType.AI_PUBLIC_SOURCE.value),
                source_url=raw.get("source_url"),
                evidence_note=raw["evidence_note"],
                confidence_score=raw.get("confidence_score"),
                review_status=LeadEnrichmentFieldReviewStatus.ACCEPTED,
                accepted_by="external-deep-enrichment-scheduler",
                accepted_at=now,
                created_at=now,
                updated_at=now,
            )
            self.session.add(candidate)
            self.session.flush()
            enrichment_service.apply_accepted_field_candidate_to_staging_lead(candidate, now=now)
            candidates.append(candidate)

        lead.missing_fields = list(output.get("missing_fields") or lead.missing_fields or [])
        quality_reasons = self.low_quality_reasons(lead)
        promotion = StagingLeadService(self.session).auto_promote_if_eligible(lead, actor="external-deep-enrichment-scheduler")
        return {
            "status": "succeeded",
            "staging_lead_id": str(lead.id),
            "field_candidate_count": len(candidates),
            "promoted": bool(promotion.get("promoted")),
            "promotion_reasons": promotion.get("reasons") or [],
            "quality_invalidated": False,
            "quality_reasons": quality_reasons,
        }

    def consume_lead_cleanup_response(self, response: dict[str, Any]) -> dict[str, Any]:
        output = self._successful_output(response, expected_agent_type="lead_cleanup")
        now = datetime.now(UTC)
        cleanup_run = LeadCleanupRun(
            trigger_source="scheduler_external_lead_cleanup",
            status=LeadCleanupRunStatus.SUCCEEDED,
            input_filter_json={"recommended_grade": ["Watch", "Invalid"]},
            output_summary_json={},
            started_at=now,
            finished_at=now,
            created_at=now,
            updated_at=now,
        )
        self.session.add(cleanup_run)
        self.session.flush()

        executed_count = 0
        hidden_count = 0
        upgraded_count = 0
        suggestion_count = 0
        quality_invalidated_count = 0
        items: list[dict[str, Any]] = []
        service = LeadCleanupSuggestionService(self.session)
        for raw in output.get("suggestions") or []:
            suggestion = LeadCleanupSuggestion(
                cleanup_run_id=cleanup_run.id,
                staging_lead_id=UUID(str(raw["staging_lead_id"])),
                suggestion_type=LeadCleanupSuggestionType(raw["suggestion_type"]),
                target_lead_id=UUID(str(raw["target_lead_id"])) if raw.get("target_lead_id") else None,
                confidence_score=raw.get("confidence_score"),
                reason=raw["reason"],
                evidence_json=raw.get("evidence_json") or {},
                recommended_action=raw["recommended_action"],
                review_status=LeadCleanupSuggestionReviewStatus.PENDING,
                created_at=now,
                updated_at=now,
            )
            self.session.add(suggestion)
            self.session.flush()
            suggestion_count += 1
            action_result = self._auto_apply_cleanup_suggestion(service, suggestion, now=now)
            if not action_result["hidden"]:
                quality_result = self._auto_invalidate_low_quality_lead(
                    self.session.get(StagingLead, suggestion.staging_lead_id),
                    actor="external-lead-cleanup-scheduler",
                    now=now,
                    context="Lead Cleanup 后仍缺关键字段",
                )
                if quality_result["quality_invalidated"]:
                    action_result = {**action_result, **quality_result, "executed": True, "hidden": True}
            executed_count += 1 if action_result["executed"] else 0
            hidden_count += 1 if action_result["hidden"] else 0
            upgraded_count += 1 if action_result["upgraded"] else 0
            quality_invalidated_count += 1 if action_result.get("quality_invalidated") else 0
            items.append(action_result)

        cleanup_run.output_summary_json = {
            "schema_version": output.get("schema_version"),
            "suggestion_count": suggestion_count,
            "executed_count": executed_count,
            "hidden_count": hidden_count,
            "upgraded_count": upgraded_count,
            "quality_invalidated_count": quality_invalidated_count,
            "writes_core_tables": True,
        }
        return {
            "status": "succeeded",
            "suggestion_count": suggestion_count,
            "executed_count": executed_count,
            "hidden_count": hidden_count,
            "upgraded_count": upgraded_count,
            "quality_invalidated_count": quality_invalidated_count,
            "items": items,
        }

    def _auto_apply_cleanup_suggestion(self, service: LeadCleanupSuggestionService, suggestion: LeadCleanupSuggestion, *, now: datetime) -> dict[str, Any]:
        lead = self.session.get(StagingLead, suggestion.staging_lead_id)
        if lead is None:
            return {"staging_lead_id": str(suggestion.staging_lead_id), "executed": False, "hidden": False, "upgraded": False, "error": "staging_lead_not_found"}

        suggestion_type = LeadCleanupSuggestionType(suggestion.suggestion_type)
        suggestion.review_status = LeadCleanupSuggestionReviewStatus.APPROVED
        suggestion.reviewer_id = "external-lead-cleanup-scheduler"
        suggestion.reviewed_at = now

        if suggestion_type in {
            LeadCleanupSuggestionType.STRONG_DUPLICATE,
            LeadCleanupSuggestionType.POSSIBLE_DUPLICATE,
            LeadCleanupSuggestionType.MERGE_CONTACT_METHOD,
            LeadCleanupSuggestionType.MERGE_SOURCE_EVIDENCE,
            LeadCleanupSuggestionType.RESTORE_FROM_WATCH,
            LeadCleanupSuggestionType.CONFIRM_INVALID,
            LeadCleanupSuggestionType.MARK_ABANDONED,
        }:
            service.execute_suggestion(
                suggestion.id,
                actor="external-lead-cleanup-scheduler",
                actor_role="admin",
                execution_note="外部 Lead Cleanup Agent 批量清洗自动执行。",
                now=now,
            )
            hidden = suggestion_type in {LeadCleanupSuggestionType.CONFIRM_INVALID, LeadCleanupSuggestionType.MARK_ABANDONED, LeadCleanupSuggestionType.STRONG_DUPLICATE, LeadCleanupSuggestionType.POSSIBLE_DUPLICATE}
            upgraded = suggestion_type == LeadCleanupSuggestionType.RESTORE_FROM_WATCH
            return {"staging_lead_id": str(lead.id), "suggestion_type": suggestion_type.value, "executed": True, "hidden": hidden, "upgraded": upgraded}

        restored_grade = str((suggestion.evidence_json or {}).get("restored_grade") or "").strip()
        if restored_grade in {CustomerGrade.A.value, CustomerGrade.B.value, CustomerGrade.C.value}:
            lead.recommended_grade = CustomerGrade(restored_grade)
            lead.review_status = StagingReviewStatus.PENDING_REVIEW
            lead.queue_status = StagingQueueStatus.PENDING_REVIEW
            suggestion.review_status = LeadCleanupSuggestionReviewStatus.EXECUTED
            suggestion.executed_by = "external-lead-cleanup-scheduler"
            suggestion.executed_at = now
            suggestion.execution_note = "外部 Lead Cleanup Agent 给出升级建议并自动升级等级。"
            return {"staging_lead_id": str(lead.id), "suggestion_type": suggestion_type.value, "executed": True, "hidden": False, "upgraded": True}

        return {"staging_lead_id": str(lead.id), "suggestion_type": suggestion_type.value, "executed": False, "hidden": False, "upgraded": False}

    def _auto_invalidate_low_quality_lead(
        self,
        lead: StagingLead | None,
        *,
        actor: str,
        now: datetime,
        context: str,
    ) -> dict[str, Any]:
        if lead is None:
            return {"quality_invalidated": False, "quality_reasons": ["staging_lead_not_found"]}
        reasons = self.low_quality_reasons(lead)
        if not reasons:
            return {"quality_invalidated": False, "quality_reasons": []}

        lead.recommended_grade = CustomerGrade.INVALID
        lead.review_status = StagingReviewStatus.REJECTED
        lead.queue_status = StagingQueueStatus.NOT_ELIGIBLE
        lead.requires_compliance_review = False
        lead.missing_fields = sorted(set([*(lead.missing_fields or []), *reasons]))
        reason_text = f"质量过低，自动置为无效线索：{context}；" + "；".join(reasons)
        lead.recommended_reason = reason_text
        lead.updated_at = now
        return {
            "quality_invalidated": True,
            "quality_reasons": reasons,
            "quality_actor": actor,
        }

    @staticmethod
    def low_quality_reasons(lead: StagingLead) -> list[str]:
        reasons: list[str] = []
        if not StagingLeadService.has_valid_customer_name(lead.customer_name):
            reasons.append("缺客户名称")
        if not StagingLeadService.has_contact(lead.contacts_json):
            reasons.append("缺至少一个联系方式")
        if not str(lead.country or "").strip() or str(lead.country or "").strip().lower() == "unknown":
            reasons.append("缺国家")
        if not str(lead.city or "").strip() or str(lead.city or "").strip().lower() == "unknown":
            reasons.append("缺城市")
        if not str(lead.source_evidence or "").strip():
            reasons.append("缺来源证据")
        if any(str(item).strip().lower() in {"do_not_contact", "dnc", "勿扰校验"} for item in (lead.missing_fields or [])):
            reasons.append("缺勿扰校验通过证据")

        hard_blocking = {"缺客户名称", "缺至少一个联系方式"}
        if hard_blocking & set(reasons):
            return reasons
        return reasons if len(reasons) >= 3 else []

    @staticmethod
    def _successful_output(response: dict[str, Any], *, expected_agent_type: str) -> dict[str, Any]:
        if response.get("status") != "succeeded":
            raise ValueError(f"外部 Agent 未成功，不能消费结果：status={response.get('status')}")
        if response.get("agent_type") != expected_agent_type:
            raise ValueError(f"外部 Agent 类型不匹配：expected={expected_agent_type} actual={response.get('agent_type')}")
        if (response.get("audit") or {}).get("writes_core_tables") is not False:
            raise ValueError("外部 Agent 响应 audit.writes_core_tables 必须为 false。")
        output = response.get("output")
        if not isinstance(output, dict):
            raise ValueError("外部 Agent 响应缺少 output object。")
        return output

    @staticmethod
    def _average(values: list[Any]) -> float | None:
        numbers = [float(value) for value in values if value is not None]
        return sum(numbers) / len(numbers) if numbers else None
