from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.agents.http_runtime import HttpAgentRuntime
from app.agents.scheduler_payloads import (
    build_external_lead_extraction_grading_input,
    build_external_source_discovery_input,
)
from app.db.session import AsyncSessionLocal
from app.services.agent_locks import AgentRedisLockManager
from app.services.external_agent_result_consumer import ExternalAgentResultConsumer
from app.services.external_agent_scheduler import ExternalAgentSchedulerService
from app.settings import settings


logger = logging.getLogger("uvicorn.error")


async def run_scheduled_external_source_discovery() -> dict[str, Any]:
    request_id = str(uuid4())
    logger.info("External Source Discovery Agent 定时任务启动：request_id=%s", request_id)
    response = await HttpAgentRuntime().run_agent(
        "source-discovery",
        request_id=request_id,
        trigger_source="scheduler",
        agent_mode="shadow",
        input_payload=build_external_source_discovery_input(request_id=request_id),
        options={"timeout_seconds": settings.agents_timeout_seconds, "shadow_mode": True},
    )
    payload = _scheduled_response_summary(response)
    consumption = await consume_external_source_discovery_response(response)
    payload["consumption"] = consumption
    logger.info("External Source Discovery Agent 定时任务完成：%s", payload)
    return payload


async def run_scheduled_external_lead_extraction_grading() -> dict[str, Any]:
    request_id = str(uuid4())
    logger.info("External Lead Extraction/Grading Agent 定时任务启动：request_id=%s", request_id)
    response = await HttpAgentRuntime().run_agent(
        "lead-extraction-grading",
        request_id=request_id,
        trigger_source="scheduler",
        agent_mode="shadow",
        input_payload=build_external_lead_extraction_grading_input(request_id=request_id),
        options={"timeout_seconds": settings.agents_timeout_seconds, "shadow_mode": True},
    )
    payload = _scheduled_response_summary(response)
    consumption = await consume_external_lead_extraction_grading_response(response)
    payload["consumption"] = consumption
    logger.info("External Lead Extraction/Grading Agent 定时任务完成：%s", payload)
    return payload


async def consume_external_source_discovery_response(response: dict[str, Any]) -> dict[str, Any]:
    async with AsyncSessionLocal() as async_session:
        def run(sync_session):
            result = ExternalAgentResultConsumer(sync_session).consume_source_discovery_response(response)
            sync_session.commit()
            return {"status": result.status, **result.summary}

        return await async_session.run_sync(run)


async def consume_external_lead_extraction_grading_response(response: dict[str, Any]) -> dict[str, Any]:
    async with AsyncSessionLocal() as async_session:
        def run(sync_session):
            result = ExternalAgentResultConsumer(sync_session).consume_lead_extraction_grading_response(response)
            sync_session.commit()
            return {"status": result.status, **result.summary}

        return await async_session.run_sync(run)


def _scheduled_response_summary(response: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": response.get("status"),
        "agent_service_run_id": response.get("agent_service_run_id"),
        "request_id": response.get("request_id"),
        "agent_type": response.get("agent_type"),
        "agent_mode": response.get("agent_mode"),
        "writes_core_tables": (response.get("audit") or {}).get("writes_core_tables"),
    }


def build_external_agent_scheduler_service() -> ExternalAgentSchedulerService:
    scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")
    lock_manager = AgentRedisLockManager(ttl_seconds=settings.external_agent_scheduler_lock_ttl_seconds)
    return ExternalAgentSchedulerService(
        scheduler=scheduler,
        lock_manager=lock_manager,
        job_configs={
            "external_source_discovery": {
                "enabled": settings.external_agent_source_discovery_enabled,
                "interval_seconds": settings.external_agent_source_discovery_interval_seconds,
            },
            "external_lead_extraction_grading": {
                "enabled": settings.external_agent_lead_extraction_grading_enabled,
                "interval_seconds": settings.external_agent_lead_extraction_grading_interval_seconds,
            },
        },
        handlers={
            "external_source_discovery": run_scheduled_external_source_discovery,
            "external_lead_extraction_grading": run_scheduled_external_lead_extraction_grading,
        },
    )


def start_external_agent_scheduler() -> ExternalAgentSchedulerService | None:
    logger.info(
        "External agent scheduler bootstrap：enabled=%s redis_configured=%s lock_ttl_seconds=%s agents_base_url=%s",
        str(settings.external_agent_scheduler_enabled).lower(),
        bool(settings.redis_url),
        settings.external_agent_scheduler_lock_ttl_seconds,
        settings.agents_base_url,
    )
    if not settings.external_agent_scheduler_enabled:
        service = ExternalAgentSchedulerService(
            scheduler=AsyncIOScheduler(timezone="Asia/Shanghai"),
            lock_manager=None,
            enabled=False,
        )
        service.start()
        return None
    try:
        service = build_external_agent_scheduler_service()
        started = service.start()
    except Exception:
        logger.exception("External agent scheduler 启动失败。")
        return None
    if not started:
        return None
    return service


def shutdown_external_agent_scheduler(service: ExternalAgentSchedulerService | None) -> None:
    if service is None:
        logger.info("External agent scheduler 无需关闭：未启动。")
        return
    if getattr(service.scheduler, "running", False):
        service.scheduler.shutdown(wait=True)
        logger.info("External agent scheduler 已关闭。")
    else:
        logger.info("External agent scheduler 无需关闭：scheduler 未处于 running 状态。")
