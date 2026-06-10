from dataclasses import dataclass
from datetime import UTC, datetime, time
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models import AgentTaskRun, ContactMethod, Customer, LeadEnrichmentFieldCandidate, LeadEnrichmentResult, StagingLead
from app.models.enums import (
    AgentTaskRunStatus,
    AgentTaskType,
    ChannelRiskLevel,
    CustomerGrade,
    LeadEnrichmentFieldSourceType,
    LeadEnrichmentFieldReviewStatus,
    LeadEnrichmentResultStatus,
    LeadEnrichmentType,
)
from app.services.compliance_guards import Phase3ComplianceGuardService
from app.schemas.lead_enrichment import LeadEnrichmentRunCreate, ManualEnrichmentCreate
from app.schemas.lead_enrichment_field_candidate import (
    LeadEnrichmentFieldCandidateAccept,
    LeadEnrichmentFieldCandidateReject,
    LeadEnrichmentFieldCandidateUpdate,
)
from app.services.agent_task_runs import AgentTaskRunService
from app.services.audit_events import Phase3AuditEventService
from app.agents.http_runtime import HttpAgentRuntime
from app.settings import Settings, settings


@dataclass(frozen=True)
class LeadEnrichmentQuota:
    daily_limit: int
    used_today: int


def select_deep_enrichment_runtime(config: Settings = settings):
    if not config.agent_deep_enrichment_http_active_enabled or not config.http_agent_runtime_enabled:
        return None
    return HttpAgentRuntime(settings=config)


