from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta
import logging

from app.settings import settings


AgentJobHandler = Callable[[], Awaitable[object]]
logger = logging.getLogger("uvicorn.error")


async def source_discovery_hourly_placeholder() -> dict[str, str]:
    return {"status": "not_implemented", "job_id": "source_discovery_hourly"}


async def lead_extraction_interval_placeholder() -> dict[str, str]:
    return {"status": "not_implemented", "job_id": "lead_extraction_interval"}


async def retry_failed_tasks_placeholder() -> dict[str, str]:
    return {"status": "not_implemented", "job_id": "retry_failed_tasks"}


class AgentSchedulerService:
    REQUIRED_JOBS = ("source_discovery_hourly", "lead_extraction_interval", "retry_failed_tasks")

    def __init__(
        self,
        *,
        scheduler,
        lock_manager,
        enabled: bool | None = None,
        handlers: dict[str, AgentJobHandler] | None = None,
        job_configs: dict[str, dict[str, int | bool]] | None = None,
        logger=None,
    ) -> None:
        self.scheduler = scheduler
        self.lock_manager = lock_manager
        self.enabled = settings.agent_scheduler_enabled if enabled is None else enabled
        self.logger = logger or globals()["logger"]
        self.handlers = {
            "source_discovery_hourly": source_discovery_hourly_placeholder,
            "lead_extraction_interval": lead_extraction_interval_placeholder,
            "retry_failed_tasks": retry_failed_tasks_placeholder,
            **(handlers or {}),
        }
        self.job_configs = job_configs or self.default_job_configs()
        self._registered = False

    @staticmethod
    def default_job_configs() -> dict[str, dict[str, int | bool]]:
        return {
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
        }

    def start(self) -> bool:
        self.logger.info(
            "Agent scheduler 启动检查：enabled=%s lock_ttl_seconds=%s",
            str(bool(self.enabled)).lower(),
            settings.agent_scheduler_lock_ttl_seconds,
        )
        if not self.enabled:
            self.logger.info("Agent scheduler 未启动：AGENT_SCHEDULER_ENABLED=false")
            return False
        self.register_jobs()
        self.scheduler.start()
        self.logger.info(
            "Agent scheduler 已启动：jobs=%s",
            ",".join(job["id"] for job in self.enabled_job_specs()),
        )
        return True

    def register_jobs(self) -> None:
        if self._registered:
            self.logger.info("Agent scheduler job 已注册，跳过重复注册。")
            return
        self.logger.info("Agent scheduler 首次执行策略：服务启动后 3 个 Agent job 立即各触发一次，之后按 interval 周期执行。")
        now = datetime.now()
        for spec in self.job_specs():
            job_id = spec["id"]
            if not spec["enabled"]:
                self.logger.info("跳过 Agent job 注册：%s enabled=false", job_id)
                continue
            seconds = spec["interval_seconds"]
            initial_delay_seconds = spec["initial_delay_seconds"]
            first_run_time = now + timedelta(seconds=initial_delay_seconds)
            self.logger.info(
                "注册 Agent job：%s interval=%ss initial_delay=%ss",
                job_id,
                seconds,
                initial_delay_seconds,
            )
            self.scheduler.add_job(
                self._build_locked_job(job_id),
                "interval",
                seconds=seconds,
                id=job_id,
                next_run_time=first_run_time,
                max_instances=1,
                coalesce=True,
                replace_existing=True,
            )
        self._registered = True

    def job_specs(self) -> list[dict[str, int | bool | str]]:
        specs: list[dict[str, int | bool | str]] = []
        for job_id in self.REQUIRED_JOBS:
            config = self.job_configs.get(job_id, {})
            specs.append(
                {
                    "id": job_id,
                    "enabled": bool(config.get("enabled", True)),
                    "interval_seconds": int(config.get("interval_seconds", 300)),
                    "initial_delay_seconds": int(config.get("initial_delay_seconds", 0)),
                }
            )
        return specs

    def enabled_job_specs(self) -> list[dict[str, int | bool | str]]:
        return [spec for spec in self.job_specs() if spec["enabled"]]

    def _build_locked_job(self, job_id: str):
        async def run_job():
            self.logger.info("Agent job 准备执行：%s", job_id)
            try:
                result = await self.lock_manager.run_with_lock(job_id, self.handlers[job_id])
            except Exception:
                self.logger.exception("Agent job 执行异常：%s", job_id)
                raise
            if isinstance(result, dict) and result.get("status") == "skipped":
                self.logger.warning("Agent job 跳过执行：%s result=%s", job_id, result)
            else:
                self.logger.info("Agent job 执行完成：%s result=%s", job_id, result)
            return result

        return run_job
