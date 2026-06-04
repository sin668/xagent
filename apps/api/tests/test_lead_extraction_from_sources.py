import asyncio
from uuid import uuid4

from sqlalchemy import delete, select

from app.db.session import AsyncSessionLocal
from app.models.ai_audit_log import AIAuditLog
from app.models.agent_task_run import AgentTaskRun
from app.models.candidate_url import CandidateUrl
from app.models.collection_task import CollectionTask
from app.models.enums import (
    AITaskType,
    AgentTaskRunStatus,
    AgentTaskType,
    ChannelRiskLevel,
    CustomerGrade,
    LeadSourceCandidateExtractionStatus,
    PageSnapshotReadStatus,
    StagingQueueStatus,
)
from app.models.lead_source_candidate import LeadSourceCandidate
from app.models.page_snapshot import PageSnapshot
from app.models.staging_lead import StagingLead
from app.services.lead_extraction_from_sources import LeadExtractionFromSourcesService
from app.services.lead_source_candidates import LeadSourceCandidateService
from app.services.public_page_read_agent import PublicPageFetchResult, PublicPageReadAgentService


TEST_PREFIX = "p2e5s4"


def extraction_output(source_url: str) -> dict:
    return {
        "schema_version": "poc-ai-output-v1",
        "task_type": "lead_extraction",
        "source": {"source_url": source_url},
        "risk_blocked": False,
        "risk_block_reason": None,
        "lead": {
            "customer_name": "Auto City Moscow",
            "country": "Russia",
            "city": "Moscow",
            "customer_type": "local_dealer_secondary_dealer",
            "activity_signal": "公开页面展示二手车库存和联系方式",
            "scale_signal": "多个车型库存",
            "import_used_relevance": "high",
            "contacts": {
                "emails": ["sales@autocity.example"],
                "phones": [],
                "whatsapp": [],
                "telegram": [],
                "wechat": [],
                "website_forms": [],
            },
            "source_evidence": [
                {
                    "claim": "dealer_identity",
                    "evidence_text": "Used cars and imported SUVs",
                    "source_url": source_url,
                }
            ],
            "missing_fields": [],
        },
        "audit": {
            "model": "test-extraction-model",
            "prompt_version": "lead-extraction-v1",
            "input_saved": True,
            "output_saved": True,
            "executed_at": "2026-06-02T10:00:00+08:00",
        },
    }


def grading_output(source_url: str, *, grade: str = "C") -> dict:
    return {
        "schema_version": "poc-ai-output-v1",
        "task_type": "lead_grading",
        "lead_id": "staging-lead",
        "recommended_grade": grade,
        "recommended_reason": "客户公开展示二手车库存和邮箱，适合人工跟进。",
        "reason_codes": ["has_public_contact", "used_car_signal"],
        "evidence_refs": [
            {
                "claim": "used_car_signal",
                "evidence_text": "Used cars and imported SUVs",
                "source_url": source_url,
            }
        ],
        "missing_fields": ["是否有进口经验"],
        "next_action": "handoff_to_export_sales",
        "suggested_handoff_team": "export_sales",
        "touch_queue_allowed": True,
        "compliance_review_required": False,
        "human_review_required": True,
        "risk_flags": [],
        "audit": {
            "model": "test-grading-model",
            "prompt_version": "lead-grading-v1",
            "input_saved": True,
            "output_saved": True,
            "executed_at": "2026-06-02T10:01:00+08:00",
        },
    }


