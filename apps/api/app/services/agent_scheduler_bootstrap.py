from __future__ import annotations

import logging
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import func, select

from app.db.session import AsyncSessionLocal
from app.models.agent_task_run import AgentTaskRun
from app.models.enums import (
    AgentTaskRunStatus,
    AgentTaskType,
    ChannelRiskLevel,
    LeadSourceCandidateExtractionStatus,
    LeadSourceCandidateReviewStatus,
)
from app.models.lead_source_candidate import LeadSourceCandidate
from app.services.agent_locks import AgentRedisLockManager
from app.services.agent_scheduler import AgentSchedulerService
from app.services.lead_extraction_from_sources import LeadExtractionFromSourcesService
from app.services.source_discovery_agent import SourceDiscoveryAgentRequest, SourceDiscoveryAgentService
from app.settings import settings


logger = logging.getLogger("uvicorn.error")


async def run_scheduled_source_discovery() -> dict[str, Any]:
    logger.info("Source Discovery Agent 定时任务启动。")
    request = SourceDiscoveryAgentRequest(
        country="Russia",
        city=None,
        channel_strategy="Low/Medium 风险公开渠道来源发现；不得登录；不得自动私信；不得自动加好友；不得反爬规避。",
        keywords=["автодилер", "автосалон", "used cars", "import cars"],
        max_candidates=20,
        trigger_source="scheduler_source_discovery_hourly",
    )
    async with AsyncSessionLocal() as async_session:
        result = await SourceDiscoveryAgentService(async_session=async_session).run(request)
        payload = {
            "status": result.task_run.status.value,
            "agent_task_run_id": str(result.task_run.id),
            "created_count": result.created_count,
            "updated_count": result.updated_count,
            "blocked_count": result.blocked_count,
            "duplicate_count": result.duplicate_count,
        }
        logger.info("Source Discovery Agent 定时任务完成：%s", payload)
        return payload


async def run_scheduled_lead_extraction() -> dict[str, Any]:
    logger.info("Lead Extraction Agent 定时任务启动。")
    async with AsyncSessionLocal() as async_session:
        def run(sync_session):
            eligible_source_count = count_eligible_lead_extraction_sources(sync_session)
            logger.info("Lead Extraction Agent 来源准入检查：eligible_source_count=%s", eligible_source_count)
            service = LeadExtractionFromSourcesService(sync_session)
            try:
                selection = service.create_lead_extraction_task_from_sources(
                    limit=10,
                    trigger_source="scheduler_lead_extraction_interval",
                    country="Russia",
                )
            except ValueError as exc:
                sync_session.rollback()
                return {
                    "status": "skipped",
                    "reason": "no_eligible_approved_sources",
                    "eligible_source_count": eligible_source_count,
                    "message": str(exc),
                }
            summary = service.run_queued_lead_extraction_task(selection.task_run.id)
            sync_session.commit()
            return {
                "status": selection.task_run.status.value,
                "agent_task_run_id": str(selection.task_run.id),
                "eligible_source_count": eligible_source_count,
                "selected_count": len(selection.selected_candidates),
                "blocked_count": len(selection.blocked_candidates),
                **summary,
            }

        payload = await async_session.run_sync(run)
        logger.info("Lead Extraction Agent 定时任务完成：%s", payload)
        return payload


