import pytest

from app.agents.scheduler_payloads import (
    build_external_deep_enrichment_batch_input,
    build_external_lead_cleanup_input,
    build_external_lead_extraction_grading_batch_input,
    build_external_lead_extraction_grading_input,
    build_external_source_discovery_input,
)
from app.services.external_agent_scheduler import ExternalAgentSchedulerService
from app.services.external_agent_scheduler_bootstrap import (
    prepare_external_deep_enrichment_input,
    prepare_external_lead_cleanup_input,
    run_scheduled_external_deep_enrichment,
    run_scheduled_external_lead_cleanup,
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


class EmptyScalarResult:
    def __init__(self, statement_log: list[str], statement) -> None:
        self.statement_log = statement_log
        self.statement = statement

    def all(self):
        self.statement_log.append(str(self.statement))
        return []


class RecordingSyncSession:
    def __init__(self, statement_log: list[str]) -> None:
        self.statement_log = statement_log

    def scalars(self, statement):
        return EmptyScalarResult(self.statement_log, statement)


class RecordingAsyncSessionLocal:
    def __init__(self, statement_log: list[str]) -> None:
        self.statement_log = statement_log

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    async def run_sync(self, callback):
        return callback(RecordingSyncSession(self.statement_log))


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
            "external_deep_enrichment": noop_job,
            "external_lead_cleanup": noop_job,
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
            "external_deep_enrichment": {"enabled": True, "interval_seconds": 600},
            "external_lead_cleanup": {"enabled": True, "interval_seconds": 900},
        },
        handlers={
            "external_source_discovery": noop_job,
            "external_lead_extraction_grading": noop_job,
            "external_deep_enrichment": noop_job,
            "external_lead_cleanup": noop_job,
        },
    )

    started = service.start()

    assert started is True
    assert scheduler.started is True
    assert [job["id"] for job in scheduler.jobs] == [
        "external_source_discovery",
        "external_lead_extraction_grading",
        "external_deep_enrichment",
        "external_lead_cleanup",
    ]
    assert [job["trigger"] for job in scheduler.jobs] == ["interval", "interval", "interval", "interval"]
    assert [job["seconds"] for job in scheduler.jobs] == [900, 300, 600, 900]
    assert all(job["max_instances"] == 1 for job in scheduler.jobs)
    assert all(job["coalesce"] is True for job in scheduler.jobs)
    logs = logger.joined()
    assert "注册 External agent job：external_source_discovery interval=900s initial_delay=0s" in logs
    assert "注册 External agent job：external_lead_extraction_grading interval=300s initial_delay=0s" in logs
    assert "注册 External agent job：external_deep_enrichment interval=600s initial_delay=0s" in logs
    assert "注册 External agent job：external_lead_cleanup interval=900s initial_delay=0s" in logs


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


def test_external_source_discovery_payload_uses_real_sources_without_shadow_examples() -> None:
    payload = build_external_source_discovery_input(
        request_id="run-1",
        market="Russia",
        channel_strategy={
            "keywords": ["автодилер"],
            "target_segments": ["official dealer"],
            "risk_policy": "只允许公开来源发现；不得登录、私信、绕过反爬。",
            "source": "channel_plans",
        },
        seed_urls=["https://www.google.com/search?q=автодилер+Moscow+Russia"],
        search_results=[
            {
                "url": "https://www.google.com/search?q=автодилер+Moscow+Russia",
                "title": "Russia official dealer plan",
                "snippet": "来自真实渠道计划的公开发现入口。",
                "source_type": "official_website",
            }
        ],
    )

    assert payload["discovery_run_id"] == "run-1"
    assert payload["trigger_source"] == "scheduler_external_source_discovery"
    assert payload["market"] == "Russia"
    assert payload["requested_actions"] == []
    assert payload["seed_urls"] == ["https://www.google.com/search?q=автодилер+Moscow+Russia"]
    assert payload["search_results"][0]["source_type"] == "official_website"
    assert "scheduler-shadow-source.example" not in payload["seed_urls"][0]
    assert "不得登录" in payload["channel_strategy"]["risk_policy"]