class FakeLLMClient:
    def __init__(
        self,
        *,
        source_url: str,
        grade: str = "C",
        omit_extraction_evidence: bool = False,
        omit_grading_evidence_refs: bool = False,
        invalid_extraction_schema: bool = False,
        invalid_grading_schema: bool = False,
        unknown_customer_type: bool = False,
        unknown_grading_enums: bool = False,
    ) -> None:
        self.source_url = source_url
        self.grade = grade
        self.omit_extraction_evidence = omit_extraction_evidence
        self.omit_grading_evidence_refs = omit_grading_evidence_refs
        self.invalid_extraction_schema = invalid_extraction_schema
        self.invalid_grading_schema = invalid_grading_schema
        self.unknown_customer_type = unknown_customer_type
        self.unknown_grading_enums = unknown_grading_enums
        self.calls: list[str] = []
        self.user_prompts: list[str] = []
        self.output_schemas: list[dict] = []

    async def generate_json(self, task_type: str, system_prompt: str, user_prompt: str, output_schema: dict) -> object:
        self.calls.append(task_type)
        self.user_prompts.append(user_prompt)
        self.output_schemas.append(output_schema)
        if task_type == "LEAD_EXTRACTION":
            output = extraction_output(self.source_url)
            if self.omit_extraction_evidence:
                output["lead"]["source_evidence"] = []
            if self.invalid_extraction_schema:
                output["schema_version"] = "1.0"
            if self.unknown_customer_type:
                output["lead"]["customer_type"] = "fleet leasing broker"
            return type(
                "Result",
                (),
                {
                    "provider": "fake-provider",
                    "model": "test-extraction-model",
                    "latency_ms": 12,
                    "token_usage": {"total_tokens": 100},
                    "output_json": output,
                    "error": None,
                },
            )()
        if task_type == "LEAD_GRADING":
            output = grading_output(self.source_url, grade=self.grade)
            if self.omit_grading_evidence_refs:
                output["evidence_refs"] = []
            if self.invalid_grading_schema:
                output["schema_version"] = "1.0"
                output["task_type"] = "LEAD_GRADING"
            if self.unknown_grading_enums:
                output["recommended_grade"] = "Interested Dealer"
                output["next_action"] = "call dealer tomorrow"
                output["suggested_handoff_team"] = "sales team"
            return type(
                "Result",
                (),
                {
                    "provider": "fake-provider",
                    "model": "test-grading-model",
                    "latency_ms": 8,
                    "token_usage": {"total_tokens": 50},
                    "output_json": output,
                    "error": None,
                },
            )()
        raise AssertionError(f"Unexpected task type: {task_type}")


class FailingLLMClient:
    async def generate_json(self, task_type: str, system_prompt: str, user_prompt: str, output_schema: dict) -> object:
        return type(
            "Result",
            (),
            {
                "provider": "fake-provider",
                "model": "test-model",
                "latency_ms": 5,
                "token_usage": None,
                "output_json": None,
                "error": {"type": "timeout_error", "message": "LLM timeout"},
            },
        )()


def candidate_payload(suffix: str) -> dict:
    source_url = f"https://{TEST_PREFIX}-{suffix}.example.com/contact"
    return {
        "source_url": source_url,
        "platform": "official_website",
        "channel_name": "dealer_directory",
        "country": "P2E5S4-Testland",
        "city": "P2E5S4-TestCity",
        "risk_level": "Medium",
        "discovery_method": "keyword_search",
        "discovery_query": "автосалон Москва",
        "discovery_reason": "公开来源页面展示车辆经销相关信息。",
        "evidence_note": "公开页面包含 Used cars and imported SUVs、dealer、auto sales 和邮箱 sales@autocity.example。",
        "evidence_links": [source_url],
        "confidence_score": 0.77,
    }


async def cleanup_records() -> None:
    async with AsyncSessionLocal() as async_session:
        await async_session.execute(delete(AIAuditLog).where(AIAuditLog.source_url.like(f"https://{TEST_PREFIX}%")))
        await async_session.execute(delete(StagingLead).where(StagingLead.customer_name == "Auto City Moscow"))
        await async_session.execute(
            delete(PageSnapshot).where(
                PageSnapshot.candidate_url_id.in_(
                    select(CandidateUrl.id).where(CandidateUrl.url.like(f"https://{TEST_PREFIX}%"))
                )
            )
        )
        await async_session.execute(delete(CandidateUrl).where(CandidateUrl.url.like(f"https://{TEST_PREFIX}%")))
        await async_session.execute(delete(CollectionTask).where(CollectionTask.channel_name.like(f"{TEST_PREFIX}%")))
        await async_session.execute(
            delete(LeadSourceCandidate).where(LeadSourceCandidate.normalized_domain.like(f"{TEST_PREFIX}%"))
        )
        await async_session.execute(delete(AgentTaskRun).where(AgentTaskRun.trigger_source.like(f"{TEST_PREFIX}%")))
        await async_session.commit()


