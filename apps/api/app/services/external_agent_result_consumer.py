from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.agent_task_run import AgentTaskRun
from app.models.enums import (
    AgentTaskRunStatus,
    AgentTaskType,
    CandidateUrlStatus,
    ChannelRiskLevel,
    CollectionTaskStatus,
    CustomerGrade,
    CustomerType,
    SourcePlatform,
    SourceUsageType,
)
from app.services.lead_source_candidates import LeadSourceCandidateService
from app.services.raw_collection import RawCollectionService
from app.services.staging_leads import StagingLeadService


@dataclass(frozen=True)
class ExternalAgentConsumptionResult:
    status: str
    summary: dict[str, Any]


class ExternalAgentResultConsumer:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.raw_collection_service = RawCollectionService(session)
        self.staging_lead_service = StagingLeadService(session)

    def consume_source_discovery_response(self, response: dict[str, Any]) -> ExternalAgentConsumptionResult:
        output = self._successful_output(response, expected_agent_type="source_discovery")
        task_run = self._create_agent_task_run(
            task_type=AgentTaskType.SOURCE_DISCOVERY,
            trigger_source="external_agent_source_discovery_result",
            response=response,
            output=output,
        )
        normalized_output = self._source_discovery_output_for_api(output)
        batch = LeadSourceCandidateService(self.session).upsert_from_source_discovery_output(
            normalized_output,
            created_by_task_run_id=task_run.id,
            llm_provider="apps/agents",
            llm_model=str(response.get("agent_type") or "source_discovery"),
            llm_output_json=output,
        )
        task_run.output_summary_json = {
            "external_agent_run_id": response.get("agent_service_run_id"),
            "created_count": batch.created_count,
            "updated_count": batch.updated_count,
            "blocked_count": batch.blocked_count,
            "duplicate_count": batch.duplicate_count,
        }
        task_run.status = AgentTaskRunStatus.SUCCEEDED
        self.session.flush()
        return ExternalAgentConsumptionResult(status="succeeded", summary=task_run.output_summary_json)

    def consume_lead_extraction_grading_response(self, response: dict[str, Any]) -> ExternalAgentConsumptionResult:
        output = self._successful_output(response, expected_agent_type="lead_extraction_grading")
        task_run = self._create_agent_task_run(
            task_type=AgentTaskType.LEAD_EXTRACTION,
            trigger_source="external_agent_lead_extraction_grading_result",
            response=response,
            output=output,
        )
        created_count = 0
        updated_count = 0
        processed_items: list[dict[str, Any]] = []
        for lead_payload in self._staging_lead_payloads(output):
            if not lead_payload["source_url"]:
                continue
            candidate_url_result = self._ensure_candidate_url_for_staging_payload(lead_payload)
            existing = self._find_existing_staging_lead(candidate_url_result.candidate_url.id, lead_payload)
            if existing is None:
                self.staging_lead_service.create_staging_lead(
                    candidate_url_id=candidate_url_result.candidate_url.id,
                    customer_name=lead_payload["customer_name"],
                    country=lead_payload["country"],
                    city=lead_payload["city"],
                    customer_type=lead_payload["customer_type"],
                    contacts_json=lead_payload["contacts_json"],
                    activity_level=lead_payload["activity_level"],
                    scale_signal=lead_payload["scale_signal"],
                    import_used_car_relevance=lead_payload["import_used_car_relevance"],
                    source_evidence=lead_payload["source_evidence"],
                    recommended_grade=lead_payload["recommended_grade"],
                    recommended_reason=lead_payload["recommended_reason"],
                    missing_fields=lead_payload["missing_fields"],
                    source_risk_level=lead_payload["source_risk_level"],
                )
                created_count += 1
                item_status = "created"
            else:
                existing.customer_name = lead_payload["customer_name"]
                existing.country = lead_payload["country"]
                existing.city = lead_payload["city"]
                existing.contacts_json = lead_payload["contacts_json"]
                existing.activity_level = lead_payload["activity_level"]
                existing.scale_signal = lead_payload["scale_signal"]
                existing.import_used_car_relevance = lead_payload["import_used_car_relevance"]
                existing.source_evidence = lead_payload["source_evidence"]
                existing.recommended_grade = CustomerGrade(lead_payload["recommended_grade"])
                existing.recommended_reason = lead_payload["recommended_reason"]
                existing.missing_fields = lead_payload["missing_fields"]
                updated_count += 1
                item_status = "updated"
            processed_items.append(
                {
                    "source_candidate_id": lead_payload.get("source_candidate_id"),
                    "source_url": lead_payload["source_url"],
                    "status": "succeeded",
                    "write_action": item_status,
                }
            )
        for item in self._failed_batch_items(output):
            processed_items.append(item)
        task_run.output_summary_json = {
            "external_agent_run_id": response.get("agent_service_run_id"),
            "created_count": created_count,
            "updated_count": updated_count,
            "processed_items": processed_items,
        }
        task_run.status = AgentTaskRunStatus.SUCCEEDED
        self.session.flush()
        return ExternalAgentConsumptionResult(status="succeeded", summary=task_run.output_summary_json)

    def _successful_output(self, response: dict[str, Any], *, expected_agent_type: str) -> dict[str, Any]:
        if response.get("status") != "succeeded":
            raise ValueError(f"外部 Agent 未成功，不能消费结果：status={response.get('status')}")
        if response.get("agent_type") != expected_agent_type:
            raise ValueError(f"外部 Agent 类型不匹配：expected={expected_agent_type} actual={response.get('agent_type')}")
        audit = response.get("audit") if isinstance(response.get("audit"), dict) else {}
        if audit.get("writes_core_tables") is not False:
            raise ValueError("外部 Agent 响应 audit.writes_core_tables 必须为 false。")
        output = response.get("output")
        if not isinstance(output, dict):
            raise ValueError("外部 Agent 响应缺少 output object。")
        return output

    def _create_agent_task_run(
        self,
        *,
        task_type: AgentTaskType,
        trigger_source: str,
        response: dict[str, Any],
        output: dict[str, Any],
    ) -> AgentTaskRun:
        task_run = AgentTaskRun(
            task_type=task_type,
            status=AgentTaskRunStatus.RUNNING,
            trigger_source=trigger_source,
            input_json={
                "external_agent_run_id": response.get("agent_service_run_id"),
                "request_id": response.get("request_id"),
                "agent_type": response.get("agent_type"),
                "agent_mode": response.get("agent_mode"),
            },
            output_summary_json={"external_agent_status": response.get("status")},
            llm_provider="apps/agents",
            llm_model=str(response.get("agent_type") or task_type.value),
            token_usage_json=None,
            error_message=None,
        )
        self.session.add(task_run)
        self.session.flush()
        return task_run

    def _source_discovery_output_for_api(self, output: dict[str, Any]) -> dict[str, Any]:
        candidates = []
        blocked_candidates = []
        for item in output.get("candidates") or []:
            risk_level = self._risk_level_for_api(item.get("risk_level"))
            payload = {
                "source_url": item.get("url"),
                "platform": self._platform_for_api(item.get("source_type")),
                "channel_name": item.get("title") or item.get("normalized_url") or "external_source_discovery",
                "country": output.get("market") or (output.get("audit") or {}).get("market") or "Unknown",
                "city": None,
                "risk_level": risk_level,
                "discovery_method": "apps_agents_source_discovery",
                "discovery_query": item.get("discovery_query"),
                "discovery_reason": item.get("evidence_summary") or "apps/agents external source discovery.",
                "evidence_note": item.get("evidence_summary") or "apps/agents external source discovery.",
                "evidence_links": [item.get("url")],
                "confidence_score": None,
            }
            if risk_level == ChannelRiskLevel.HIGH.value:
                blocked_candidates.append({**payload, "blocked_reason": "High 风险来源需人工复核。"})
            else:
                candidates.append(payload)
        for item in output.get("blocked_items") or []:
            url = item.get("url") or item.get("source_url")
            if not url:
                continue
            blocked_candidates.append(
                {
                    "source_url": url,
                    "platform": self._platform_for_api(item.get("source_type")),
                    "channel_name": item.get("title") or "external_source_discovery_blocked",
                    "risk_level": self._risk_level_for_api(item.get("risk_level"), default=ChannelRiskLevel.FORBIDDEN.value),
                    "blocked_reason": item.get("reason") or item.get("blocked_reason") or "apps/agents blocked item.",
                }
            )
        return {
            "task_type": "SOURCE_DISCOVERY",
            "country": output.get("market") or (output.get("audit") or {}).get("market") or "Unknown",
            "city": None,
            "channel_strategy": "apps/agents LangGraph Source Discovery output",
            "candidates": candidates,
            "blocked_candidates": blocked_candidates,
        }

    def _staging_lead_payloads(self, output: dict[str, Any]) -> list[dict[str, Any]]:
        batch_results = [item for item in output.get("batch_results") or [] if isinstance(item, dict)]
        if batch_results:
            results: list[dict[str, Any]] = []
            for item in batch_results:
                if item.get("status") != "succeeded" or not isinstance(item.get("output"), dict):
                    continue
                for payload in self._staging_lead_payloads(item["output"]):
                    payload["source_candidate_id"] = item.get("source_candidate_id") or payload.get("source_candidate_id")
                    results.append(payload)
            return results

        extraction = output.get("extraction") if isinstance(output.get("extraction"), dict) else {}
        grading = output.get("grading") if isinstance(output.get("grading"), dict) else {}
        suggestions = list(grading.get("suggestions") or [])
        results = []
        for index, candidate in enumerate(extraction.get("candidates") or []):
            suggestion = suggestions[index] if index < len(suggestions) and isinstance(suggestions[index], dict) else {}
            contacts = self._contacts_from_candidate(candidate)
            source_url = str(candidate.get("source_url") or suggestion.get("source_url") or "").strip()
            evidence_values = [
                self._field_quote(candidate, "company_name"),
                self._field_quote(candidate, "email"),
                self._field_quote(candidate, "phone"),
                self._field_quote(candidate, "vehicle_interest"),
                self._field_quote(candidate, "export_intent"),
            ]
            evidence = "；".join(value for value in evidence_values if value) or source_url
            results.append(
                {
                    "source_url": source_url,
                    "source_candidate_id": output.get("source_candidate_id"),
                    "source_risk_level": self._source_risk_from_suggestion(suggestion),
                    "customer_name": self._field_value(candidate, "company_name") or "Unknown",
                    "country": self._field_value(candidate, "country") or "Unknown",
                    "city": self._field_value(candidate, "city"),
                    "customer_type": CustomerType.LOCAL_DEALER_SECONDARY_DEALER.value,
                    "contacts_json": contacts,
                    "activity_level": "external_agent_runtime",
                    "scale_signal": self._field_value(candidate, "export_intent"),
                    "import_used_car_relevance": self._field_value(candidate, "vehicle_interest"),
                    "source_evidence": evidence,
                    "recommended_grade": suggestion.get("recommended_grade") or CustomerGrade.C.value,
                    "recommended_reason": "；".join(str(item) for item in suggestion.get("reasons") or []) or "apps/agents grading.",
                    "missing_fields": self._missing_fields(candidate),
                }
            )
        return results

    @staticmethod
    def _failed_batch_items(output: dict[str, Any]) -> list[dict[str, Any]]:
        failed: list[dict[str, Any]] = []
        for item in output.get("batch_results") or []:
            if not isinstance(item, dict) or item.get("status") == "succeeded":
                continue
            failed.append(
                {
                    "source_candidate_id": item.get("source_candidate_id"),
                    "source_url": item.get("source_url"),
                    "status": "failed",
                    "error_message": (item.get("error") or {}).get("message") if isinstance(item.get("error"), dict) else None,
                }
            )
        return failed

    def _ensure_candidate_url_for_staging_payload(self, payload: dict[str, Any]):
        task = self.raw_collection_service.create_collection_task(
            channel_name="apps_agents_lead_extraction_grading",
            task_type="external_agent_lead_extraction_grading",
            risk_level=payload["source_risk_level"],
            allowed_actions="read_public_source_only",
            forbidden_actions="no_auto_outreach,no_login,no_anti_scraping_bypass",
            source_usage_type=SourceUsageType.AUTOMATIC_COLLECTION,
            status=CollectionTaskStatus.COMPLETED,
        )
        return self.raw_collection_service.upsert_candidate_url(
            task_id=task.id,
            url=payload["source_url"],
            source_platform=SourcePlatform.OFFICIAL_WEBSITE,
            source_risk_level=payload["source_risk_level"],
            source_usage_type=SourceUsageType.AUTOMATIC_COLLECTION,
            discovery_reason=payload["source_evidence"] or "apps/agents lead extraction.",
            status=CandidateUrlStatus.STAGED,
        )

    def _find_existing_staging_lead(self, candidate_url_id, payload: dict[str, Any]):
        from app.models.staging_lead import StagingLead

        dedupe_key = StagingLeadService.build_dedupe_key(payload["customer_name"], payload["city"], payload["contacts_json"])
        return self.session.scalar(
            select(StagingLead).where(
                StagingLead.candidate_url_id == candidate_url_id,
                StagingLead.dedupe_key == dedupe_key,
            )
        )

    @staticmethod
    def _risk_level_for_api(value: object, *, default: str = ChannelRiskLevel.LOW.value) -> str:
        normalized = str(value or "").strip().lower()
        return {
            "low": ChannelRiskLevel.LOW.value,
            "medium": ChannelRiskLevel.MEDIUM.value,
            "high": ChannelRiskLevel.HIGH.value,
            "forbidden": ChannelRiskLevel.FORBIDDEN.value,
        }.get(normalized, default)

    @staticmethod
    def _platform_for_api(value: object) -> str:
        normalized = str(value or "").strip()
        try:
            return SourcePlatform(normalized).value
        except ValueError:
            return SourcePlatform.OTHER.value

    @staticmethod
    def _field_value(candidate: dict[str, Any], field_name: str) -> str | None:
        field = candidate.get(field_name) if isinstance(candidate.get(field_name), dict) else {}
        value = field.get("value")
        return str(value).strip() if value else None

    @staticmethod
    def _field_quote(candidate: dict[str, Any], field_name: str) -> str | None:
        field = candidate.get(field_name) if isinstance(candidate.get(field_name), dict) else {}
        evidence = field.get("evidence") if isinstance(field.get("evidence"), dict) else {}
        quote = evidence.get("quote")
        return str(quote).strip() if quote else None

    def _contacts_from_candidate(self, candidate: dict[str, Any]) -> list[dict[str, str]]:
        contacts: list[dict[str, str]] = []
        for contact in candidate.get("contacts") or []:
            if not isinstance(contact, dict):
                continue
            contact_type = str(contact.get("contact_type") or contact.get("type") or "").strip().lower()
            value = str(contact.get("value") or "").strip()
            if not contact_type or not value:
                continue
            contacts.append(
                {
                    "type": contact_type,
                    "value": value,
                    "usage": str(contact.get("usage") or "source_public_contact"),
                }
            )
        email = self._field_value(candidate, "email")
        phone = self._field_value(candidate, "phone")
        if email:
            contacts.append({"type": "email", "value": email, "usage": "source_public_contact"})
        if phone:
            contacts.append({"type": "phone", "value": phone, "usage": "source_public_contact"})
        return self._dedupe_contacts(contacts)

    @staticmethod
    def _dedupe_contacts(contacts: list[dict[str, str]]) -> list[dict[str, str]]:
        deduped = []
        seen: set[tuple[str, str]] = set()
        for contact in contacts:
            contact_type = str(contact.get("type") or "").strip().lower()
            value = str(contact.get("value") or "").strip()
            if not contact_type or not value:
                continue
            key = (contact_type, value.lower())
            if key in seen:
                continue
            seen.add(key)
            deduped.append(
                {
                    "type": contact_type,
                    "value": value,
                    "usage": str(contact.get("usage") or "source_public_contact"),
                }
            )
        return deduped

    @staticmethod
    def _missing_fields(candidate: dict[str, Any]) -> list[str]:
        missing = []
        for field_name, field in candidate.items():
            if isinstance(field, dict) and field.get("value") is None:
                missing.append(field_name)
        return missing

    @staticmethod
    def _source_risk_from_suggestion(suggestion: dict[str, Any]) -> str:
        route = suggestion.get("status_route")
        if route == "needs_manual_risk_review":
            return ChannelRiskLevel.HIGH.value
        if route == "risk_blocked":
            return ChannelRiskLevel.FORBIDDEN.value
        return ChannelRiskLevel.LOW.value