class LeadEnrichmentService:
    CRITICAL_PROMOTION_FIELDS = {"customer_name", "contacts_json", "source_evidence", "country", "city"}

    def __init__(self, session: Session) -> None:
        self.session = session

    @staticmethod
    def _now() -> datetime:
        return datetime.now(UTC)

    def get_staging_lead(self, lead_id: UUID) -> StagingLead | None:
        return self.session.execute(
            select(StagingLead)
            .options(selectinload(StagingLead.candidate_url))
            .where(StagingLead.id == lead_id)
        ).scalar_one_or_none()

    @staticmethod
    def _day_bounds(now: datetime) -> tuple[datetime, datetime]:
        normalized = now.astimezone(UTC) if now.tzinfo is not None else now.replace(tzinfo=UTC)
        start = datetime.combine(normalized.date(), time.min, tzinfo=UTC)
        end = datetime.combine(normalized.date(), time.max, tzinfo=UTC)
        return start, end

    def quota_for_lead(self, lead_id: UUID, *, daily_limit: int, now: datetime | None = None) -> LeadEnrichmentQuota:
        started_at, ended_at = self._day_bounds(now or self._now())
        used_today = int(
            self.session.execute(
                select(func.count(LeadEnrichmentResult.id)).where(
                    LeadEnrichmentResult.staging_lead_id == lead_id,
                    LeadEnrichmentResult.enrichment_type == LeadEnrichmentType.AI_DEEP_RESEARCH,
                    LeadEnrichmentResult.created_at >= started_at,
                    LeadEnrichmentResult.created_at <= ended_at,
                )
            ).scalar_one()
            or 0
        )
        return LeadEnrichmentQuota(daily_limit=daily_limit, used_today=used_today)

    @staticmethod
    def _contact_values(contacts_json: list | None) -> set[str]:
        return {
            str(item.get("value", "")).strip().lower()
            for item in (contacts_json or [])
            if isinstance(item, dict) and str(item.get("value", "")).strip()
        }

    def has_do_not_contact_match(self, lead: StagingLead) -> bool:
        contact_values = self._contact_values(lead.contacts_json)
        normalized_name = (lead.customer_name or "").strip().lower()
        if not contact_values and not normalized_name:
            return False

        query = select(Customer).where(Customer.do_not_contact.is_(True))
        if normalized_name and normalized_name != "unknown":
            query = query.where(func.lower(Customer.name) == normalized_name)
            if self.session.execute(query.limit(1)).scalar_one_or_none() is not None:
                return True

        if not contact_values:
            return False
        matched_contact = self.session.execute(
            select(ContactMethod.id)
            .join(Customer, ContactMethod.customer_id == Customer.id)
            .where(Customer.do_not_contact.is_(True), func.lower(ContactMethod.value).in_(contact_values))
            .limit(1)
        ).scalar_one_or_none()
        return matched_contact is not None

    @staticmethod
    def validate_trigger_allowed(
        lead: StagingLead,
        *,
        quota: LeadEnrichmentQuota,
        has_do_not_contact_match: bool,
    ) -> None:
        grade = CustomerGrade(lead.recommended_grade)
        if grade in {CustomerGrade.WATCH, CustomerGrade.INVALID}:
            raise ValueError("Watch/Invalid 线索不得深挖。")

        candidate = getattr(lead, "candidate_url", None)
        risk_level = getattr(candidate, "source_risk_level", None)
        if risk_level is not None and ChannelRiskLevel(risk_level) == ChannelRiskLevel.FORBIDDEN:
            raise ValueError("Forbidden 来源线索不得深挖。")

        if has_do_not_contact_match:
            raise ValueError("命中勿扰客户，不得深挖。")

        if quota.used_today >= quota.daily_limit:
            raise ValueError(f"已达到每日深挖配额：{quota.used_today}/{quota.daily_limit}。")

    @staticmethod
    def build_pending_run_payload(
        lead: StagingLead,
        *,
        request: LeadEnrichmentRunCreate,
        now: datetime | None = None,
    ) -> dict:
        timestamp = now or LeadEnrichmentService._now()
        candidate = getattr(lead, "candidate_url", None)
        input_snapshot = {
            "triggered_at": timestamp.isoformat(),
            "customer_name": lead.customer_name,
            "country": lead.country,
            "city": lead.city,
            "contacts_json": lead.contacts_json or [],
            "source_url": getattr(candidate, "url", None),
            "source_risk_level": getattr(getattr(candidate, "source_risk_level", None), "value", None),
            "source_evidence": lead.source_evidence,
            "recommended_grade": CustomerGrade(lead.recommended_grade).value,
            "missing_fields": lead.missing_fields or [],
            "manual_keywords": request.manual_keywords,
            "allowed_channel_scope": request.allowed_channel_scope,
            "note": request.note,
        }
        return {
            "staging_lead_id": lead.id,
            "enrichment_type": LeadEnrichmentType.AI_DEEP_RESEARCH,
            "triggered_by": request.triggered_by,
            "status": LeadEnrichmentResultStatus.PENDING,
            "input_snapshot_json": input_snapshot,
            "output_json": None,
            "evidence_links": [],
            "confidence_score": None,
            "missing_fields": lead.missing_fields or [],
            "recommended_action": "run_deep_enrichment_agent",
            "agent_task_run_id": None,
            "created_at": timestamp,
            "updated_at": timestamp,
        }

    def create_pending_run(
        self,
        lead: StagingLead,
        *,
        request: LeadEnrichmentRunCreate,
        daily_limit: int,
        now: datetime | None = None,
    ) -> tuple[LeadEnrichmentResult, LeadEnrichmentQuota]:
        quota = self.quota_for_lead(lead.id, daily_limit=daily_limit, now=now)
        self.validate_trigger_allowed(
            lead,
            quota=quota,
            has_do_not_contact_match=self.has_do_not_contact_match(lead),
        )
        run = LeadEnrichmentResult(**self.build_pending_run_payload(lead, request=request, now=now))
        self.session.add(run)
        self.session.flush()
        candidate = getattr(lead, "candidate_url", None)
        Phase3AuditEventService.record_event(
            self.session,
            event_name="lead_deep_enrichment_started",
            actor=request.triggered_by,
            entity_type="lead_enrichment_result",
            entity_id=run.id,
            reason=request.note,
            evidence={
                "staging_lead_id": lead.id,
                "source_url": getattr(candidate, "url", None),
                "source_risk_level": getattr(getattr(candidate, "source_risk_level", None), "value", None),
                "manual_keywords": request.manual_keywords,
                "allowed_channel_scope": request.allowed_channel_scope,
            },
            occurred_at=run.created_at,
        )
        return run, LeadEnrichmentQuota(daily_limit=quota.daily_limit, used_today=quota.used_today + 1)

    def run_deep_enrichment_agent(
        self,
        result: LeadEnrichmentResult,
        *,
        runtime,
        now: datetime | None = None,
        agents_base_url: str | None = None,
    ) -> AgentTaskRun:
        timestamp = now or self._now()
        task_payload = AgentTaskRunService.build_initial_payload(
            task_type=AgentTaskType.LEAD_GRADING,
            trigger_source="phase3_deep_enrichment_runtime",
            input_json={
                "enrichment_result_id": str(result.id),
                "staging_lead_id": str(result.staging_lead_id),
                "missing_fields": result.missing_fields or [],
            },
        )
        task_run = AgentTaskRun(**task_payload)
        self.session.add(task_run)
        self.session.flush()
        result.agent_task_run_id = task_run.id
        task_run.status = AgentTaskRunStatus.RUNNING
        task_run.started_at = timestamp
        task_run.updated_at = timestamp
        result.status = LeadEnrichmentResultStatus.RUNNING
        result.updated_at = timestamp

        external_agent_response = None
        try:
            runtime_kwargs = {
                "agent_run_id": task_run.id,
                "staging_lead_id": result.staging_lead_id,
                "lead_snapshot": result.input_snapshot_json or {},
                "missing_fields": result.missing_fields or [],
            }
            if hasattr(runtime, "run_deep_enrichment_response"):
                external_agent_response = runtime.run_deep_enrichment_response(**runtime_kwargs)
                output = external_agent_response.get("output") if isinstance(external_agent_response, dict) else None
            else:
                output = runtime.run_deep_enrichment(**runtime_kwargs)
            if not isinstance(output, dict):
                raise ValueError("Deep Enrichment Agent 输出缺少结构化 output。")
            if output.get("schema_version") != "phase3.agent.deep_enrichment.v1":
                raise ValueError("Deep Enrichment Agent 输出 schema_version 不正确。")
            audit = output.get("audit") or {}
            if audit.get("writes_core_tables") is not False:
                raise ValueError("Deep Enrichment Agent 输出缺少 staging/core 边界审计。")

            field_candidates = output.get("field_candidates") or []
            candidates = [
                LeadEnrichmentFieldCandidate(
                    enrichment_result_id=result.id,
                    staging_lead_id=result.staging_lead_id,
                    field_name=item["field_name"],
                    candidate_value=item["candidate_value"],
                    source_type=LeadEnrichmentFieldSourceType(item["source_type"]),
                    source_url=item.get("source_url"),
                    evidence_note=item["evidence_note"],
                    confidence_score=item.get("confidence_score"),
                    review_status=LeadEnrichmentFieldReviewStatus(item.get("review_status") or LeadEnrichmentFieldReviewStatus.PENDING.value),
                    accepted_by=None,
                    accepted_at=None,
                    rejected_reason=None,
                    created_at=timestamp,
                    updated_at=timestamp,
                )
                for item in field_candidates
            ]
            self.session.add_all(candidates)
            evidence_links = sorted(
                {
                    str(item.get("source_url")).strip()
                    for item in field_candidates
                    if str(item.get("source_url") or "").strip()
                }
            )
            result.status = LeadEnrichmentResultStatus.SUCCEEDED
            result.output_json = output
            result.evidence_links = evidence_links
            result.confidence_score = self._average_confidence([item.get("confidence_score") for item in field_candidates])
            result.missing_fields = output.get("missing_fields") or []
            result.recommended_action = output.get("recommended_next_action") or "manual_review"
            result.updated_at = timestamp
            success_summary = {
                "schema_version": output["schema_version"],
                "field_candidate_count": len(candidates),
                "evidence_links": evidence_links,
                "writes_core_tables": False,
            }
            if external_agent_response is not None:
                task_payload = AgentTaskRunService.succeed_with_external_agent_summary(
                    self._task_to_payload(task_run),
                    output_summary_json=success_summary,
                    external_agent_response=external_agent_response,
                    agents_base_url=agents_base_url or getattr(getattr(runtime, "settings", None), "agents_base_url", ""),
                )
                self._apply_task_payload(task_run, task_payload)
            else:
                task_run.status = AgentTaskRunStatus.SUCCEEDED
                task_run.output_summary_json = success_summary
            task_run.error_message = None
            task_run.finished_at = timestamp
            task_run.updated_at = timestamp
        except Exception as exc:
            result.status = LeadEnrichmentResultStatus.FAILED
            result.output_json = {
                "error": str(exc),
                "agent_task_run_id": str(task_run.id),
            }
            result.updated_at = timestamp
            if external_agent_response is not None:
                task_payload = AgentTaskRunService.fail_with_external_agent_summary(
                    self._task_to_payload(task_run),
                    error_message=str(exc),
                    error={"type": "schema_validation_error", "message": str(exc), "retryable": False},
                    external_agent_response=external_agent_response,
                    agents_base_url=agents_base_url or getattr(getattr(runtime, "settings", None), "agents_base_url", ""),
                )
                self._apply_task_payload(task_run, task_payload)
            else:
                task_run.status = AgentTaskRunStatus.FAILED
                task_run.error_message = str(exc)
                task_run.output_summary_json = {
                    "error": str(exc),
                    "writes_core_tables": False,
                }
            task_run.finished_at = timestamp
            task_run.updated_at = timestamp

        self.session.flush()
        return task_run

    @staticmethod
    def _task_to_payload(task_run: AgentTaskRun) -> dict:
        return {
            "task_type": task_run.task_type,
            "status": task_run.status,
            "trigger_source": task_run.trigger_source,
            "input_json": task_run.input_json,
            "output_summary_json": task_run.output_summary_json,
            "llm_provider": task_run.llm_provider,
            "llm_model": task_run.llm_model,
            "prompt_template_id": task_run.prompt_template_id,
            "prompt_version": task_run.prompt_version,
            "token_usage_json": task_run.token_usage_json,
            "latency_ms": task_run.latency_ms,
            "error_message": task_run.error_message,
            "retry_count": task_run.retry_count,
            "started_at": task_run.started_at,
            "finished_at": task_run.finished_at,
            "created_at": task_run.created_at,
            "updated_at": task_run.updated_at,
        }

    @staticmethod
    def _apply_task_payload(task_run: AgentTaskRun, payload: dict) -> None:
        for key, value in payload.items():
            if hasattr(task_run, key):
                setattr(task_run, key, value)

    @staticmethod
    def _average_confidence(values: list[float | None]) -> float | None:
        confidence_values = [float(value) for value in values if value is not None]
        if not confidence_values:
            return None
        return sum(confidence_values) / len(confidence_values)

    @classmethod
    def validate_manual_enrichment_allowed(cls, lead: StagingLead, *, request: ManualEnrichmentCreate) -> None:
        candidate = getattr(lead, "candidate_url", None)
        risk_level = getattr(candidate, "source_risk_level", None)
        if risk_level is not None and ChannelRiskLevel(risk_level) == ChannelRiskLevel.FORBIDDEN:
            raise ValueError("Forbidden 来源线索不得通过人工补录绕过合规硬门禁。")

        for field in request.fields:
            if (
                field.field_name in cls.CRITICAL_PROMOTION_FIELDS
                and field.source_type == LeadEnrichmentFieldSourceType.UNKNOWN
            ):
                raise ValueError("unknown 来源不得作为晋级关键证据。")

    @classmethod
    def build_manual_enrichment_payloads(
        cls,
        lead: StagingLead,
        *,
        request: ManualEnrichmentCreate,
        now: datetime | None = None,
    ) -> tuple[dict, list[dict]]:
        cls.validate_manual_enrichment_allowed(lead, request=request)
        timestamp = now or cls._now()
        input_snapshot = {
            "operator": request.operator,
            "note": request.note,
            "customer_name": lead.customer_name,
            "country": lead.country,
            "city": lead.city,
            "contacts_json": lead.contacts_json or [],
            "source_evidence": lead.source_evidence,
            "recommended_grade": CustomerGrade(lead.recommended_grade).value,
            "manual_fields": [field.model_dump(mode="json") for field in request.fields],
        }
        result_payload = {
            "staging_lead_id": lead.id,
            "enrichment_type": LeadEnrichmentType.MANUAL_SUPPLEMENT,
            "triggered_by": request.operator,
            "status": LeadEnrichmentResultStatus.SUCCEEDED,
            "input_snapshot_json": input_snapshot,
            "output_json": {
                "manual_field_count": len(request.fields),
                "note": request.note,
            },
            "evidence_links": [field.source_url for field in request.fields if field.source_url],
            "confidence_score": None,
            "missing_fields": lead.missing_fields or [],
            "recommended_action": "manual_review",
            "agent_task_run_id": None,
            "created_at": timestamp,
            "updated_at": timestamp,
        }
        candidate_payloads = [
            {
                "staging_lead_id": lead.id,
                "field_name": field.field_name,
                "candidate_value": field.candidate_value,
                "source_type": field.source_type,
                "source_url": field.source_url,
                "evidence_note": field.evidence_note,
                "confidence_score": field.confidence_score,
                "review_status": LeadEnrichmentFieldReviewStatus.NEEDS_REVIEW,
                "accepted_by": None,
                "accepted_at": None,
                "rejected_reason": None,
                "created_at": timestamp,
                "updated_at": timestamp,
            }
            for field in request.fields
        ]
        return result_payload, candidate_payloads

    def create_manual_enrichment(
        self,
        lead: StagingLead,
        *,
        request: ManualEnrichmentCreate,
        now: datetime | None = None,
    ) -> tuple[LeadEnrichmentResult, list[LeadEnrichmentFieldCandidate]]:
        result_payload, candidate_payloads = self.build_manual_enrichment_payloads(lead, request=request, now=now)
        result = LeadEnrichmentResult(**result_payload)
        self.session.add(result)
        self.session.flush()
        candidates = [
            LeadEnrichmentFieldCandidate(enrichment_result_id=result.id, **candidate_payload)
            for candidate_payload in candidate_payloads
        ]
        self.session.add_all(candidates)
        self.session.flush()
        return result, candidates

    def list_results_for_lead(self, lead_id: UUID) -> list[LeadEnrichmentResult]:
        return list(
            self.session.execute(
                select(LeadEnrichmentResult)
                .where(LeadEnrichmentResult.staging_lead_id == lead_id)
                .order_by(LeadEnrichmentResult.created_at.desc(), LeadEnrichmentResult.id.desc())
            ).scalars()
        )

    def list_field_candidates_for_results(
        self,
        result_ids: list[UUID],
    ) -> list[LeadEnrichmentFieldCandidate]:
        if not result_ids:
            return []
        return list(
            self.session.execute(
                select(LeadEnrichmentFieldCandidate)
                .where(LeadEnrichmentFieldCandidate.enrichment_result_id.in_(result_ids))
                .order_by(
                    LeadEnrichmentFieldCandidate.created_at.asc(),
                    LeadEnrichmentFieldCandidate.id.asc(),
                )
            ).scalars()
        )

    def get_field_candidate(self, candidate_id: UUID) -> LeadEnrichmentFieldCandidate | None:
        return self.session.get(LeadEnrichmentFieldCandidate, candidate_id)

    @staticmethod
    def _apply_candidate_updates(
        candidate: LeadEnrichmentFieldCandidate,
        request: LeadEnrichmentFieldCandidateAccept | LeadEnrichmentFieldCandidateUpdate,
    ) -> None:
        update_fields = request.model_dump(exclude_unset=True)
        for field_name in ("candidate_value", "source_type", "source_url", "evidence_note", "confidence_score"):
            if field_name in update_fields:
                setattr(candidate, field_name, update_fields[field_name])

    @classmethod
    def validate_candidate_has_evidence_for_acceptance(cls, candidate: LeadEnrichmentFieldCandidate) -> None:
        Phase3ComplianceGuardService.ensure_field_candidate_has_evidence(candidate)

    @classmethod
    def accept_field_candidate(
        cls,
        candidate: LeadEnrichmentFieldCandidate,
        *,
        request: LeadEnrichmentFieldCandidateAccept,
        now: datetime | None = None,
    ) -> LeadEnrichmentFieldCandidate:
        timestamp = now or cls._now()
        cls._apply_candidate_updates(candidate, request)
        cls.validate_candidate_has_evidence_for_acceptance(candidate)
        candidate.review_status = LeadEnrichmentFieldReviewStatus.ACCEPTED
        candidate.accepted_by = request.accepted_by
        candidate.accepted_at = timestamp
        candidate.rejected_reason = None
        candidate.updated_at = timestamp
        return candidate

    @classmethod
    def reject_field_candidate(
        cls,
        candidate: LeadEnrichmentFieldCandidate,
        *,
        request: LeadEnrichmentFieldCandidateReject,
        now: datetime | None = None,
    ) -> LeadEnrichmentFieldCandidate:
        timestamp = now or cls._now()
        candidate.review_status = LeadEnrichmentFieldReviewStatus.REJECTED
        candidate.rejected_reason = request.rejected_reason
        candidate.accepted_by = None
        candidate.accepted_at = None
        candidate.updated_at = timestamp
        return candidate

    def accept_field_candidate_with_audit(
        self,
        candidate: LeadEnrichmentFieldCandidate,
        *,
        request: LeadEnrichmentFieldCandidateAccept,
        now: datetime | None = None,
    ) -> LeadEnrichmentFieldCandidate:
        accepted = self.accept_field_candidate(candidate, request=request, now=now)
        self.apply_accepted_field_candidate_to_staging_lead(accepted, now=accepted.accepted_at or now)
        Phase3AuditEventService.record_event(
            self.session,
            event_name="lead_enrichment_field_accepted",
            actor=request.accepted_by,
            entity_type="lead_enrichment_field_candidate",
            entity_id=accepted.id,
            reason=accepted.evidence_note,
            evidence={
                "staging_lead_id": accepted.staging_lead_id,
                "enrichment_result_id": accepted.enrichment_result_id,
                "field_name": accepted.field_name,
                "source_type": accepted.source_type.value,
                "source_url": accepted.source_url,
                "confidence_score": accepted.confidence_score,
            },
            occurred_at=accepted.accepted_at,
        )
        return accepted

    def apply_accepted_field_candidate_to_staging_lead(
        self,
        candidate: LeadEnrichmentFieldCandidate,
        *,
        now: datetime | None = None,
    ) -> StagingLead | None:
        lead = self.session.get(StagingLead, candidate.staging_lead_id)
        if lead is None or not hasattr(lead, candidate.field_name):
            return lead

        if candidate.field_name == "contacts_json":
            lead.contacts_json = self.merge_contacts_json(lead.contacts_json, candidate.candidate_value)
        else:
            setattr(lead, candidate.field_name, candidate.candidate_value)
        lead.missing_fields = [
            field_name
            for field_name in (lead.missing_fields or [])
            if field_name != candidate.field_name
        ]
        lead.updated_at = now or self._now()
        return lead

    @staticmethod
    def merge_contacts_json(existing_contacts: list | None, candidate_value) -> list:
        merged: list = []
        seen_values: set[str] = set()
        for contact in [*(existing_contacts or []), *(candidate_value if isinstance(candidate_value, list) else [candidate_value])]:
            if not isinstance(contact, dict):
                continue
            value = str(contact.get("value") or "").strip()
            if not value:
                continue
            normalized = value.lower()
            if normalized in seen_values:
                continue
            seen_values.add(normalized)
            merged.append(contact)
        return merged

    def reject_field_candidate_with_audit(
        self,
        candidate: LeadEnrichmentFieldCandidate,
        *,
        request: LeadEnrichmentFieldCandidateReject,
        now: datetime | None = None,
    ) -> LeadEnrichmentFieldCandidate:
        rejected = self.reject_field_candidate(candidate, request=request, now=now)
        Phase3AuditEventService.record_event(
            self.session,
            event_name="lead_enrichment_field_rejected",
            actor=None,
            entity_type="lead_enrichment_field_candidate",
            entity_id=rejected.id,
            reason=request.rejected_reason,
            evidence={
                "staging_lead_id": rejected.staging_lead_id,
                "enrichment_result_id": rejected.enrichment_result_id,
                "field_name": rejected.field_name,
                "source_type": rejected.source_type.value,
                "source_url": rejected.source_url,
                "confidence_score": rejected.confidence_score,
            },
            occurred_at=rejected.updated_at,
        )
        return rejected

    @classmethod
    def update_field_candidate(
        cls,
        candidate: LeadEnrichmentFieldCandidate,
        *,
        request: LeadEnrichmentFieldCandidateUpdate,
        now: datetime | None = None,
    ) -> LeadEnrichmentFieldCandidate:
        timestamp = now or cls._now()
        if request.review_status == LeadEnrichmentFieldReviewStatus.ACCEPTED:
            raise ValueError("字段采纳必须通过 /accept 接口执行，以保留证据校验和采纳审计。")
        cls._apply_candidate_updates(candidate, request)
        if request.review_status is not None:
            candidate.review_status = request.review_status
        if request.accepted_by is not None:
            candidate.accepted_by = request.accepted_by
        if request.accepted_at is not None:
            candidate.accepted_at = request.accepted_at
        if request.rejected_reason is not None:
            candidate.rejected_reason = request.rejected_reason
        candidate.updated_at = timestamp
        return candidate

    @staticmethod
    def group_field_candidates_by_result_id(
        candidates: list[LeadEnrichmentFieldCandidate],
    ) -> dict[UUID, list[LeadEnrichmentFieldCandidate]]:
        grouped: dict[UUID, list[LeadEnrichmentFieldCandidate]] = {}
        for candidate in candidates:
            grouped.setdefault(candidate.enrichment_result_id, []).append(candidate)
        return grouped

    @staticmethod
    def serialize_field_candidate(candidate: LeadEnrichmentFieldCandidate) -> dict:
        return {
            "id": candidate.id,
            "enrichment_result_id": candidate.enrichment_result_id,
            "staging_lead_id": candidate.staging_lead_id,
            "field_name": candidate.field_name,
            "candidate_value": candidate.candidate_value,
            "source_type": candidate.source_type.value,
            "source_url": candidate.source_url,
            "evidence_note": candidate.evidence_note,
            "confidence_score": candidate.confidence_score,
            "review_status": candidate.review_status.value,
            "accepted_by": candidate.accepted_by,
            "accepted_at": candidate.accepted_at,
            "rejected_reason": candidate.rejected_reason,
            "created_at": candidate.created_at,
            "updated_at": candidate.updated_at,
        }

    @classmethod
    def serialize_result_with_candidates(
        cls,
        result: LeadEnrichmentResult,
        candidates: list[LeadEnrichmentFieldCandidate],
    ) -> dict:
        return {
            "id": result.id,
            "staging_lead_id": result.staging_lead_id,
            "enrichment_type": result.enrichment_type.value,
            "triggered_by": result.triggered_by,
            "status": result.status.value,
            "input_snapshot_json": result.input_snapshot_json,
            "output_json": result.output_json,
            "evidence_links": result.evidence_links,
            "confidence_score": result.confidence_score,
            "missing_fields": result.missing_fields,
            "recommended_action": result.recommended_action,
            "agent_task_run_id": result.agent_task_run_id,
            "created_at": result.created_at,
            "updated_at": result.updated_at,
            "field_candidates": [cls.serialize_field_candidate(candidate) for candidate in candidates],
        }