async def seed_lead_extraction_task() -> tuple[str, str, str]:
    suffix = uuid4().hex[:10]
    async with AsyncSessionLocal() as async_session:
        def run(sync_session):
            seed_task = AgentTaskRun(
                task_type=AgentTaskType.SOURCE_DISCOVERY,
                status=AgentTaskRunStatus.SUCCEEDED,
                trigger_source=f"{TEST_PREFIX}-seed-{suffix}",
                input_json={"country": "Russia"},
                output_summary_json={"created_count": 1},
            )
            sync_session.add(seed_task)
            sync_session.flush()
            candidate = LeadSourceCandidateService(sync_session).upsert_candidate(
                candidate_payload(suffix),
                created_by_task_run_id=seed_task.id,
                llm_provider="deepseek",
                llm_model="deepseek-chat",
                llm_output_json={"task_type": "SOURCE_DISCOVERY", "candidates": [], "blocked_candidates": []},
            ).candidate
            sync_session.flush()
            selection = LeadExtractionFromSourcesService(sync_session).create_lead_extraction_task_from_sources(
                trigger_source=f"{TEST_PREFIX}-selection-{suffix}",
                limit=1,
                country="P2E5S4-Testland",
                city="P2E5S4-TestCity",
            )
            sync_session.flush()
            return str(selection.task_run.id), str(candidate.id), candidate.source_url

        result = await async_session.run_sync(run)
        await async_session.commit()
        return result


async def fetch_state(task_run_id: str, candidate_id: str) -> dict:
    async with AsyncSessionLocal() as async_session:
        def run(sync_session):
            task = sync_session.get(AgentTaskRun, task_run_id)
            candidate = sync_session.get(LeadSourceCandidate, candidate_id)
            staging = sync_session.scalar(select(StagingLead).where(StagingLead.customer_name == "Auto City Moscow"))
            audits = list(
                sync_session.scalars(
                    select(AIAuditLog).where(AIAuditLog.source_url == candidate.source_url).order_by(AIAuditLog.executed_at)
                ).all()
            )
            return {
                "task": task,
                "candidate": candidate,
                "staging": staging,
                "audits": audits,
            }

        return await async_session.run_sync(run)


async def fetch_latest_snapshot_for_candidate_url(source_url: str) -> dict:
    async with AsyncSessionLocal() as async_session:
        def run(sync_session):
            candidate_url = sync_session.scalar(select(CandidateUrl).where(CandidateUrl.url == source_url))
            snapshot = sync_session.scalar(
                select(PageSnapshot)
                .where(PageSnapshot.candidate_url_id == candidate_url.id)
                .order_by(PageSnapshot.captured_at.desc(), PageSnapshot.id.desc())
            )
            return {
                "read_status": snapshot.read_status.value,
                "text_excerpt": snapshot.text_excerpt or "",
            }

        return await async_session.run_sync(run)


def setup_function():
    asyncio.run(cleanup_records())


def teardown_function():
    asyncio.run(cleanup_records())


