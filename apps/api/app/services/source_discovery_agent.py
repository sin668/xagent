from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.models.agent_task_run import AgentTaskRun
from app.models.enums import AgentTaskRunStatus, AgentTaskType, LLMPromptTaskType, LLMPromptTemplateStatus
from app.models.llm_prompt_template import LLMPromptTemplate
from app.services.lead_source_candidates import LeadSourceCandidateBatchResult, LeadSourceCandidateService
from app.services.llm_client import LLMClient, LLMClientResult
from app.services.source_discovery_schema import SourceDiscoverySchemaService, SourceDiscoveryValidationError


class SourceDiscoveryLLMClient(Protocol):
    async def generate_json(
        self,
        task_type: str,
        system_prompt: str,
        user_prompt: str,
        output_schema: dict[str, Any],
    ) -> LLMClientResult:
        ...


class SourceDiscoveryAgentRequest(BaseModel):
    country: str = Field(min_length=1, max_length=80)
    city: str | None = Field(default=None, max_length=120)
    channel_strategy: str = Field(min_length=1, max_length=160)
    keywords: list[str] = Field(default_factory=list)
    max_candidates: int = Field(default=50, gt=0, le=500)
    trigger_source: str = Field(default="manual", min_length=1, max_length=80)


@dataclass(frozen=True)
class SourceDiscoveryAgentResult:
    task_run: AgentTaskRun
    created_count: int
    updated_count: int
    blocked_count: int
    duplicate_count: int
    error: dict[str, str] | None = None


