import pytest
from pathlib import Path

from app.settings import Settings
from app.services.agent_scheduler import AgentSchedulerService


API_ROOT = Path(__file__).resolve().parents[1]


class FakeScheduler:
    def __init__(self) -> None:
        self.jobs: list[dict] = []
        self.started = False

    def add_job(self, func, trigger, **kwargs):
        self.jobs.append({"func": func, "trigger": trigger, **kwargs})

    def start(self):
        self.started = True


class FakeLockManager:
    async def run_with_lock(self, job_id, callback):
        return await callback()


async def noop_job():
    return {"status": "ok"}


class RecordingLogger:
    def __init__(self) -> None:
        self.messages: list[tuple[str, str]] = []

    def info(self, message, *args, **_kwargs) -> None:
        self.messages.append(("info", message % args if args else message))

    def warning(self, message, *args, **_kwargs) -> None:
        self.messages.append(("warning", message % args if args else message))

    def exception(self, message, *args, **_kwargs) -> None:
        self.messages.append(("exception", message % args if args else message))

    def joined(self) -> str:
        return "\n".join(message for _level, message in self.messages)


DEFAULT_TEST_JOB_CONFIGS = {
    "source_discovery_hourly": {"enabled": True, "interval_seconds": 3600},
    "lead_extraction_interval": {"enabled": True, "interval_seconds": 900},
    "retry_failed_tasks": {"enabled": True, "interval_seconds": 300},
}


def test_apscheduler_dependency_is_declared_for_deployable_scheduler() -> None:
    pyproject = (API_ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert "apscheduler" in pyproject.lower()


def test_agent_scheduler_setting_defaults_to_disabled() -> None:
    settings = Settings(_env_file=None)

    assert settings.agent_scheduler_enabled is False
    assert settings.agent_scheduler_lock_ttl_seconds == 300
    assert settings.agent_source_discovery_enabled is True
    assert settings.agent_source_discovery_interval_seconds == 3600
    assert settings.agent_lead_extraction_enabled is True
    assert settings.agent_lead_extraction_interval_seconds == 900
    assert settings.agent_retry_worker_enabled is True
    assert settings.agent_retry_worker_interval_seconds == 300


def test_agent_scheduler_does_not_register_or_start_when_disabled() -> None:
    scheduler = FakeScheduler()
    logger = RecordingLogger()
    service = AgentSchedulerService(
        scheduler=scheduler,
        lock_manager=FakeLockManager(),
        enabled=False,
        logger=logger,
        handlers={
            "source_discovery_hourly": noop_job,
            "lead_extraction_interval": noop_job,
            "retry_failed_tasks": noop_job,
        },
    )

    started = service.start()

    assert started is False
    assert scheduler.jobs == []
    assert scheduler.started is False
    assert "Agent scheduler 未启动：AGENT_SCHEDULER_ENABLED=false" in logger.joined()


def test_agent_scheduler_registers_required_jobs_before_starting() -> None:
    scheduler = FakeScheduler()
    logger = RecordingLogger()
    service = AgentSchedulerService(
        scheduler=scheduler,
        lock_manager=FakeLockManager(),
        enabled=True,
        logger=logger,
        job_configs=DEFAULT_TEST_JOB_CONFIGS,
        handlers={
            "source_discovery_hourly": noop_job,
            "lead_extraction_interval": noop_job,
            "retry_failed_tasks": noop_job,
        },
    )

    started = service.start()

    assert started is True
    assert scheduler.started is True
    assert [job["id"] for job in scheduler.jobs] == [
        "source_discovery_hourly",
        "lead_extraction_interval",
        "retry_failed_tasks",
    ]
    assert [job["trigger"] for job in scheduler.jobs] == ["interval", "interval", "interval"]
    assert [job["seconds"] for job in scheduler.jobs] == [3600, 900, 300]
    assert all(job["max_instances"] == 1 for job in scheduler.jobs)
    assert all(job["coalesce"] is True for job in scheduler.jobs)
    assert all(job["next_run_time"] is not None for job in scheduler.jobs)
    logs = logger.joined()
    assert "Agent scheduler 启动检查：enabled=true" in logs
    assert "Agent scheduler 首次执行策略：服务启动后 3 个 Agent job 立即各触发一次，之后按 interval 周期执行。" in logs
    assert "注册 Agent job：source_discovery_hourly interval=3600s initial_delay=0s" in logs
    assert "注册 Agent job：lead_extraction_interval interval=900s initial_delay=0s" in logs
    assert "注册 Agent job：retry_failed_tasks interval=300s initial_delay=0s" in logs
    assert "Agent scheduler 已启动：jobs=source_discovery_hourly,lead_extraction_interval,retry_failed_tasks" in logs


def test_agent_scheduler_can_disable_individual_jobs_and_override_intervals() -> None:
    scheduler = FakeScheduler()
    logger = RecordingLogger()
    service = AgentSchedulerService(
        scheduler=scheduler,
        lock_manager=FakeLockManager(),
        enabled=True,
        logger=logger,
        job_configs={
            "source_discovery_hourly": {"enabled": False, "interval_seconds": 7200},
            "lead_extraction_interval": {"enabled": True, "interval_seconds": 120},
            "retry_failed_tasks": {"enabled": True, "interval_seconds": 60},
        },
        handlers={
            "source_discovery_hourly": noop_job,
            "lead_extraction_interval": noop_job,
            "retry_failed_tasks": noop_job,
        },
    )

    started = service.start()

    assert started is True
    assert [job["id"] for job in scheduler.jobs] == ["lead_extraction_interval", "retry_failed_tasks"]
    assert [job["seconds"] for job in scheduler.jobs] == [120, 60]
    logs = logger.joined()
    assert "跳过 Agent job 注册：source_discovery_hourly enabled=false" in logs
    assert "注册 Agent job：lead_extraction_interval interval=120s initial_delay=0s" in logs
    assert "注册 Agent job：retry_failed_tasks interval=60s initial_delay=0s" in logs


@pytest.mark.asyncio
async def test_registered_job_wrapper_uses_redis_lock_before_running_handler() -> None:
    calls: list[str] = []
    logger = RecordingLogger()

    class RecordingLockManager:
        async def run_with_lock(self, job_id, callback):
            calls.append(f"lock:{job_id}")
            return await callback()

    async def source_job():
        calls.append("source_job")
        return {"status": "ok"}

    scheduler = FakeScheduler()
    service = AgentSchedulerService(
        scheduler=scheduler,
        lock_manager=RecordingLockManager(),
        enabled=True,
        logger=logger,
        job_configs=DEFAULT_TEST_JOB_CONFIGS,
        handlers={
            "source_discovery_hourly": source_job,
            "lead_extraction_interval": noop_job,
            "retry_failed_tasks": noop_job,
        },
    )
    service.start()

    result = await scheduler.jobs[0]["func"]()

    assert result == {"status": "ok"}
    assert calls == ["lock:source_discovery_hourly", "source_job"]
    logs = logger.joined()
    assert "Agent job 准备执行：source_discovery_hourly" in logs
    assert "Agent job 执行完成：source_discovery_hourly result={'status': 'ok'}" in logs