def test_run_queued_sources_writes_staging_grading_audit_and_updates_source_status() -> None:
    task_run_id, candidate_id, source_url = asyncio.run(seed_lead_extraction_task())
    fake_llm = FakeLLMClient(source_url=source_url, grade="C")

    async def execute() -> dict:
        async with AsyncSessionLocal() as async_session:
            def run(sync_session):
                service = LeadExtractionFromSourcesService(sync_session, llm_client=fake_llm)
                result = service.run_queued_lead_extraction_task(task_run_id)
                sync_session.commit()
                return result

            return await async_session.run_sync(run)

    result = asyncio.run(execute())
    state = asyncio.run(fetch_state(task_run_id, candidate_id))

    assert result["processed_count"] == 1
    assert result["succeeded_count"] == 1
    assert fake_llm.calls == ["LEAD_EXTRACTION", "LEAD_GRADING"]

    assert state["task"].status == AgentTaskRunStatus.SUCCEEDED
    assert state["task"].output_summary_json["succeeded_count"] == 1
    assert state["candidate"].extraction_status == LeadSourceCandidateExtractionStatus.SUCCEEDED
    assert state["candidate"].last_extracted_at is not None

    staging = state["staging"]
    assert staging is not None
    assert staging.recommended_grade == CustomerGrade.C
    assert staging.requires_compliance_review is True
    assert staging.queue_status == StagingQueueStatus.ELIGIBLE

    audit_types = [audit.task_type for audit in state["audits"]]
    assert AITaskType.LEAD_EXTRACTION in audit_types
    assert AITaskType.LEAD_GRADING in audit_types
    assert all(audit.prompt_version for audit in state["audits"])
    assert all(audit.model_name for audit in state["audits"])
    assert all(str(task_run_id) in str(audit.input_payload) for audit in state["audits"])


def test_llm_failure_marks_source_retry_and_task_retry_pending() -> None:
    task_run_id, candidate_id, _source_url = asyncio.run(seed_lead_extraction_task())

    async def execute() -> None:
        async with AsyncSessionLocal() as async_session:
            def run(sync_session):
                service = LeadExtractionFromSourcesService(sync_session, llm_client=FailingLLMClient())
                result = service.run_queued_lead_extraction_task(task_run_id)
                sync_session.commit()
                return result

            return await async_session.run_sync(run)

    result = asyncio.run(execute())
    state = asyncio.run(fetch_state(task_run_id, candidate_id))

    assert result["failed_count"] == 1
    assert state["task"].status == AgentTaskRunStatus.RETRY_PENDING
    assert state["candidate"].extraction_status == LeadSourceCandidateExtractionStatus.RETRY
    assert state["candidate"].last_extracted_at is None
    assert state["staging"] is None


def test_retry_pending_task_requeues_retry_source_before_execution() -> None:
    task_run_id, candidate_id, source_url = asyncio.run(seed_lead_extraction_task())

    async def fail_once() -> None:
        async with AsyncSessionLocal() as async_session:
            def run(sync_session):
                service = LeadExtractionFromSourcesService(sync_session, llm_client=FailingLLMClient())
                result = service.run_queued_lead_extraction_task(task_run_id)
                sync_session.commit()
                return result

            return await async_session.run_sync(run)

    asyncio.run(fail_once())
    retry_state = asyncio.run(fetch_state(task_run_id, candidate_id))
    assert retry_state["task"].status == AgentTaskRunStatus.RETRY_PENDING
    assert retry_state["candidate"].extraction_status == LeadSourceCandidateExtractionStatus.RETRY

    fake_llm = FakeLLMClient(source_url=source_url, grade="C")

    async def retry_execute() -> dict:
        async with AsyncSessionLocal() as async_session:
            def run(sync_session):
                service = LeadExtractionFromSourcesService(sync_session, llm_client=fake_llm)
                result = service.run_queued_lead_extraction_task(task_run_id)
                sync_session.commit()
                return result

            return await async_session.run_sync(run)

    result = asyncio.run(retry_execute())
    final_state = asyncio.run(fetch_state(task_run_id, candidate_id))

    assert result["succeeded_count"] == 1
    assert final_state["task"].status == AgentTaskRunStatus.SUCCEEDED
    assert final_state["candidate"].extraction_status == LeadSourceCandidateExtractionStatus.SUCCEEDED