class SourceDiscoveryAgentService:
    def __init__(self, *, async_session: AsyncSession, llm_client: SourceDiscoveryLLMClient | None = None) -> None:
        self.async_session = async_session
        self.llm_client = llm_client or LLMClient()

    async def run(self, request: SourceDiscoveryAgentRequest) -> SourceDiscoveryAgentResult:
        task_run = await self.create_pending_task(request)
        return await self.run_existing_task(task_run.id)

    async def create_pending_task(self, request: SourceDiscoveryAgentRequest) -> AgentTaskRun:
        task_run, _prompt_template = await self.async_session.run_sync(self._create_pending_task, request)
        await self.async_session.commit()
        return task_run

    async def run_existing_task(self, task_run_id) -> SourceDiscoveryAgentResult:
        task_run, prompt_template = await self.async_session.run_sync(self._start_existing_task, task_run_id)
        await self.async_session.commit()
        request = SourceDiscoveryAgentRequest.model_validate(task_run.input_json or {})
        user_prompt = self._render_user_prompt(prompt_template.user_prompt_template, request)
        llm_result = await self.llm_client.generate_json(
            "SOURCE_DISCOVERY",
            prompt_template.system_prompt,
            user_prompt,
            prompt_template.output_schema_json,
        )

        if llm_result.error:
            return await self._mark_failed(task_run.id, llm_result, llm_result.error)

        try:
            SourceDiscoverySchemaService.validate_output(llm_result.output_json)
        except SourceDiscoveryValidationError as exc:
            error = {"type": exc.error_type, "message": str(exc)}
            return await self._mark_manual_review(task_run.id, llm_result, error)

        return await self._upsert_and_mark_succeeded(task_run.id, llm_result)

    def _create_pending_task(
        self,
        sync_session: Session,
        request: SourceDiscoveryAgentRequest,
    ) -> tuple[AgentTaskRun, LLMPromptTemplate]:
        prompt_template = self._load_active_default_prompt(sync_session)
        task_run = AgentTaskRun(
            task_type=AgentTaskType.SOURCE_DISCOVERY,
            status=AgentTaskRunStatus.PENDING,
            trigger_source=request.trigger_source,
            input_json=request.model_dump(),
            prompt_template_id=prompt_template.id,
            prompt_version=prompt_template.version,
            llm_provider=prompt_template.provider,
            llm_model=prompt_template.model,
        )
        sync_session.add(task_run)
        sync_session.flush()
        return task_run, prompt_template

    def _start_existing_task(self, sync_session: Session, task_run_id) -> tuple[AgentTaskRun, LLMPromptTemplate]:
        task_run = sync_session.get(AgentTaskRun, task_run_id)
        if task_run is None:
            raise ValueError("SOURCE_DISCOVERY agent_task_run 不存在。")
        if task_run.task_type != AgentTaskType.SOURCE_DISCOVERY:
            raise ValueError("agent_task_run 不是 SOURCE_DISCOVERY 类型。")
        if task_run.status not in {AgentTaskRunStatus.PENDING, AgentTaskRunStatus.RETRY_PENDING}:
            raise ValueError("只有 pending 或 retry_pending 的 SOURCE_DISCOVERY 任务可以执行。")
        prompt_template = sync_session.get(LLMPromptTemplate, task_run.prompt_template_id)
        if prompt_template is None:
            prompt_template = self._load_active_default_prompt(sync_session)
        task_run.status = AgentTaskRunStatus.RUNNING
        sync_session.flush()
        return task_run, prompt_template

    def _load_active_default_prompt(self, sync_session: Session) -> LLMPromptTemplate:
        prompt_template = sync_session.scalar(
            select(LLMPromptTemplate).where(
                LLMPromptTemplate.task_type == LLMPromptTaskType.SOURCE_DISCOVERY,
                LLMPromptTemplate.status == LLMPromptTemplateStatus.ACTIVE,
                LLMPromptTemplate.is_default.is_(True),
            )
        )
        if prompt_template is None:
            raise ValueError("缺少 active default SOURCE_DISCOVERY prompt template")
        return prompt_template

    def _render_user_prompt(self, template: str, request: SourceDiscoveryAgentRequest) -> str:
        rendered = template.format(
            country=request.country,
            city=request.city or "Unknown",
            channel_strategy=request.channel_strategy,
            keywords=", ".join(request.keywords) if request.keywords else "Unknown",
            max_candidates=request.max_candidates,
        )
        keywords = ", ".join(request.keywords) if request.keywords else "Unknown"
        return (
            f"{rendered}\n\n"
            "本次运行变量：\n"
            f"- 国家：{request.country}\n"
            f"- 城市：{request.city or 'Unknown'}\n"
            f"- 渠道策略：{request.channel_strategy}\n"
            f"- 关键词：{keywords}\n"
            f"- 候选来源上限：{request.max_candidates}"
        )

    async def _upsert_and_mark_succeeded(
        self,
        task_run_id,
        llm_result: LLMClientResult,
    ) -> SourceDiscoveryAgentResult:
        def run(sync_session: Session) -> SourceDiscoveryAgentResult:
            task_run = sync_session.get(AgentTaskRun, task_run_id)
            batch = LeadSourceCandidateService(sync_session).upsert_from_source_discovery_output(
                llm_result.output_json,
                created_by_task_run_id=task_run.id,
                llm_provider=llm_result.provider,
                llm_model=llm_result.model,
                llm_output_json=llm_result.output_json,
            )
            self._apply_llm_audit(task_run, llm_result)
            task_run.status = AgentTaskRunStatus.SUCCEEDED
            task_run.output_summary_json = self._summary(batch=batch)
            task_run.error_message = None
            sync_session.flush()
            return SourceDiscoveryAgentResult(
                task_run=task_run,
                created_count=batch.created_count,
                updated_count=batch.updated_count,
                blocked_count=batch.blocked_count,
                duplicate_count=batch.duplicate_count,
            )

        result = await self.async_session.run_sync(run)
        await self.async_session.commit()
        return result

    async def _mark_manual_review(
        self,
        task_run_id,
        llm_result: LLMClientResult,
        error: dict[str, str],
    ) -> SourceDiscoveryAgentResult:
        return await self._mark_terminal(
            task_run_id,
            status=AgentTaskRunStatus.MANUAL_REVIEW_REQUIRED,
            llm_result=llm_result,
            error=error,
        )

    async def _mark_failed(
        self,
        task_run_id,
        llm_result: LLMClientResult,
        error: dict[str, str],
    ) -> SourceDiscoveryAgentResult:
        return await self._mark_terminal(
            task_run_id,
            status=AgentTaskRunStatus.FAILED,
            llm_result=llm_result,
            error=error,
        )

    async def _mark_terminal(
        self,
        task_run_id,
        *,
        status: AgentTaskRunStatus,
        llm_result: LLMClientResult,
        error: dict[str, str],
    ) -> SourceDiscoveryAgentResult:
        def run(sync_session: Session) -> SourceDiscoveryAgentResult:
            task_run = sync_session.get(AgentTaskRun, task_run_id)
            self._apply_llm_audit(task_run, llm_result)
            task_run.status = status
            task_run.error_message = error["message"]
            task_run.output_summary_json = {"error": error}
            sync_session.flush()
            return SourceDiscoveryAgentResult(
                task_run=task_run,
                created_count=0,
                updated_count=0,
                blocked_count=0,
                duplicate_count=0,
                error=error,
            )

        result = await self.async_session.run_sync(run)
        await self.async_session.commit()
        return result

    def _apply_llm_audit(self, task_run: AgentTaskRun, llm_result: LLMClientResult) -> None:
        task_run.llm_provider = llm_result.provider
        task_run.llm_model = llm_result.model
        task_run.token_usage_json = llm_result.token_usage
        task_run.latency_ms = llm_result.latency_ms

    def _summary(self, *, batch: LeadSourceCandidateBatchResult) -> dict[str, Any]:
        return {
            "created_count": batch.created_count,
            "updated_count": batch.updated_count,
            "blocked_count": batch.blocked_count,
            "duplicate_count": batch.duplicate_count,
        }
