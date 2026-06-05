from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta
import logging

from app.settings import settings


ExternalAgentJobHandler = Callable[[], Awaitable[object]]
logger = logging.getLogger("uvicorn.error")


class ExternalAgentSchedulerService:
    REQUIRED_JOBS = ("external_source_discovery", "external_lead_extraction_grading")

    def __init__(
        self,
        *,
        scheduler,
        lock_manager,
        enabled: bool | None = None,
        handlers: dict[str, ExternalAgentJobHandler] | None = None,
        job_configs: dict[str, dict[str, int | bool]] | None = None,
        logger=None,
    ) -> None:
        self.scheduler = scheduler
        self.lock_manager = lock_manager
        self.enabled = settings.external_agent_scheduler_enabled if enabled is None else enabled
        self.logger = logger or globals()["logger"]
        self.handlers = handlers or {}
        self.job_configs = job_configs or self.default_job_configs()
        self._registered = False

    @staticmethod
    def default_job_configs() -> dict[str, dict[str, int | bool]]:
        return {
            "external_source_discovery": {
                "enabled": settings.external_agent_source_discovery_enabled,
                "interval_seconds": settings.external_agent_source_discovery_interval_seconds,
            },
            "external_lead_extraction_grading": {
                "enabled": settings.external_agent_lead_extraction_grading_enabled,
                "interval_seconds": settings.external_agent_lead_extraction_grading_interval_seconds,
            },
        }

    def start(self) -> bool:
        self.logger.info(
            "External agent scheduler 启动检查：enabled=%s lock_ttl_seconds=%s",
            str(bool(self.enabled)).lower(),
            settings.external_agent_scheduler_lock_ttl_seconds,
        )
        if not self.enabled:
            self.logger.info("External agent scheduler 未启动：EXTERNAL_AGENT_SCHEDULER_ENABLED=false")
            return False
        self.register_jobs()
        self.scheduler.start()
        self.logger.info(
            "External agent scheduler 已启动：jobs=%s",
            ",".join(job["id"] for job in self.enabled_job_specs()),
        )
        return True

    def register_jobs(self) -> None:
        if self._registered:
            self.logger.info("External agent scheduler job 已注册，跳过重复注册。")
            return
        self.logger.info("External agent scheduler 首次执行策略：启用的 HTTP Agent job 启动后立即触发一次，之后按 interval 周期执行。")
        now = datetime.now()
        for spec in self.job_specs():
            job_id = spec["id"]
            if not spec["enabled"]:
                self.logger.info("跳过 External agent job 注册：%s enabled=false", job_id)
                continue
            if job_id not in self.handlers:
                self.logger.warning("跳过 External agent job 注册：%s handler_missing=true", job_id)
                continue
            seconds = spec["interval_seconds"]
            initial_delay_seconds = spec["initial_delay_seconds"]
            self.logger.info(
                "注册 External agent job：%s interval=%ss initial_delay=%ss",
                job_id,
                seconds,
                initial_delay_seconds,
            )
            self.scheduler.add_job(
                self._build_locked_job(job_id),
                "interval",
                seconds=seconds,
                id=job_id,
                next_run_time=now + timedelta(seconds=initial_delay_seconds),
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
                    "enabled": bool(config.get("enabled", False)),
                    "interval_seconds": int(config.get("interval_seconds", 300)),
                    "initial_delay_seconds": int(config.get("initial_delay_seconds", 0)),
                }
            )
        return specs

    def enabled_job_specs(self) -> list[dict[str, int | bool | str]]:
        return [spec for spec in self.job_specs() if spec["enabled"] and spec["id"] in self.handlers]

    def _build_locked_job(self, job_id: str):
        async def run_job():
            self.logger.info("External agent job 准备执行：%s", job_id)
            try:
                result = await self.lock_manager.run_with_lock(job_id, self.handlers[job_id])
            except Exception:
                self.logger.exception("External agent job 执行异常：%s", job_id)
                raise
            self.logger.info("External agent job 执行完成：%s result=%s", job_id, result)
            return result

        return run_job