def test_extraction_adds_audited_fallback_evidence_when_llm_omits_evidence() -> None:
    task_run_id, candidate_id, source_url = asyncio.run(seed_lead_extraction_task())
    fake_llm = FakeLLMClient(source_url=source_url, grade="C", omit_extraction_evidence=True)

    async def execute() -> dict:
        async with AsyncSessionLocal() as async_session:
            def run(sync_session):
                service = LeadExtractionFromSourcesService(sync_session, llm_client=fake_llm)
                result = service.run_queued_lead_extraction_task(task_run_id)
                sync_session.commit()
                return result

            return await async_session.run_sync(run)

    result = asyncio.run(execute())
    state = asyncio.run(fetch_state(task_run_id, candidate_id))

    assert result["succeeded_count"] == 1
    assert state["task"].status == AgentTaskRunStatus.SUCCEEDED
    assert state["candidate"].extraction_status == LeadSourceCandidateExtractionStatus.SUCCEEDED

    staging = state["staging"]
    assert staging is not None
    assert "source_candidate_public_text" in staging.source_evidence
    assert "sales@autocity.example" in staging.source_evidence

    extraction_audits = [audit for audit in state["audits"] if audit.task_type == AITaskType.LEAD_EXTRACTION]
    assert extraction_audits
    output_json = extraction_audits[-1].output_json
    assert output_json["audit"]["source_evidence_fallback_applied"] is True
    assert output_json["audit"]["source_evidence_fallback_reason"] == "llm_missing_source_evidence"


def test_grading_adds_audited_fallback_evidence_refs_when_llm_omits_refs() -> None:
    task_run_id, candidate_id, source_url = asyncio.run(seed_lead_extraction_task())
    fake_llm = FakeLLMClient(source_url=source_url, grade="C", omit_grading_evidence_refs=True)

    async def execute() -> dict:
        async with AsyncSessionLocal() as async_session:
            def run(sync_session):
                service = LeadExtractionFromSourcesService(sync_session, llm_client=fake_llm)
                result = service.run_queued_lead_extraction_task(task_run_id)
                sync_session.commit()
                return result

            return await async_session.run_sync(run)

    result = asyncio.run(execute())
    state = asyncio.run(fetch_state(task_run_id, candidate_id))

    assert result["succeeded_count"] == 1
    assert state["task"].status == AgentTaskRunStatus.SUCCEEDED
    assert state["candidate"].extraction_status == LeadSourceCandidateExtractionStatus.SUCCEEDED

    grading_audits = [audit for audit in state["audits"] if audit.task_type == AITaskType.LEAD_GRADING]
    assert grading_audits
    llm_output = grading_audits[-1].output_json["llm_output"]
    assert llm_output["audit"]["evidence_refs_fallback_applied"] is True
    assert llm_output["audit"]["evidence_refs_fallback_reason"] == "llm_missing_evidence_refs"
    assert llm_output["evidence_refs"][0]["source_url"] == source_url
    assert "Used cars and imported SUVs" in llm_output["evidence_refs"][0]["evidence_text"]