def test_external_lead_extraction_grading_payload_uses_real_candidate_without_shadow_examples() -> None:
    payload = build_external_lead_extraction_grading_input(
        request_id="run-2",
        source_candidate_id="candidate-1",
        candidate_url_id="candidate-url-1",
        source_url="https://real-dealer.example/contact",
        source_content="Real Dealer exports used cars. Contact: sales@real-dealer.example",
        risk_flags=[],
        expected_contacts={"email": "sales@real-dealer.example"},
    )

    assert payload["combined_run_id"] == "run-2"
    assert payload["extraction_run_id"] == "run-2"
    assert payload["grading_run_id"] == "run-2"
    assert payload["trigger_source"] == "scheduler_external_lead_extraction_grading"
    assert payload["source_candidate_id"] == "candidate-1"
    assert payload["candidate_url_id"] == "candidate-url-1"
    assert payload["source_url"] == "https://real-dealer.example/contact"
    assert "Contact:" in payload["source_content"]
    assert "scheduler-shadow-input.local" not in payload["source_url"]
    assert payload["risk_flags"] == []
    assert payload["expected_contacts"]["email"] == "sales@real-dealer.example"


def test_external_deep_enrichment_batch_payload_uses_real_leads() -> None:
    payload = build_external_deep_enrichment_batch_input(
        request_id="deep-run-1",
        leads=[
            {
                "request_id": "deep-item-1",
                "staging_lead_id": "lead-1",
                "lead_snapshot": {"customer_name": "Real Dealer", "contacts_json": []},
                "missing_fields": ["contacts_json"],
            }
        ],
    )

    assert payload["agent_run_id"] == "deep-run-1"
    assert payload["trigger_source"] == "scheduler_external_deep_enrichment"
    assert payload["leads"][0]["staging_lead_id"] == "lead-1"
    assert payload["leads"][0]["missing_fields"] == ["contacts_json"]
    assert "scheduler-shadow" not in str(payload)


def test_external_lead_cleanup_payload_uses_watch_invalid_batch() -> None:
    payload = build_external_lead_cleanup_input(
        request_id="cleanup-run-1",
        leads=[
            {
                "staging_lead_id": "lead-watch",
                "customer_name": "Watch Dealer",
                "recommended_grade": "Watch",
                "contacts_json": [{"type": "email", "value": "watch@example.com"}],
            },
            {
                "staging_lead_id": "lead-invalid",
                "customer_name": "Invalid Dealer",
                "recommended_grade": "Invalid",
                "contacts_json": [],
            },
        ],
    )

    assert payload["cleanup_run_id"] == "cleanup-run-1"
    assert payload["trigger_source"] == "scheduler_external_lead_cleanup"
    assert [item["recommended_grade"] for item in payload["leads"]] == ["Watch", "Invalid"]
    assert "scheduler-shadow" not in str(payload)


@pytest.mark.asyncio
async def test_prepare_external_deep_enrichment_excludes_already_promoted_leads(monkeypatch: pytest.MonkeyPatch) -> None:
    statements: list[str] = []

    monkeypatch.setattr(
        "app.services.external_agent_scheduler_bootstrap.AsyncSessionLocal",
        lambda: RecordingAsyncSessionLocal(statements),
    )

    result = await prepare_external_deep_enrichment_input(request_id="deep-run")

    assert result["status"] == "skipped"
    assert "staging_leads.review_status NOT IN" in statements[0]
    assert "staging_leads.queue_status NOT IN" in statements[0]
    assert "NOT (EXISTS" in statements[0]
    assert "review_logs.action" in statements[0]


@pytest.mark.asyncio
async def test_prepare_external_lead_cleanup_excludes_hidden_invalid_leads(monkeypatch: pytest.MonkeyPatch) -> None:
    statements: list[str] = []

    monkeypatch.setattr(
        "app.services.external_agent_scheduler_bootstrap.AsyncSessionLocal",
        lambda: RecordingAsyncSessionLocal(statements),
    )

    result = await prepare_external_lead_cleanup_input(request_id="cleanup-run")

    assert result["status"] == "skipped"
    assert "staging_leads.review_status NOT IN" in statements[0]
    assert "NOT (EXISTS" in statements[0]
    assert "review_logs.action" in statements[0]


