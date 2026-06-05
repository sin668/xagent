from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AgentTaskRun, LeadCleanupRun, LeadCleanupSuggestion, ReviewLog, StagingLead
from app.models.enums import (
    AgentTaskRunStatus,
    AgentTaskType,
    CustomerGrade,
    LeadCleanupRunStatus,
    LeadCleanupSuggestionReviewStatus,
    LeadCleanupSuggestionType,
    StagingQueueStatus,
    StagingReviewStatus,
)
from app.services.agent_task_runs import AgentTaskRunService
from app.services.permissions import Phase3PermissionService
from app.agents.http_runtime import HttpAgentRuntime
from app.settings import Settings, settings


@dataclass(slots=True)
class LeadCleanupSuggestionQueryFilters:
    suggestion_type: LeadCleanupSuggestionType | None = None
    review_status: LeadCleanupSuggestionReviewStatus | None = LeadCleanupSuggestionReviewStatus.PENDING
    min_confidence: float | None = None
    max_confidence: float | None = None
    lead_id: UUID | None = None
    limit: int = 100


def select_lead_cleanup_runtime(config: Settings = settings):
    if not config.agent_lead_cleanup_http_active_enabled or not config.http_agent_runtime_enabled:
        return None
    return HttpAgentRuntime(settings=config)