def test_retry_pending_task_skips_already_succeeded_sources_and_retries_remaining_sources() -> None:
    first_task_run_id, first_candidate_id, source_url = asyncio.run(seed_lead_extraction_task())
    second_task_run_id, second_candidate_id, _second_source_url = asyncio.run(seed_lead_extraction_task())

    async def prepare_mixed_retry_task() -> str:
        async with AsyncSessionLocal() as async_session:
            def run(sync_session):
                first_task = sync_session.get(AgentTaskRun, first_task_run_id)
                first_candidate = sync_session.get(LeadSourceCandidate, first_candidate_id)
                second_candidate = sync_session.get(LeadSourceCandidate, second_candidate_id)

                first_candidate.extraction_status = LeadSourceCandidateExtractionStatus.SUCCEEDED
                second_candidate.extraction_status = LeadSourceCandidateExtractionStatus.RETRY
                first_task.status = AgentTaskRunStatus.RETRY_PENDING
                first_task.input_json = {
                    **(first_task.input_json or {}),
                    "candidate_ids": [first_candidate_id, second_candidate_id],
                }
                sync_session.commit()
                return str(first_task.id)

            return await async_session.run_sync(run)

    task_run_id = asyncio.run(prepare_mixed_retry_task())
    fake_llm = FakeLLMClient(source_url=source_url, grade="C")

    async def execute() -> dict:
        async with AsyncSessionLocal() as async_session:
            def run(sync_session):
                service = LeadExtractionFromSourcesService(sync_session, llm_client=fake_llm)
                result = service.run_queued_lead_extraction_task(task_run_id)
                sync_session.commit()
                return result

            return await async_session.run_sync(run)

    result = asyncio.run(execute())
    state = asyncio.run(fetch_state(task_run_id, second_candidate_id))

    assert result["succeeded_count"] == 1
    assert result["failed_count"] == 0
    assert result["skipped_count"] == 1
    assert result["processed_candidates"][0]["status"] == "skipped"
    assert result["processed_candidates"][0]["reason"] == "source_already_succeeded"
    assert result["processed_candidates"][1]["status"] == "succeeded"
    assert state["task"].status == AgentTaskRunStatus.SUCCEEDED
    assert state["candidate"].extraction_status == LeadSourceCandidateExtractionStatus.SUCCEEDED


def test_lead_extraction_reads_public_page_text_before_llm_extraction(monkeypatch) -> None:
    task_run_id, candidate_id, source_url = asyncio.run(seed_lead_extraction_task())
    fake_llm = FakeLLMClient(source_url=source_url, grade="C")
    html = """
    <html><head><title>Auto City Moscow</title></head><body>
      <h1>Auto City Moscow</h1>
      <p>Used cars and imported SUVs</p>
      <p>Email: sales@autocity.example</p>
    </body></html>
    """

    def fake_fetch(url: str) -> PublicPageFetchResult:
        return PublicPageFetchResult(url=url, html=html, http_status=200)

    monkeypatch.setattr(PublicPageReadAgentService, "fetch_public_page", staticmethod(fake_fetch))

    async def execute() -> dict:
        async with AsyncSessionLocal() as async_session:
            def run(sync_session):
                service = LeadExtractionFromSourcesService(sync_session, llm_client=fake_llm)
                result = service.run_queued_lead_extraction_task(task_run_id)
                sync_session.commit()
                return result

            return await async_session.run_sync(run)

    result = asyncio.run(execute())
    state = asyncio.run(fetch_state(task_run_id, candidate_id))

    assert result["succeeded_count"] == 1
    extraction_prompt = fake_llm.user_prompts[0]
    assert "Auto City Moscow" in extraction_prompt
    assert "sales@autocity.example" in extraction_prompt
    assert "公开页面读取成功" not in extraction_prompt

    latest_snapshot = asyncio.run(fetch_latest_snapshot_for_candidate_url(source_url))
    assert latest_snapshot["read_status"] == PageSnapshotReadStatus.SUCCESS.value
    assert "sales@autocity.example" in latest_snapshot["text_excerpt"]
    assert state["candidate"].extraction_status == LeadSourceCandidateExtractionStatus.SUCCEEDED