@pytest.mark.asyncio
async def test_scheduled_external_source_discovery_calls_apps_agents_http_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict] = []
    consumed_responses: list[dict] = []

    async def fake_prepare(request_id):
        return {
            "status": "prepared",
            "channel_plan_count": 1,
            "input_payload": build_external_source_discovery_input(
                request_id=request_id,
                market="Russia",
                channel_strategy={
                    "keywords": ["автодилер"],
                    "target_segments": ["official dealer"],
                    "risk_policy": "只允许公开来源发现；不得登录、私信、绕过反爬。",
                    "source": "channel_plans",
                    "channel_plan_ids": ["plan-1"],
                },
                seed_urls=["https://www.google.com/search?q=автодилер+Moscow+Russia"],
                search_results=[
                    {
                        "url": "https://www.google.com/search?q=автодилер+Moscow+Russia",
                        "title": "Russia official dealer plan",
                        "snippet": "来自真实渠道计划的公开发现入口。",
                        "source_type": "official_website",
                    }
                ],
            ),
        }

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

    monkeypatch.setattr("app.services.external_agent_scheduler_bootstrap.prepare_external_source_discovery_input", fake_prepare)
    monkeypatch.setattr("app.services.external_agent_scheduler_bootstrap.HttpAgentRuntime.run_agent", fake_run_agent)
    monkeypatch.setattr("app.services.external_agent_scheduler_bootstrap.consume_external_source_discovery_response", fake_consume)

    result = await run_scheduled_external_source_discovery()

    assert result["status"] == "succeeded"
    assert result["writes_core_tables"] is False
    assert result["consumption"] == {"status": "succeeded", "created_count": 1, "updated_count": 0}
    assert consumed_responses[0]["agent_service_run_id"] == "agent-run-1"
    assert calls[0]["agent_endpoint"] == "source-discovery"
    assert calls[0]["trigger_source"] == "scheduler"
    assert calls[0]["agent_mode"] == "active"
    assert calls[0]["input_payload"]["discovery_run_id"] == calls[0]["request_id"]
    assert calls[0]["input_payload"]["trigger_source"] == "scheduler_external_source_discovery"
    assert calls[0]["input_payload"]["channel_strategy"]["source"] == "channel_plans"
    assert calls[0]["input_payload"]["seed_urls"] == ["https://www.google.com/search?q=автодилер+Moscow+Russia"]
    assert "scheduler-shadow-source.example" not in calls[0]["input_payload"]["seed_urls"][0]


@pytest.mark.asyncio
async def test_scheduled_external_source_discovery_calls_apps_agents_with_default_strategy_without_channel_plans(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict] = []
    consumed_responses: list[dict] = []

    async def fake_prepare(request_id):
        return {
            "status": "prepared",
            "channel_plan_count": 0,
            "input_payload": build_external_source_discovery_input(
                request_id=request_id,
                market="Russia",
                channel_strategy={
                    "keywords": ["автодилер", "автосалон"],
                    "target_segments": ["dealer directories"],
                    "risk_policy": "只允许公开来源发现；不得登录、私信、绕过验证码或绕过反爬。",
                    "source": "default_source_discovery_agent",
                    "channel_plan_ids": [],
                },
                seed_urls=[],
                search_results=[],
            ),
        }

    async def fake_run_agent(self, agent_endpoint, **kwargs):
        calls.append({"agent_endpoint": agent_endpoint, **kwargs})
        return {
            "status": "succeeded",
            "agent_service_run_id": "agent-run-default",
            "request_id": kwargs["request_id"],
            "agent_type": "source_discovery",
            "agent_mode": kwargs["agent_mode"],
            "audit": {"writes_core_tables": False},
            "output": {
                "schema_version": "phase4.agent.source_discovery.v1",
                "candidates": [],
                "blocked_items": [],
                "audit": {"writes_core_tables": False},
            },
        }

    async def fake_consume(response):
        consumed_responses.append(response)
        return {"status": "succeeded", "created_count": 0, "updated_count": 0}

    monkeypatch.setattr("app.services.external_agent_scheduler_bootstrap.prepare_external_source_discovery_input", fake_prepare)
    monkeypatch.setattr("app.services.external_agent_scheduler_bootstrap.HttpAgentRuntime.run_agent", fake_run_agent)
    monkeypatch.setattr("app.services.external_agent_scheduler_bootstrap.consume_external_source_discovery_response", fake_consume)

    result = await run_scheduled_external_source_discovery()

    assert result["status"] == "succeeded"
    assert result["channel_plan_count"] == 0
    assert consumed_responses[0]["agent_service_run_id"] == "agent-run-default"
    assert calls[0]["agent_endpoint"] == "source-discovery"
    assert calls[0]["agent_mode"] == "active"
    assert calls[0]["input_payload"]["channel_strategy"]["source"] == "default_source_discovery_agent"
    assert calls[0]["input_payload"]["seed_urls"] == []