class LeadCleanupSuggestionService:
    def __init__(self, session: Session) -> None:
        self.session = session

    @staticmethod
    def build_query(filters: LeadCleanupSuggestionQueryFilters):
        query = select(LeadCleanupSuggestion).order_by(
            LeadCleanupSuggestion.created_at.desc(),
            LeadCleanupSuggestion.id.desc(),
        )
        if filters.suggestion_type is not None:
            query = query.where(LeadCleanupSuggestion.suggestion_type == filters.suggestion_type)
        if filters.review_status is not None:
            query = query.where(LeadCleanupSuggestion.review_status == filters.review_status)
        if filters.min_confidence is not None:
            query = query.where(LeadCleanupSuggestion.confidence_score >= filters.min_confidence)
        if filters.max_confidence is not None:
            query = query.where(LeadCleanupSuggestion.confidence_score <= filters.max_confidence)
        if filters.lead_id is not None:
            query = query.where(
                (LeadCleanupSuggestion.staging_lead_id == filters.lead_id)
                | (LeadCleanupSuggestion.target_lead_id == filters.lead_id)
            )
        return query.limit(filters.limit)

    def list_suggestions(self, filters: LeadCleanupSuggestionQueryFilters) -> list[LeadCleanupSuggestion]:
        return list(self.session.scalars(self.build_query(filters)).all())

    def get_suggestion(self, suggestion_id: UUID) -> LeadCleanupSuggestion:
        suggestion = self.session.scalar(select(LeadCleanupSuggestion).where(LeadCleanupSuggestion.id == suggestion_id))
        if suggestion is None:
            raise ValueError(f"清洗建议不存在: {suggestion_id}")
        return suggestion

    def get_staging_lead(self, lead_id: UUID, *, role: str) -> StagingLead:
        lead = self.session.scalar(select(StagingLead).where(StagingLead.id == lead_id))
        if lead is None:
            raise ValueError(f"{role} 线索不存在: {lead_id}")
        return lead

    @classmethod
    def validate_review_permission(cls, suggestion: LeadCleanupSuggestion, *, actor_role: str) -> None:
        try:
            Phase3PermissionService.ensure_cleanup_review_allowed(
                LeadCleanupSuggestionType(suggestion.suggestion_type),
                actor_role=actor_role,
            )
        except PermissionError as exc:
            message = str(exc)
            if "恢复 Invalid/Watch" in message:
                raise PermissionError("恢复 Watch/Invalid 必须由合规或管理员确认。") from exc
            if "疑似重复和客户级归并" in message:
                raise PermissionError("疑似重复和客户级归并需要管理员确认。") from exc
            raise

    @staticmethod
    def ensure_pending(suggestion: LeadCleanupSuggestion) -> None:
        if LeadCleanupSuggestionReviewStatus(suggestion.review_status) != LeadCleanupSuggestionReviewStatus.PENDING:
            raise ValueError("只有 pending 清洗建议可以人工确认或拒绝。")

    def audit_review(
        self,
        suggestion: LeadCleanupSuggestion,
        *,
        action: str,
        actor: str,
        result: str,
        review_note: str,
    ) -> ReviewLog:
        log = ReviewLog(
            task_id=str(suggestion.id),
            agent_name="manual-lead-cleanup-review",
            action=action,
            reviewer=actor,
            input_ref=(
                f"suggestion:{suggestion.id};suggestion_type={suggestion.suggestion_type.value};"
                f"staging_lead_id={suggestion.staging_lead_id};target_lead_id={suggestion.target_lead_id}"
            ),
            output_ref=f"review_status={suggestion.review_status.value}",
            result=result,
            error_message=review_note,
        )
        self.session.add(log)
        return log

    def audit_execution(
        self,
        suggestion: LeadCleanupSuggestion,
        *,
        actor: str,
        result: str,
        execution_note: str,
    ) -> ReviewLog:
        log = ReviewLog(
            task_id=str(suggestion.id),
            agent_name="manual-lead-cleanup-execution",
            action="lead_cleanup_suggestion_executed",
            reviewer=actor,
            input_ref=(
                f"suggestion:{suggestion.id};suggestion_type={suggestion.suggestion_type.value};"
                f"staging_lead_id={suggestion.staging_lead_id};target_lead_id={suggestion.target_lead_id}"
            ),
            output_ref=f"review_status={suggestion.review_status.value};executed_by={suggestion.executed_by}",
            result=result,
            error_message=execution_note,
        )
        self.session.add(log)
        return log

    def audit_suggestion_created(
        self,
        suggestion: LeadCleanupSuggestion,
        *,
        actor: str,
        result: str,
        evidence_note: str,
    ) -> ReviewLog:
        log = ReviewLog(
            task_id=str(suggestion.id),
            agent_name="lead-cleanup-suggestion",
            action="lead_cleanup_suggestion_created",
            reviewer=actor,
            input_ref=(
                f"suggestion:{suggestion.id};suggestion_type={suggestion.suggestion_type.value};"
                f"staging_lead_id={suggestion.staging_lead_id};target_lead_id={suggestion.target_lead_id}"
            ),
            output_ref=f"review_status={suggestion.review_status.value}",
            result=result,
            error_message=evidence_note,
        )
        self.session.add(log)
        return log

    def run_cleanup_agent(
        self,
        cleanup_run: LeadCleanupRun,
        *,
        leads: list[dict],
        runtime,
        now: datetime | None = None,
        agents_base_url: str | None = None,
    ) -> AgentTaskRun:
        timestamp = now or datetime.now(UTC)
        task_payload = AgentTaskRunService.build_initial_payload(
            task_type=AgentTaskType.LEAD_GRADING,
            trigger_source="phase3_lead_cleanup_runtime",
            input_json={
                "cleanup_run_id": str(cleanup_run.id),
                "lead_count": len(leads),
                "input_filter_json": cleanup_run.input_filter_json or {},
            },
        )
        task_run = AgentTaskRun(**task_payload)
        self.session.add(task_run)
        self.session.flush()
        task_run.status = AgentTaskRunStatus.RUNNING
        task_run.started_at = timestamp
        task_run.updated_at = timestamp
        cleanup_run.status = LeadCleanupRunStatus.RUNNING
        cleanup_run.started_at = timestamp
        cleanup_run.updated_at = timestamp

        external_agent_response = None
        try:
            runtime_kwargs = {"cleanup_run_id": cleanup_run.id, "leads": leads}
            if hasattr(runtime, "run_lead_cleanup_response"):
                external_agent_response = runtime.run_lead_cleanup_response(**runtime_kwargs)
                output = external_agent_response.get("output") if isinstance(external_agent_response, dict) else None
            else:
                output = runtime.run_lead_cleanup(**runtime_kwargs)
            if not isinstance(output, dict):
                raise ValueError("Lead Cleanup Agent 输出缺少结构化 output。")
            if output.get("schema_version") != "phase3.agent.lead_cleanup.v1":
                raise ValueError("Lead Cleanup Agent 输出 schema_version 不正确。")
            audit = output.get("audit") or {}
            if audit.get("writes_core_tables") is not False:
                raise ValueError("Lead Cleanup Agent 输出缺少 staging/core 边界审计。")

            suggestions = [
                LeadCleanupSuggestion(
                    cleanup_run_id=cleanup_run.id,
                    staging_lead_id=UUID(str(item["staging_lead_id"])),
                    suggestion_type=LeadCleanupSuggestionType(item["suggestion_type"]),
                    target_lead_id=UUID(str(item["target_lead_id"])) if item.get("target_lead_id") else None,
                    confidence_score=item.get("confidence_score"),
                    reason=item["reason"],
                    evidence_json=item.get("evidence_json") or {},
                    recommended_action=item["recommended_action"],
                    review_status=LeadCleanupSuggestionReviewStatus(item.get("review_status") or LeadCleanupSuggestionReviewStatus.PENDING.value),
                    reviewer_id=None,
                    reviewed_at=None,
                    executed_by=None,
                    executed_at=None,
                    execution_note=None,
                    created_at=timestamp,
                    updated_at=timestamp,
                )
                for item in output.get("suggestions") or []
            ]
            self.session.add_all(suggestions)
            cleanup_run.status = LeadCleanupRunStatus.SUCCEEDED
            cleanup_run.output_summary_json = {
                "schema_version": output["schema_version"],
                "suggestion_count": len(suggestions),
                "blocked_count": len(output.get("blocked_items") or []),
                "writes_core_tables": False,
            }
            cleanup_run.finished_at = timestamp
            cleanup_run.updated_at = timestamp
            if external_agent_response is not None:
                task_payload = AgentTaskRunService.succeed_with_external_agent_summary(
                    self._task_to_payload(task_run),
                    output_summary_json=cleanup_run.output_summary_json,
                    external_agent_response=external_agent_response,
                    agents_base_url=agents_base_url or getattr(getattr(runtime, "settings", None), "agents_base_url", ""),
                )
                self._apply_task_payload(task_run, task_payload)
            else:
                task_run.status = AgentTaskRunStatus.SUCCEEDED
                task_run.output_summary_json = cleanup_run.output_summary_json
            task_run.error_message = None
            task_run.finished_at = timestamp
            task_run.updated_at = timestamp
        except Exception as exc:
            cleanup_run.status = LeadCleanupRunStatus.FAILED
            cleanup_run.output_summary_json = {
                "error": str(exc),
                "agent_task_run_id": str(task_run.id),
                "writes_core_tables": False,
            }
            cleanup_run.finished_at = timestamp
            cleanup_run.updated_at = timestamp
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
                task_run.output_summary_json = cleanup_run.output_summary_json
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

    def review_suggestion(
        self,
        suggestion_id: UUID,
        *,
        actor: str,
        actor_role: str,
        review_note: str,
        decision: LeadCleanupSuggestionReviewStatus,
        now: datetime | None = None,
    ) -> LeadCleanupSuggestion:
        if decision not in {LeadCleanupSuggestionReviewStatus.APPROVED, LeadCleanupSuggestionReviewStatus.REJECTED}:
            raise ValueError("清洗建议人工复核只支持 approve/reject。")
        suggestion = self.get_suggestion(suggestion_id)
        self.ensure_pending(suggestion)
        if decision == LeadCleanupSuggestionReviewStatus.APPROVED:
            self.validate_review_permission(suggestion, actor_role=actor_role)
        reviewed_at = now or datetime.now(UTC)
        suggestion.review_status = decision
        suggestion.reviewer_id = actor
        suggestion.reviewed_at = reviewed_at
        action = "lead_cleanup_suggestion_approved" if decision == LeadCleanupSuggestionReviewStatus.APPROVED else "lead_cleanup_suggestion_rejected"
        result = "approved" if decision == LeadCleanupSuggestionReviewStatus.APPROVED else "rejected"
        self.audit_review(
            suggestion,
            action=action,
            actor=actor,
            result=result,
            review_note=review_note,
        )
        self.session.flush()
        return suggestion

    def approve_suggestion(
        self,
        suggestion_id: UUID,
        *,
        actor: str,
        actor_role: str,
        review_note: str,
        now: datetime | None = None,
    ) -> LeadCleanupSuggestion:
        return self.review_suggestion(
            suggestion_id,
            actor=actor,
            actor_role=actor_role,
            review_note=review_note,
            decision=LeadCleanupSuggestionReviewStatus.APPROVED,
            now=now,
        )

    def reject_suggestion(
        self,
        suggestion_id: UUID,
        *,
        actor: str,
        actor_role: str,
        review_note: str,
        now: datetime | None = None,
    ) -> LeadCleanupSuggestion:
        return self.review_suggestion(
            suggestion_id,
            actor=actor,
            actor_role=actor_role,
            review_note=review_note,
            decision=LeadCleanupSuggestionReviewStatus.REJECTED,
            now=now,
        )

    @staticmethod
    def ensure_approved(suggestion: LeadCleanupSuggestion) -> None:
        if LeadCleanupSuggestionReviewStatus(suggestion.review_status) != LeadCleanupSuggestionReviewStatus.APPROVED:
            raise ValueError("未 approve 的清洗建议不能执行。")

    @staticmethod
    def contact_identity(contact: dict) -> tuple[str, str]:
        contact_type = str(contact.get("type") or contact.get("method_type") or "unknown").strip().lower()
        value = str(contact.get("value") or "").strip().lower()
        return contact_type, value

    @classmethod
    def merge_contacts(cls, target: StagingLead, source: StagingLead) -> None:
        merged = list(target.contacts_json or [])
        seen = {cls.contact_identity(item) for item in merged if isinstance(item, dict)}
        for item in source.contacts_json or []:
            if not isinstance(item, dict):
                continue
            identity = cls.contact_identity(item)
            if not identity[1] or identity in seen:
                continue
            merged.append(item)
            seen.add(identity)
        target.contacts_json = merged

    @staticmethod
    def append_source_evidence(target: StagingLead, evidence: str | None) -> None:
        evidence_text = (evidence or "").strip()
        if not evidence_text:
            return
        current = (target.source_evidence or "").strip()
        if evidence_text in current:
            return
        target.source_evidence = f"{current}\n{evidence_text}".strip() if current else evidence_text

    @classmethod
    def propagate_do_not_contact(cls, target: StagingLead, suggestion: LeadCleanupSuggestion) -> None:
        evidence = suggestion.evidence_json or {}
        if not bool(evidence.get("do_not_contact")):
            return
        reason = str(evidence.get("do_not_contact_reason") or "清洗建议传播勿扰状态。").strip()
        target.recommended_grade = CustomerGrade.WATCH
        target.queue_status = StagingQueueStatus.NOT_ELIGIBLE
        cls.append_source_evidence(target, f"勿扰状态传播：{reason}")

    def execute_suggestion(
        self,
        suggestion_id: UUID,
        *,
        actor: str,
        actor_role: str,
        execution_note: str,
        now: datetime | None = None,
    ) -> LeadCleanupSuggestion:
        suggestion = self.get_suggestion(suggestion_id)
        self.ensure_approved(suggestion)
        try:
            Phase3PermissionService.ensure_cleanup_execution_allowed(
                LeadCleanupSuggestionType(suggestion.suggestion_type),
                actor_role=actor_role,
            )
        except PermissionError as exc:
            message = str(exc)
            if "恢复 Invalid/Watch" in message:
                raise PermissionError("恢复 Watch/Invalid 必须由合规或管理员确认。") from exc
            if "重复线索和客户级归并" in message or "疑似重复和客户级归并" in message:
                raise PermissionError("疑似重复和客户级归并需要管理员确认。") from exc
            raise
        executed_at = now or datetime.now(UTC)
        source = self.get_staging_lead(suggestion.staging_lead_id, role="来源")
        target = self.get_staging_lead(suggestion.target_lead_id, role="目标") if suggestion.target_lead_id else None

        if suggestion.suggestion_type in {
            LeadCleanupSuggestionType.STRONG_DUPLICATE,
            LeadCleanupSuggestionType.POSSIBLE_DUPLICATE,
        }:
            if target is None:
                raise ValueError("重复清洗建议必须包含 target_lead_id。")
            source.review_status = StagingReviewStatus.DUPLICATE
            source.queue_status = StagingQueueStatus.NOT_ELIGIBLE
            source.dedupe_key = f"duplicate_of:{target.id}"
            self.merge_contacts(target, source)
            self.append_source_evidence(target, source.source_evidence)
            self.propagate_do_not_contact(target, suggestion)
        elif suggestion.suggestion_type == LeadCleanupSuggestionType.MERGE_CONTACT_METHOD:
            if target is None:
                raise ValueError("联系方式归并建议必须包含 target_lead_id。")
            self.merge_contacts(target, source)
            self.propagate_do_not_contact(target, suggestion)
        elif suggestion.suggestion_type == LeadCleanupSuggestionType.MERGE_SOURCE_EVIDENCE:
            if target is None:
                raise ValueError("来源证据归并建议必须包含 target_lead_id。")
            self.append_source_evidence(target, source.source_evidence)
            self.propagate_do_not_contact(target, suggestion)
        elif suggestion.suggestion_type == LeadCleanupSuggestionType.RESTORE_FROM_WATCH:
            source.review_status = StagingReviewStatus.PENDING_REVIEW
            source.queue_status = StagingQueueStatus.PENDING_REVIEW
            source.recommended_grade = CustomerGrade(str((suggestion.evidence_json or {}).get("restored_grade") or CustomerGrade.B.value))
        elif suggestion.suggestion_type == LeadCleanupSuggestionType.CONFIRM_INVALID:
            source.review_status = StagingReviewStatus.REJECTED
            source.queue_status = StagingQueueStatus.NOT_ELIGIBLE
            source.recommended_grade = CustomerGrade.INVALID
        elif suggestion.suggestion_type == LeadCleanupSuggestionType.MARK_ABANDONED:
            source.review_status = StagingReviewStatus.REJECTED
            source.queue_status = StagingQueueStatus.NOT_ELIGIBLE
        else:
            raise ValueError("该清洗建议类型不能自动执行，需保持人工复核。")

        suggestion.review_status = LeadCleanupSuggestionReviewStatus.EXECUTED
        suggestion.executed_by = actor
        suggestion.executed_at = executed_at
        suggestion.execution_note = execution_note
        self.audit_execution(suggestion, actor=actor, result="executed", execution_note=execution_note)
        self.session.flush()
        return suggestion