def test_lead_extraction_agent_passes_strict_output_schemas_to_llm(monkeypatch) -> None:
    task_run_id, _candidate_id, source_url = asyncio.run(seed_lead_extraction_task())
    fake_llm = FakeLLMClient(source_url=source_url, grade="C")
    html = """
    <html><body>
      <h1>Auto City Moscow</h1>
      <p>Used cars and imported SUVs</p>
      <p>Email: sales@autocity.example</p>
    </body></html>
    """

    monkeypatch.setattr(
        PublicPageReadAgentService,
        "fetch_public_page",
        staticmethod(lambda url: PublicPageFetchResult(url=url, html=html, http_status=200)),
    )

    async def execute() -> None:
        async with AsyncSessionLocal() as async_session:
            def run(sync_session):
                LeadExtractionFromSourcesService(sync_session, llm_client=fake_llm).run_queued_lead_extraction_task(task_run_id)
                sync_session.commit()

            await async_session.run_sync(run)

    asyncio.run(execute())

    extraction_schema, grading_schema = fake_llm.output_schemas
    assert extraction_schema["required"] == ["schema_version", "task_type", "source", "risk_blocked", "lead", "audit"]
    assert "customer_name" in extraction_schema["properties"]["lead"]["properties"]
    assert "contacts" in extraction_schema["properties"]["lead"]["properties"]
    assert grading_schema["required"] == [
        "schema_version",
        "task_type",
        "recommended_grade",
        "recommended_reason",
        "evidence_refs",
        "next_action",
        "suggested_handoff_team",
        "touch_queue_allowed",
        "compliance_review_required",
        "audit",
    ]


def test_source_selection_recovers_orphaned_queued_sources_when_no_task_is_running() -> None:
    task_run_id, candidate_id, _source_url = asyncio.run(seed_lead_extraction_task())

    async def prepare_orphaned_queued_source() -> None:
        async with AsyncSessionLocal() as async_session:
            def run(sync_session):
                task = sync_session.get(AgentTaskRun, task_run_id)
                candidate = sync_session.get(LeadSourceCandidate, candidate_id)
                task.status = AgentTaskRunStatus.FAILED
                candidate.extraction_status = LeadSourceCandidateExtractionStatus.QUEUED
                sync_session.commit()

            await async_session.run_sync(run)

    asyncio.run(prepare_orphaned_queued_source())

    async def select_again() -> dict:
        async with AsyncSessionLocal() as async_session:
            def run(sync_session):
                selection = LeadExtractionFromSourcesService(sync_session).create_lead_extraction_task_from_sources(
                    trigger_source=f"{TEST_PREFIX}-recover-queued",
                    limit=1,
                    country="P2E5S4-Testland",
                    city="P2E5S4-TestCity",
                )
                sync_session.commit()
                selected = selection.selected_candidates[0]
                return {
                    "task_id": str(selection.task_run.id),
                    "candidate_id": str(selected.id),
                    "extraction_status": selected.extraction_status.value,
                }

            return await async_session.run_sync(run)

    result = asyncio.run(select_again())

    assert result["candidate_id"] == candidate_id
    assert result["extraction_status"] == LeadSourceCandidateExtractionStatus.QUEUED.value


def test_agent_canonicalizes_wrong_extraction_schema_version_and_audits_original_value() -> None:
    task_run_id, candidate_id, source_url = asyncio.run(seed_lead_extraction_task())
    fake_llm = FakeLLMClient(source_url=source_url, invalid_extraction_schema=True)

    async def execute() -> dict:
        async with AsyncSessionLocal() as async_session:
            def run(sync_session):
                service = LeadExtractionFromSourcesService(sync_session, llm_client=fake_llm)
                result = service.run_queued_lead_extraction_task(task_run_id)
                sync_session.commit()
                return result

            return await async_session.run_sync(run)

    result = asyncio.run(execute())
    state = asyncio.run(fetch_state(task_run_id, candidate_id))

    assert result["succeeded_count"] == 1
    assert result["failed_count"] == 0
    assert state["task"].status == AgentTaskRunStatus.SUCCEEDED
    assert state["candidate"].extraction_status == LeadSourceCandidateExtractionStatus.SUCCEEDED
    extraction_audits = [audit for audit in state["audits"] if audit.task_type == AITaskType.LEAD_EXTRACTION]
    assert extraction_audits
    output_json = extraction_audits[-1].output_json
    assert output_json["schema_version"] == "poc-ai-output-v1"
    assert output_json["audit"]["llm_reported_schema_version"] == "1.0"
    assert output_json["audit"]["schema_version_canonicalized"] is True