@pytest.mark.asyncio
async def test_scheduled_external_lead_extraction_grading_calls_apps_agents_http_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict] = []
    consumed_responses: list[dict] = []
    finalized: list[dict] = []

    async def fake_prepare(request_id):
        item_1_payload = build_external_lead_extraction_grading_input(
            request_id=f"{request_id}-1",
            source_candidate_id="candidate-1",
            candidate_url_id="candidate-url-1",
            source_url="https://real-dealer.example/contact",
            source_content="Real Dealer exports used cars. Contact: sales@real-dealer.example",
            risk_flags=[],
            expected_contacts={"email": "sales@real-dealer.example"},
        )
        item_2_payload = build_external_lead_extraction_grading_input(
            request_id=f"{request_id}-2",
            source_candidate_id="candidate-2",
            candidate_url_id="candidate-url-2",
            source_url="https://second-dealer.example/contact",
            source_content="Second Dealer imports vehicles. Contact: sales@second-dealer.example",
            risk_flags=[],
            expected_contacts={"email": "sales@second-dealer.example"},
        )
        return {
            "status": "prepared",
            "selected_count": 2,
            "prepared_count": 2,
            "agent_task_run_id": "task-run-1",
            "source_candidate_id": "candidate-1",
            "input_payload": build_external_lead_extraction_grading_batch_input(
                request_id=request_id,
                sources=[
                    {
                        "request_id": f"{request_id}-1",
                        "source_candidate_id": "candidate-1",
                        "candidate_url_id": "candidate-url-1",
                        "source_url": "https://real-dealer.example/contact",
                        "source_content": "Real Dealer exports used cars. Contact: sales@real-dealer.example",
                        "risk_flags": [],
                        "expected_contacts": {"email": "sales@real-dealer.example"},
                    },
                    {
                        "request_id": f"{request_id}-2",
                        "source_candidate_id": "candidate-2",
                        "candidate_url_id": "candidate-url-2",
                        "source_url": "https://second-dealer.example/contact",
                        "source_content": "Second Dealer imports vehicles. Contact: sales@second-dealer.example",
                        "risk_flags": [],
                        "expected_contacts": {"email": "sales@second-dealer.example"},
                    },
                ],
            ),
            "items": [
                {
                    "request_id": f"{request_id}-1",
                    "source_candidate_id": "candidate-1",
                    "source_url": "https://real-dealer.example/contact",
                    "input_payload": item_1_payload,
                },
                {
                    "request_id": f"{request_id}-2",
                    "source_candidate_id": "candidate-2",
                    "source_url": "https://second-dealer.example/contact",
                    "input_payload": item_2_payload,
                },
            ],
            "preparation_failed_items": [],
        }

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
        return {
            "status": "succeeded",
            "created_count": 2,
            "updated_count": 0,
            "processed_items": [
                {
                    "source_candidate_id": "candidate-1",
                    "source_url": "https://real-dealer.example/contact",
                    "status": "succeeded",
                },
                {
                    "source_candidate_id": "candidate-2",
                    "source_url": "https://second-dealer.example/contact",
                    "status": "succeeded",
                },
            ],
        }

    async def fake_finalize_batch(**kwargs):
        finalized.append(kwargs)
        return {
            "status": "succeeded",
            "succeeded_count": 2,
            "failed_count": 0,
            "created_count": 2,
            "updated_count": 0,
        }

    monkeypatch.setattr("app.services.external_agent_scheduler_bootstrap.prepare_external_lead_extraction_grading_input", fake_prepare)
    monkeypatch.setattr("app.services.external_agent_scheduler_bootstrap.HttpAgentRuntime.run_agent", fake_run_agent)
    monkeypatch.setattr("app.services.external_agent_scheduler_bootstrap.consume_external_lead_extraction_grading_response", fake_consume)
    monkeypatch.setattr("app.services.external_agent_scheduler_bootstrap.finalize_external_lead_extraction_grading_batch", fake_finalize_batch)

    result = await run_scheduled_external_lead_extraction_grading()

    assert result["status"] == "succeeded"
    assert result["writes_core_tables"] is False
    assert result["selected_count"] == 2
    assert result["prepared_count"] == 2
    assert result["processed_count"] == 2
    assert result["created_count"] == 2
    assert len(consumed_responses) == 1
    assert consumed_responses[0]["agent_service_run_id"] == "agent-run-2"
    assert len(calls) == 1
    assert calls[0]["agent_endpoint"] == "lead-extraction-grading"
    assert calls[0]["trigger_source"] == "scheduler"
    assert calls[0]["agent_mode"] == "active"
    assert calls[0]["agent_task_run_id"] == "task-run-1"
    assert calls[0]["input_payload"]["combined_run_id"] == calls[0]["request_id"]
    assert calls[0]["input_payload"]["trigger_source"] == "scheduler_external_lead_extraction_grading"
    assert calls[0]["input_payload"]["source_candidate_id"] == "candidate-1"
    assert calls[0]["input_payload"]["source_url"] == "https://real-dealer.example/contact"
    assert [item["source_candidate_id"] for item in calls[0]["input_payload"]["sources"]] == ["candidate-1", "candidate-2"]
    assert [item["source_url"] for item in calls[0]["input_payload"]["sources"]] == [
        "https://real-dealer.example/contact",
        "https://second-dealer.example/contact",
    ]
    assert "scheduler-shadow-input.local" not in calls[0]["input_payload"]["source_url"]
    assert finalized[0]["agent_task_run_id"] == "task-run-1"
    assert len(finalized[0]["processed_items"]) == 2