async def run_scheduled_retry_worker() -> dict[str, Any]:
    logger.info("Retry Worker Agent 定时任务启动。")
    async with AsyncSessionLocal() as async_session:
        statement = (
            select(AgentTaskRun)
            .where(
                AgentTaskRun.status == AgentTaskRunStatus.RETRY_PENDING,
                AgentTaskRun.task_type.in_([AgentTaskType.LEAD_EXTRACTION]),
            )
            .order_by(AgentTaskRun.updated_at.asc(), AgentTaskRun.id.asc())
            .limit(5)
        )

        def run(sync_session):
            tasks = list(sync_session.scalars(statement).all())
            processed: list[dict[str, str]] = []
            for task in tasks:
                if task.task_type == AgentTaskType.LEAD_EXTRACTION:
                    summary = LeadExtractionFromSourcesService(sync_session).run_queued_lead_extraction_task(task.id)
                    processed.append(
                        {
                            "agent_task_run_id": str(task.id),
                            "task_type": task.task_type.value,
                            "status": task.status.value,
                            "summary": str(summary),
                        }
                    )
            sync_session.commit()
            return {"status": "ok", "processed_count": len(processed), "processed": processed}

        payload = await async_session.run_sync(run)
        logger.info("Retry Worker Agent 定时任务完成：%s", payload)
        return payload


def count_eligible_lead_extraction_sources(sync_session) -> int:
    return sync_session.scalar(
        select(func.count())
        .select_from(LeadSourceCandidate)
        .where(
            LeadSourceCandidate.risk_level.in_([ChannelRiskLevel.LOW, ChannelRiskLevel.MEDIUM]),
            LeadSourceCandidate.review_status.in_(
                [
                    LeadSourceCandidateReviewStatus.AUTO_APPROVED,
                    LeadSourceCandidateReviewStatus.APPROVED,
                ]
            ),
            LeadSourceCandidate.approved_for_extraction.is_(True),
            LeadSourceCandidate.extraction_status.in_(
                [
                    LeadSourceCandidateExtractionStatus.PENDING,
                    LeadSourceCandidateExtractionStatus.RETRY,
                ]
            ),
        )
    ) or 0


def build_agent_scheduler_service() -> AgentSchedulerService:
    scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")
    lock_manager = AgentRedisLockManager(ttl_seconds=settings.agent_scheduler_lock_ttl_seconds)
    return AgentSchedulerService(
        scheduler=scheduler,
        lock_manager=lock_manager,
        job_configs={
            "source_discovery_hourly": {
                "enabled": settings.agent_source_discovery_enabled,
                "interval_seconds": settings.agent_source_discovery_interval_seconds,
            },
            "lead_extraction_interval": {
                "enabled": settings.agent_lead_extraction_enabled,
                "interval_seconds": settings.agent_lead_extraction_interval_seconds,
            },
            "retry_failed_tasks": {
                "enabled": settings.agent_retry_worker_enabled,
                "interval_seconds": settings.agent_retry_worker_interval_seconds,
            },
        },
        handlers={
            "source_discovery_hourly": run_scheduled_source_discovery,
            "lead_extraction_interval": run_scheduled_lead_extraction,
            "retry_failed_tasks": run_scheduled_retry_worker,
        },
    )


def start_agent_scheduler() -> AgentSchedulerService | None:
    logger.info(
        "Agent scheduler bootstrap：enabled=%s redis_configured=%s lock_ttl_seconds=%s",
        str(settings.agent_scheduler_enabled).lower(),
        bool(settings.redis_url),
        settings.agent_scheduler_lock_ttl_seconds,
    )
    if not settings.agent_scheduler_enabled:
        service = AgentSchedulerService(
            scheduler=AsyncIOScheduler(timezone="Asia/Shanghai"),
            lock_manager=None,
            enabled=False,
        )
        service.start()
        return None
    try:
        service = build_agent_scheduler_service()
        started = service.start()
    except Exception:
        logger.exception("Agent scheduler 启动失败。")
        return None
    if not started:
        return None
    return service


def shutdown_agent_scheduler(service: AgentSchedulerService | None) -> None:
    if service is None:
        logger.info("Agent scheduler 无需关闭：未启动。")
        return
    if getattr(service.scheduler, "running", False):
        service.scheduler.shutdown(wait=True)
        logger.info("Agent scheduler 已关闭。")
    else:
        logger.info("Agent scheduler 无需关闭：scheduler 未处于 running 状态。")