def test_agent_canonicalizes_wrong_grading_schema_version_and_audits_original_value() -> None:
    task_run_id, candidate_id, source_url = asyncio.run(seed_lead_extraction_task())
    fake_llm = FakeLLMClient(source_url=source_url, grade="C", invalid_grading_schema=True)

    async def execute() -> dict:
        async with AsyncSessionLocal() as async_session:
            def run(sync_session):
                service = LeadExtractionFromSourcesService(sync_session, llm_client=fake_llm)
                result = service.run_queued_lead_extraction_task(task_run_id)
                sync_session.commit()
                return result

            return await async_session.run_sync(run)

    result = asyncio.run(execute())
    state = asyncio.run(fetch_state(task_run_id, candidate_id))

    assert result["succeeded_count"] == 1
    assert result["failed_count"] == 0
    assert state["task"].status == AgentTaskRunStatus.SUCCEEDED
    assert state["candidate"].extraction_status == LeadSourceCandidateExtractionStatus.SUCCEEDED
    grading_audits = [audit for audit in state["audits"] if audit.task_type == AITaskType.LEAD_GRADING]
    assert grading_audits
    output_json = grading_audits[-1].output_json["llm_output"]
    assert output_json["schema_version"] == "poc-ai-output-v1"
    assert output_json["task_type"] == "lead_grading"
    assert output_json["audit"]["llm_reported_schema_version"] == "1.0"
    assert output_json["audit"]["schema_version_canonicalized"] is True
    assert output_json["audit"]["llm_reported_task_type"] == "LEAD_GRADING"
    assert output_json["audit"]["task_type_canonicalized"] is True


def test_agent_relaxes_unknown_llm_enums_when_extracted_lead_has_contact_and_audits_original_values() -> None:
    task_run_id, candidate_id, source_url = asyncio.run(seed_lead_extraction_task())
    fake_llm = FakeLLMClient(
        source_url=source_url,
        unknown_customer_type=True,
        unknown_grading_enums=True,
    )

    async def execute() -> dict:
        async with AsyncSessionLocal() as async_session:
            def run(sync_session):
                service = LeadExtractionFromSourcesService(sync_session, llm_client=fake_llm)
                result = service.run_queued_lead_extraction_task(task_run_id)
                sync_session.commit()
                return result

            return await async_session.run_sync(run)

    result = asyncio.run(execute())
    state = asyncio.run(fetch_state(task_run_id, candidate_id))

    assert result["succeeded_count"] == 1
    assert result["failed_count"] == 0
    assert state["task"].status == AgentTaskRunStatus.SUCCEEDED
    assert state["candidate"].extraction_status == LeadSourceCandidateExtractionStatus.SUCCEEDED
    assert state["staging"] is not None
    assert state["staging"].recommended_grade == CustomerGrade.B

    extraction_audits = [audit for audit in state["audits"] if audit.task_type == AITaskType.LEAD_EXTRACTION]
    grading_audits = [audit for audit in state["audits"] if audit.task_type == AITaskType.LEAD_GRADING]
    extraction_output = extraction_audits[-1].output_json
    grading_output_json = grading_audits[-1].output_json["llm_output"]
    assert extraction_output["lead"]["customer_type"] == "unknown"
    assert extraction_output["audit"]["llm_reported_customer_type"] == "fleet leasing broker"
    assert extraction_output["audit"]["customer_type_canonicalized"] is True
    assert grading_output_json["recommended_grade"] == "B"
    assert grading_output_json["next_action"] == "handoff_to_customer_service"
    assert grading_output_json["suggested_handoff_team"] == "customer_service"
    assert grading_output_json["audit"]["llm_reported_recommended_grade"] == "Interested Dealer"
    assert grading_output_json["audit"]["recommended_grade_canonicalized"] is True
    assert grading_output_json["audit"]["llm_reported_next_action"] == "call dealer tomorrow"
    assert grading_output_json["audit"]["next_action_canonicalized"] is True