@pytest.mark.asyncio
async def test_scheduled_external_lead_extraction_grading_skips_without_real_candidate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_prepare(request_id):
        return {"status": "skipped", "reason": "no_eligible_approved_sources", "message": "没有符合准入条件"}

    async def forbidden_run_agent(*_args, **_kwargs):
        raise AssertionError("没有真实候选时不得调用 apps/agents")

    monkeypatch.setattr("app.services.external_agent_scheduler_bootstrap.prepare_external_lead_extraction_grading_input", fake_prepare)
    monkeypatch.setattr("app.services.external_agent_scheduler_bootstrap.HttpAgentRuntime.run_agent", forbidden_run_agent)

    result = await run_scheduled_external_lead_extraction_grading()

    assert result["status"] == "skipped"
    assert result["reason"] == "no_eligible_approved_sources"


@pytest.mark.asyncio
async def test_scheduled_external_deep_enrichment_calls_apps_agents_once_with_batch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict] = []
    consumed: list[dict] = []

    async def fake_prepare(request_id):
        return {
            "status": "prepared",
            "selected_count": 2,
            "input_payload": build_external_deep_enrichment_batch_input(
                request_id=request_id,
                leads=[
                    {
                        "request_id": f"{request_id}-1",
                        "staging_lead_id": "lead-1",
                        "lead_snapshot": {"customer_name": "A Dealer", "contacts_json": []},
                        "missing_fields": ["contacts_json"],
                    },
                    {
                        "request_id": f"{request_id}-2",
                        "staging_lead_id": "lead-2",
                        "lead_snapshot": {"customer_name": "B Dealer", "contacts_json": []},
                        "missing_fields": ["contacts_json"],
                    },
                ],
            ),
        }

    async def fake_run_agent(self, agent_endpoint, **kwargs):
        calls.append({"agent_endpoint": agent_endpoint, **kwargs})
        return {
            "status": "succeeded",
            "agent_service_run_id": "deep-agent-run",
            "request_id": kwargs["request_id"],
            "agent_type": "deep_enrichment",
            "agent_mode": kwargs["agent_mode"],
            "audit": {"writes_core_tables": False},
            "output": {"batch_results": []},
        }

    async def fake_consume(response):
        consumed.append(response)
        return {"status": "succeeded", "processed_count": 2, "promoted_count": 1}

    monkeypatch.setattr("app.services.external_agent_scheduler_bootstrap.prepare_external_deep_enrichment_input", fake_prepare)
    monkeypatch.setattr("app.services.external_agent_scheduler_bootstrap.HttpAgentRuntime.run_agent", fake_run_agent)
    monkeypatch.setattr("app.services.external_agent_scheduler_bootstrap.consume_external_deep_enrichment_response", fake_consume)

    result = await run_scheduled_external_deep_enrichment()

    assert result["status"] == "succeeded"
    assert result["processed_count"] == 2
    assert result["promoted_count"] == 1
    assert len(calls) == 1
    assert calls[0]["agent_endpoint"] == "deep-enrichment"
    assert calls[0]["input_payload"]["trigger_source"] == "scheduler_external_deep_enrichment"
    assert [item["staging_lead_id"] for item in calls[0]["input_payload"]["leads"]] == ["lead-1", "lead-2"]
    assert consumed[0]["agent_service_run_id"] == "deep-agent-run"


