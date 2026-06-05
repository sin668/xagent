from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.agent_service_run import AgentServiceRun
from app.schemas.trace import AgentNodeTrace, AgentNodeTraceError, AgentRunTraceAudit
from app.services.retry_policy import DEFAULT_MAX_RETRIES, RetryPolicy


TERMINAL_STATUSES = {"succeeded", "failed", "blocked", "cancelled"}


class InvalidAgentRunTransition(ValueError):
    pass


class AgentRunNotFound(LookupError):
    pass


class AgentServiceRunService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_run(
        self,
        *,
        request_id: str | UUID,
        agent_type: str,
        agent_mode: str,
        trigger_source: str,
        input_json: dict,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ) -> AgentServiceRun:
        run = AgentServiceRun(
            request_id=UUID(str(request_id)),
            agent_type=agent_type,
            agent_mode=agent_mode,
            status="pending",
            trigger_source=trigger_source,
            input_json=input_json,
            audit_json={},
            retry_count=0,
            max_retries=max_retries,
        )
        self.session.add(run)
        self.session.commit()
        self.session.refresh(run)
        return run

    def get_run(self, run_id: UUID) -> AgentServiceRun:
        run = self.session.get(AgentServiceRun, run_id)
        if run is None:
            raise AgentRunNotFound(f"Agent service run not found: {run_id}")
        return run

    def mark_running(self, run_id: UUID) -> AgentServiceRun:
        run = self.get_run(run_id)
        self._ensure_not_terminal(run)
        now = self._now()
        run.status = "running"
        run.started_at = run.started_at or now
        run.updated_at = now
        return self._save(run)

    def mark_retrying(
        self,
        run_id: UUID,
        *,
        error_type: str,
        error_message: str,
        next_retry_at: datetime | None = None,
    ) -> AgentServiceRun:
        run = self.get_run(run_id)
        self._ensure_not_terminal(run)
        now = self._now()
        run.status = "retrying"
        run.retry_count += 1
        run.next_retry_at = next_retry_at
        run.error_type = error_type
        run.error_message = error_message
        run.updated_at = now
        return self._save(run)

    def record_failure_with_retry_policy(
        self,
        run_id: UUID,
        *,
        error_type: str,
        error_message: str,
    ) -> AgentServiceRun:
        run = self.get_run(run_id)
        self._ensure_not_terminal(run)
        policy = RetryPolicy(max_retries=run.max_retries)
        now = self._now()
        decision = policy.decide(error_type=error_type, retry_count=run.retry_count, now=now)

        if decision.should_retry:
            return self.mark_retrying(
                run_id,
                error_type=error_type,
                error_message=error_message,
                next_retry_at=decision.next_retry_at,
            )

        run.next_retry_at = None
        return self.mark_failed(run_id, error_type=error_type, error_message=error_message)

    def append_node_trace(self, run_id: UUID, trace: AgentNodeTrace) -> AgentServiceRun:
        run = self.get_run(run_id)
        audit = self._trace_audit_from_run(run)
        audit.executed_nodes.append(trace)
        run.audit_json = self._merge_trace_audit(run.audit_json or {}, audit)
        run.updated_at = self._now()
        return self._save(run)

    def update_trace_summary(
        self,
        run_id: UUID,
        *,
        risk_flags: list[str] | None = None,
        source_urls: list[str] | None = None,
        failed_node: str | None = None,
    ) -> AgentServiceRun:
        run = self.get_run(run_id)
        audit = self._trace_audit_from_run(run)
        if risk_flags is not None:
            audit.risk_flags = self._merge_unique(audit.risk_flags, risk_flags)
        if source_urls is not None:
            audit.source_urls = self._merge_unique(audit.source_urls, source_urls)
        if failed_node is not None:
            audit.failed_node = failed_node
        run.audit_json = self._merge_trace_audit(run.audit_json or {}, audit)
        run.updated_at = self._now()
        return self._save(run)

    def record_failed_node_trace(
        self,
        run_id: UUID,
        *,
        node: str,
        duration_ms: int,
        error_type: str,
        error_message: str,
        retryable: bool,
        input_summary: dict | None = None,
        output_summary: dict | None = None,
    ) -> AgentServiceRun:
        trace = AgentNodeTrace(
            node=node,
            status="failed",
            duration_ms=duration_ms,
            input_summary=input_summary or {},
            output_summary=output_summary or {},
            error=AgentNodeTraceError(error_type=error_type, message=error_message, retryable=retryable),
        )
        run = self.append_node_trace(run_id, trace)
        return self.update_trace_summary(run.id, failed_node=node)

    def mark_succeeded(
        self,
        run_id: UUID,
        *,
        output_json: dict | None = None,
        output_summary_json: dict | None = None,
    ) -> AgentServiceRun:
        run = self.get_run(run_id)
        self._ensure_not_terminal(run)
        now = self._now()
        run.status = "succeeded"
        run.output_json = output_json
        run.output_summary_json = output_summary_json
        run.finished_at = now
        run.updated_at = now
        return self._save(run)

    def mark_failed(self, run_id: UUID, *, error_type: str, error_message: str) -> AgentServiceRun:
        return self._mark_terminal_error(run_id, "failed", error_type=error_type, error_message=error_message)

    def mark_blocked(self, run_id: UUID, *, error_type: str, error_message: str) -> AgentServiceRun:
        return self._mark_terminal_error(run_id, "blocked", error_type=error_type, error_message=error_message)

    def mark_cancelled(self, run_id: UUID) -> AgentServiceRun:
        run = self.get_run(run_id)
        self._ensure_not_terminal(run)
        now = self._now()
        run.status = "cancelled"
        run.finished_at = now
        run.updated_at = now
        return self._save(run)

    def _mark_terminal_error(
        self,
        run_id: UUID,
        status: str,
        *,
        error_type: str,
        error_message: str,
    ) -> AgentServiceRun:
        run = self.get_run(run_id)
        self._ensure_not_terminal(run)
        now = self._now()
        run.status = status
        run.error_type = error_type
        run.error_message = error_message
        run.finished_at = now
        run.updated_at = now
        return self._save(run)

    def _save(self, run: AgentServiceRun) -> AgentServiceRun:
        self.session.add(run)
        self.session.commit()
        self.session.refresh(run)
        return run

    def _trace_audit_from_run(self, run: AgentServiceRun) -> AgentRunTraceAudit:
        raw_audit = run.audit_json or {}
        trace_fields = set(AgentRunTraceAudit.model_fields)
        return AgentRunTraceAudit(**{key: value for key, value in raw_audit.items() if key in trace_fields})

    def _merge_trace_audit(self, raw_audit: dict, audit: AgentRunTraceAudit) -> dict:
        return {**raw_audit, **audit.model_dump()}

    def _merge_unique(self, current: list[str], incoming: list[str]) -> list[str]:
        values: list[str] = []
        seen: set[str] = set()
        for item in [*current, *incoming]:
            value = str(item)
            if value in seen:
                continue
            seen.add(value)
            values.append(value)
        return values

    def _ensure_not_terminal(self, run: AgentServiceRun) -> None:
        if run.status in TERMINAL_STATUSES:
            raise InvalidAgentRunTransition(f"Agent run {run.id} is already terminal: {run.status}")

    def _now(self) -> datetime:
        return datetime.now(UTC)
