import pytest

from app.agents.scheduler_payloads import (
    build_external_lead_extraction_grading_input,
    build_external_source_discovery_input,
)
from app.services.external_agent_scheduler import ExternalAgentSchedulerService
from app.services.external_agent_scheduler_bootstrap import (
    run_scheduled_external_lead_extraction_grading,
    run_scheduled_external_source_discovery,
)


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


def test_external_agent_scheduler_defaults_to_disabled_and_registers_no_jobs() -> None:
    scheduler = FakeScheduler()
    logger = RecordingLogger()
    service = ExternalAgentSchedulerService(
        scheduler=scheduler,
        lock_manager=FakeLockManager(),
        enabled=False,
        logger=logger,
        handlers={
            "external_source_discovery": noop_job,
            "external_lead_extraction_grading": noop_job,
        },
    )

    started = service.start()

    assert started is False
    assert scheduler.jobs == []
    assert scheduler.started is False
    assert "External agent scheduler 未启动：EXTERNAL_AGENT_SCHEDULER_ENABLED=false" in logger.joined()


def test_external_agent_scheduler_registers_jobs_independent_from_legacy_agent_config() -> None:
    scheduler = FakeScheduler()
    logger = RecordingLogger()
    service = ExternalAgentSchedulerService(
        scheduler=scheduler,
        lock_manager=FakeLockManager(),
        enabled=True,
        logger=logger,
        job_configs={
            "external_source_discovery": {"enabled": True, "interval_seconds": 900},
            "external_lead_extraction_grading": {"enabled": True, "interval_seconds": 300},
        },
        handlers={
            "external_source_discovery": noop_job,
            "external_lead_extraction_grading": noop_job,
        },
    )

    started = service.start()

    assert started is True
    assert scheduler.started is True
    assert [job["id"] for job in scheduler.jobs] == ["external_source_discovery", "external_lead_extraction_grading"]
    assert [job["trigger"] for job in scheduler.jobs] == ["interval", "interval"]
    assert [job["seconds"] for job in scheduler.jobs] == [900, 300]
    assert all(job["max_instances"] == 1 for job in scheduler.jobs)
    assert all(job["coalesce"] is True for job in scheduler.jobs)
    logs = logger.joined()
    assert "注册 External agent job：external_source_discovery interval=900s initial_delay=0s" in logs
    assert "注册 External agent job：external_lead_extraction_grading interval=300s initial_delay=0s" in logs


@pytest.mark.asyncio
async def test_external_agent_scheduler_uses_lock_before_running_handler() -> None:
    calls: list[str] = []

    class RecordingLockManager:
        async def run_with_lock(self, job_id, callback):
            calls.append(f"lock:{job_id}")
            return await callback()

    async def source_job():
        calls.append("source_job")
        return {"status": "ok"}

    scheduler = FakeScheduler()
    service = ExternalAgentSchedulerService(
        scheduler=scheduler,
        lock_manager=RecordingLockManager(),
        enabled=True,
        job_configs={
            "external_source_discovery": {"enabled": True, "interval_seconds": 900},
            "external_lead_extraction_grading": {"enabled": False, "interval_seconds": 300},
        },
        handlers={"external_source_discovery": source_job},
    )
    service.start()

    result = await scheduler.jobs[0]["func"]()

    assert result == {"status": "ok"}
    assert calls == ["lock:external_source_discovery", "source_job"]


def test_external_source_discovery_payload_is_shadow_safe() -> None:
    payload = build_external_source_discovery_input(request_id="run-1")

    assert payload["discovery_run_id"] == "run-1"
    assert payload["trigger_source"] == "scheduler_external_source_discovery"
    assert payload["market"] == "Russia"
    assert payload["requested_actions"] == []
    assert payload["seed_urls"] == ["https://scheduler-shadow-source.example/dealers"]
    assert payload["search_results"] == []
    assert "不得登录" in payload["channel_strategy"]["risk_policy"]