@pytest.mark.asyncio
async def test_scheduled_external_lead_cleanup_calls_apps_agents_once_with_watch_invalid_batch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict] = []
    consumed: list[dict] = []

    async def fake_prepare(request_id):
        return {
            "status": "prepared",
            "selected_count": 2,
            "input_payload": build_external_lead_cleanup_input(
                request_id=request_id,
                leads=[
                    {"staging_lead_id": "lead-watch", "recommended_grade": "Watch"},
                    {"staging_lead_id": "lead-invalid", "recommended_grade": "Invalid"},
                ],
            ),
        }

    async def fake_run_agent(self, agent_endpoint, **kwargs):
        calls.append({"agent_endpoint": agent_endpoint, **kwargs})
        return {
            "status": "succeeded",
            "agent_service_run_id": "cleanup-agent-run",
            "request_id": kwargs["request_id"],
            "agent_type": "lead_cleanup",
            "agent_mode": kwargs["agent_mode"],
            "audit": {"writes_core_tables": False},
            "output": {"schema_version": "phase3.agent.lead_cleanup.v1", "suggestions": []},
        }

    async def fake_consume(response):
        consumed.append(response)
        return {"status": "succeeded", "executed_count": 2, "upgraded_count": 1, "hidden_count": 1}

    monkeypatch.setattr("app.services.external_agent_scheduler_bootstrap.prepare_external_lead_cleanup_input", fake_prepare)
    monkeypatch.setattr("app.services.external_agent_scheduler_bootstrap.HttpAgentRuntime.run_agent", fake_run_agent)
    monkeypatch.setattr("app.services.external_agent_scheduler_bootstrap.consume_external_lead_cleanup_response", fake_consume)

    result = await run_scheduled_external_lead_cleanup()

    assert result["status"] == "succeeded"
    assert result["executed_count"] == 2
    assert result["upgraded_count"] == 1
    assert result["hidden_count"] == 1
    assert len(calls) == 1
    assert calls[0]["agent_endpoint"] == "lead-cleanup"
    assert calls[0]["input_payload"]["trigger_source"] == "scheduler_external_lead_cleanup"
    assert [item["staging_lead_id"] for item in calls[0]["input_payload"]["leads"]] == ["lead-watch", "lead-invalid"]
    assert consumed[0]["agent_service_run_id"] == "cleanup-agent-run"
