from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from app.models import AgentTaskRun, EmailReplyDraft
from app.models.enums import AgentTaskRunStatus, AgentTaskType, EmailReplyDraftStatus
from app.agents.http_runtime import HttpAgentRuntime
from app.settings import Settings, settings
from app.services.agent_task_runs import AgentTaskRunService


def select_email_reply_runtime(config: Settings = settings):
    if not config.agent_email_reply_http_active_enabled or not config.http_agent_runtime_enabled:
        return None
    return HttpAgentRuntime(settings=config)


class EmailReplyAgentService:
    TRIGGER_SOURCE = "phase5_email_reply_runtime"

    @classmethod
    def run_email_reply_agent(
        cls,
        draft: EmailReplyDraft,
        *,
        runtime,
        context: dict | None,
        prompt: dict | None,
        session=None,
        options: dict | None = None,
        agent_mode: str = "active",
        dry_run: bool = False,
        now: datetime | None = None,
        agents_base_url: str | None = None,
    ) -> AgentTaskRun:
        timestamp = now or datetime.now(UTC)
        initial_payload = AgentTaskRunService.build_initial_payload(
            task_type=AgentTaskType.EMAIL_REPLY,
            trigger_source=cls.TRIGGER_SOURCE,
            input_json={
                "thread_id": str(draft.thread_id),
                "message_id": str(draft.message_id),
                "customer_id": str(draft.customer_id) if draft.customer_id else None,
                "draft_id": str(draft.id),
                "context": context or {},
                "prompt": prompt or {},
                "options": options or {},
            },
        )
        task_run = AgentTaskRun(**initial_payload)
        task_run.status = AgentTaskRunStatus.RUNNING
        task_run.started_at = timestamp
        task_run.updated_at = timestamp
        draft.agent_task_run_id = task_run.id
        draft.updated_at = timestamp
        if session is not None:
            session.add(task_run)
            session.add(draft)
            session.flush()

        external_agent_response: dict | None = None
        try:
            external_agent_response = cls._call_runtime(
                runtime,
                request_id=task_run.id,
                agent_task_run_id=task_run.id,
                draft=draft,
                context=context or {},
                prompt=prompt or {},
                options=options or {},
                agent_mode=agent_mode,
                dry_run=dry_run,
            )
            output = external_agent_response.get("output") if isinstance(external_agent_response, dict) else None
            cls._validate_output(output)
            cls._apply_output_to_draft(draft, output, external_agent_response=external_agent_response, timestamp=timestamp)
            summary = cls._success_summary(output)
            task_payload = AgentTaskRunService.succeed_with_external_agent_summary(
                cls._task_to_payload(task_run),
                output_summary_json=summary,
                external_agent_response=external_agent_response,
                agents_base_url=cls._agents_base_url(runtime, agents_base_url),
            )
            cls._apply_task_payload(task_run, task_payload)
            task_run.finished_at = timestamp
            task_run.updated_at = timestamp
        except Exception as exc:
            cls._apply_failure_to_draft(draft, error_message=str(exc), timestamp=timestamp)
            error_type = "schema_validation_error" if external_agent_response is not None else "external_agent_unavailable"
            task_payload = AgentTaskRunService.fail_with_external_agent_summary(
                cls._task_to_payload(task_run),
                error_message=str(exc),
                error={"type": error_type, "message": str(exc), "retryable": False},
                external_agent_response=external_agent_response,
                agents_base_url=cls._agents_base_url(runtime, agents_base_url),
            )
            task_payload["output_summary_json"] = {
                **(task_payload.get("output_summary_json") or {}),
                "writes_core_tables": False,
            }
            cls._apply_task_payload(task_run, task_payload)
            if task_run.status == AgentTaskRunStatus.RETRY_PENDING:
                task_run.status = AgentTaskRunStatus.FAILED
            task_run.finished_at = timestamp
            task_run.updated_at = timestamp
        return task_run

    @staticmethod
    def _call_runtime(
        runtime,
        *,
        request_id,
        agent_task_run_id,
        draft: EmailReplyDraft,
        context: dict,
        prompt: dict,
        options: dict,
        agent_mode: str,
        dry_run: bool,
    ) -> dict:
        return runtime.run_email_reply_response(
            request_id=request_id,
            agent_task_run_id=agent_task_run_id,
            thread_id=draft.thread_id,
            message_id=draft.message_id,
            customer_id=draft.customer_id,
            draft_id=draft.id,
            context=context,
            prompt=prompt,
            options=options,
            agent_mode=agent_mode,
            dry_run=dry_run,
        )

    @staticmethod
    def _validate_output(output: dict | None) -> None:
        if not isinstance(output, dict):
            raise ValueError("EMAIL_REPLY Agent 输出缺少结构化 output。")
        if output.get("schema_version") != "email-reply-v1":
            raise ValueError("EMAIL_REPLY Agent 输出 schema_version 不正确。")
        if not isinstance(output.get("suggested_body"), str) or not output.get("suggested_body", "").strip():
            raise ValueError("EMAIL_REPLY Agent 输出缺少建议回复正文。")

    @classmethod
    def _apply_output_to_draft(
        cls,
        draft: EmailReplyDraft,
        output: dict,
        *,
        external_agent_response: dict,
        timestamp: datetime,
    ) -> None:
        draft.agent_service_run_id = cls._uuid_or_none(external_agent_response.get("agent_service_run_id"))
        draft.detected_language = output.get("detected_language")
        draft.reply_language = output.get("reply_language")
        draft.language_confidence = output.get("language_confidence")
        draft.ai_suggested_subject = output.get("suggested_subject")
        draft.ai_suggested_body = output["suggested_body"]
        draft.knowledge_hits_json = list(output.get("knowledge_hits") or [])
        draft.auto_send_allowed = bool(output.get("auto_send_allowed"))
        draft.auto_send_decision_json = {
            "next_action": output.get("next_action"),
            "risk_flags": list(output.get("risk_flags") or []),
            "audit": dict(output.get("audit") or {}),
        }
        draft.manual_review_required = bool(output.get("manual_review_required", True))
        draft.manual_review_reason = output.get("manual_review_reason")
        draft.prompt_version = (output.get("audit") or {}).get("prompt_version")
        draft.model = (output.get("audit") or {}).get("model")
        draft.status = EmailReplyDraftStatus.PENDING_REVIEW if draft.manual_review_required else EmailReplyDraftStatus.APPROVED
        draft.updated_at = timestamp

    @staticmethod
    def _apply_failure_to_draft(draft: EmailReplyDraft, *, error_message: str, timestamp: datetime) -> None:
        draft.status = EmailReplyDraftStatus.FAILED
        draft.manual_review_required = True
        draft.manual_review_reason = f"EMAIL_REPLY Agent 调用失败：{error_message}"
        draft.auto_send_allowed = False
        draft.updated_at = timestamp

    @staticmethod
    def _success_summary(output: dict) -> dict:
        return {
            "schema_version": output["schema_version"],
            "knowledge_hit_count": len(output.get("knowledge_hits") or []),
            "auto_send_allowed": bool(output.get("auto_send_allowed")),
            "manual_review_required": bool(output.get("manual_review_required", True)),
            "next_action": output.get("next_action"),
            "writes_core_tables": False,
        }

    @staticmethod
    def _task_to_payload(task_run: AgentTaskRun) -> dict:
        return {
            "id": task_run.id,
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
    def _agents_base_url(runtime, explicit: str | None) -> str:
        if explicit is not None:
            return explicit
        return getattr(getattr(runtime, "settings", None), "agents_base_url", "") or ""

    @staticmethod
    def _uuid_or_none(value) -> UUID | None:
        return UUID(str(value)) if value else None