def test_external_lead_extraction_grading_payload_is_shadow_safe_and_valid() -> None:
    payload = build_external_lead_extraction_grading_input(request_id="run-2")

    assert payload["combined_run_id"] == "run-2"
    assert payload["extraction_run_id"] == "run-2"
    assert payload["grading_run_id"] == "run-2"
    assert payload["trigger_source"] == "scheduler_external_lead_extraction_grading"
    assert payload["source_url"].startswith("https://")
    assert "Contact:" in payload["source_content"]
    assert payload["risk_flags"] == []
    assert payload["expected_contacts"]["email"] == "sales@scheduler-shadow.example"


@pytest.mark.asyncio
async def test_scheduled_external_source_discovery_calls_apps_agents_http_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict] = []
    consumed_responses: list[dict] = []

    async def fake_run_agent(self, agent_endpoint, **kwargs):
        calls.append({"agent_endpoint": agent_endpoint, **kwargs})
        return {
            "status": "succeeded",
            "agent_service_run_id": "agent-run-1",
            "request_id": kwargs["request_id"],
            "agent_type": "source_discovery",
            "agent_mode": kwargs["agent_mode"],
            "audit": {"writes_core_tables": False},
        }

    async def fake_consume(response):
        consumed_responses.append(response)
        return {"status": "succeeded", "created_count": 1, "updated_count": 0}

    monkeypatch.setattr("app.services.external_agent_scheduler_bootstrap.HttpAgentRuntime.run_agent", fake_run_agent)
    monkeypatch.setattr("app.services.external_agent_scheduler_bootstrap.consume_external_source_discovery_response", fake_consume)

    result = await run_scheduled_external_source_discovery()

    assert result["status"] == "succeeded"
    assert result["writes_core_tables"] is False
    assert result["consumption"] == {"status": "succeeded", "created_count": 1, "updated_count": 0}
    assert consumed_responses[0]["agent_service_run_id"] == "agent-run-1"
    assert calls[0]["agent_endpoint"] == "source-discovery"
    assert calls[0]["trigger_source"] == "scheduler"
    assert calls[0]["agent_mode"] == "shadow"
    assert calls[0]["input_payload"]["discovery_run_id"] == calls[0]["request_id"]
    assert calls[0]["input_payload"]["trigger_source"] == "scheduler_external_source_discovery"


@pytest.mark.asyncio
async def test_scheduled_external_lead_extraction_grading_calls_apps_agents_http_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict] = []
    consumed_responses: list[dict] = []

    async def fake_run_agent(self, agent_endpoint, **kwargs):
        calls.append({"agent_endpoint": agent_endpoint, **kwargs})
        return {
            "status": "succeeded",
            "agent_service_run_id": "agent-run-2",
            "request_id": kwargs["request_id"],
            "agent_type": "lead_extraction_grading",
            "agent_mode": kwargs["agent_mode"],
            "audit": {"writes_core_tables": False},
        }

    async def fake_consume(response):
        consumed_responses.append(response)
        return {"status": "succeeded", "created_count": 1, "updated_count": 0}

    monkeypatch.setattr("app.services.external_agent_scheduler_bootstrap.HttpAgentRuntime.run_agent", fake_run_agent)
    monkeypatch.setattr("app.services.external_agent_scheduler_bootstrap.consume_external_lead_extraction_grading_response", fake_consume)

    result = await run_scheduled_external_lead_extraction_grading()

    assert result["status"] == "succeeded"
    assert result["writes_core_tables"] is False
    assert result["consumption"] == {"status": "succeeded", "created_count": 1, "updated_count": 0}
    assert consumed_responses[0]["agent_service_run_id"] == "agent-run-2"
    assert calls[0]["agent_endpoint"] == "lead-extraction-grading"
    assert calls[0]["trigger_source"] == "scheduler"
    assert calls[0]["agent_mode"] == "shadow"
    assert calls[0]["input_payload"]["combined_run_id"] == calls[0]["request_id"]
    assert calls[0]["input_payload"]["trigger_source"] == "scheduler_external_lead_extraction_grading"
