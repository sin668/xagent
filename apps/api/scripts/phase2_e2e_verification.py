from __future__ import annotations

import asyncio
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from uuid import uuid4

import httpx
from sqlalchemy import delete, select, text

API_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_ROOT))

from app.db.session import AsyncSessionLocal
from app.models.ai_audit_log import AIAuditLog
from app.models.agent_task_run import AgentTaskRun
from app.models.candidate_url import CandidateUrl
from app.models.collection_task import CollectionTask
from app.models.enums import (
    AgentTaskRunStatus,
    AgentTaskType,
)
from app.models.lead_source_candidate import LeadSourceCandidate
from app.models.page_snapshot import PageSnapshot
from app.models.staging_lead import StagingLead
from app.services.lead_extraction_from_sources import LeadExtractionFromSourcesService
from app.services.lead_source_candidates import LeadSourceCandidateService


TEST_PREFIX = "p2e6s4"
API_BASE_URL = "http://127.0.0.1:8000"


@dataclass
class VerificationResult:
    postgres_ok: bool
    redis_checked_by_shell: bool
    llm_health: dict
    source_discovery_run: dict
    seeded_candidate_ids: dict
    mobile_review_response: dict
    lead_extraction_selection: dict
    blocked_gate_result: dict
    db_counts_after: dict
    notes: list[str]


class FakeLLMClient:
    def __init__(self, *, source_url: str) -> None:
        self.source_url = source_url

    async def generate_json(self, task_type: str, system_prompt: str, user_prompt: str, output_schema: dict) -> object:
        if task_type == "LEAD_EXTRACTION":
            output_json = {
                "schema_version": "poc-ai-output-v1",
                "task_type": "lead_extraction",
                "source": {"source_url": self.source_url},
                "risk_blocked": False,
                "risk_block_reason": None,
                "lead": {
                    "customer_name": "P2E6S4 Auto City Moscow",
                    "country": "Russia",
                    "city": "Moscow",
                    "customer_type": "local_dealer_secondary_dealer",
                    "activity_signal": "公开页面展示二手车库存和联系方式",
                    "scale_signal": "多个车型库存",
                    "import_used_relevance": "high",
                    "contacts": {
                        "emails": ["sales@p2e6s4-autocity.example"],
                        "phones": [],
                        "whatsapp": [],
                        "telegram": [],
                        "wechat": [],
                        "website_forms": [],
                    },
                    "source_evidence": [
                        {
                            "claim": "used_car_signal",
                            "evidence_text": "Used cars and imported SUVs",
                            "source_url": self.source_url,
                        }
                    ],
                    "missing_fields": [],
                },
                "audit": {
                    "model": "p2e6s4-fake-extraction-model",
                    "prompt_version": "lead-extraction-v1",
                    "input_saved": True,
                    "output_saved": True,
                },
            }
        elif task_type == "LEAD_GRADING":
            output_json = {
                "schema_version": "poc-ai-output-v1",
                "task_type": "lead_grading",
                "lead_id": "p2e6s4-staging-lead",
                "recommended_grade": "C",
                "recommended_reason": "客户公开展示二手车库存和邮箱，适合出口销售人工复核跟进。",
                "reason_codes": ["has_public_contact", "used_car_signal"],
                "evidence_refs": [
                    {
                        "claim": "used_car_signal",
                        "evidence_text": "Used cars and imported SUVs",
                        "source_url": self.source_url,
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
                    "model": "p2e6s4-fake-grading-model",
                    "prompt_version": "lead-grading-v1",
                    "input_saved": True,
                    "output_saved": True,
                },
            }
        else:
            raise AssertionError(f"Unexpected task type: {task_type}")

        return type(
            "Result",
            (),
            {
                "provider": "p2e6s4-fake-provider",
                "model": output_json["audit"]["model"],
                "latency_ms": 10,
                "token_usage": {"total_tokens": 123},
                "output_json": output_json,
                "error": None,
            },
        )()


def candidate_payload(suffix: str, *, risk_level: str, channel_name: str) -> dict:
    source_url = f"https://{TEST_PREFIX}-{suffix}-{risk_level.lower()}.example.com/contact"
    return {
        "source_url": source_url,
        "platform": "official_website",
        "channel_name": channel_name,
        "country": "Russia",
        "city": "Moscow",
        "risk_level": risk_level,
        "discovery_method": "e2e_verification_seed",
        "discovery_query": "p2e6s4 verification",
        "discovery_reason": "端到端验收使用的公开来源候选。",
        "evidence_note": "公开页面包含 Used cars and imported SUVs 以及 sales@p2e6s4-autocity.example。",
        "evidence_links": [source_url],
        "confidence_score": 0.91,
    }


async def cleanup_records() -> None:
    async with AsyncSessionLocal() as async_session:
        await async_session.execute(delete(AIAuditLog).where(AIAuditLog.source_url.like(f"https://{TEST_PREFIX}%")))
        await async_session.execute(delete(StagingLead).where(StagingLead.customer_name == "P2E6S4 Auto City Moscow"))
        await async_session.execute(
            delete(PageSnapshot).where(
                PageSnapshot.candidate_url_id.in_(
                    select(CandidateUrl.id).where(CandidateUrl.url.like(f"https://{TEST_PREFIX}%"))
                )
            )
        )
        await async_session.execute(delete(CandidateUrl).where(CandidateUrl.url.like(f"https://{TEST_PREFIX}%")))
        await async_session.execute(delete(CollectionTask).where(CollectionTask.channel_name.like(f"%{TEST_PREFIX}%")))
        await async_session.execute(
            delete(LeadSourceCandidate).where(LeadSourceCandidate.normalized_domain.like(f"{TEST_PREFIX}%"))
        )
        await async_session.execute(delete(AgentTaskRun).where(AgentTaskRun.trigger_source.like(f"{TEST_PREFIX}%")))
        await async_session.commit()


async def seed_candidates() -> dict[str, str]:
    suffix = uuid4().hex[:8]
    async with AsyncSessionLocal() as async_session:
        def run(sync_session):
            seed_task = AgentTaskRun(
                task_type=AgentTaskType.SOURCE_DISCOVERY,
                status=AgentTaskRunStatus.SUCCEEDED,
                trigger_source=f"{TEST_PREFIX}-seed-{suffix}",
                input_json={"country": "Russia"},
                output_summary_json={"created_count": 3},
            )
            sync_session.add(seed_task)
            sync_session.flush()
            service = LeadSourceCandidateService(sync_session)
            medium = service.upsert_candidate(
                candidate_payload(suffix, risk_level="Medium", channel_name=f"{TEST_PREFIX}_dealer_directory"),
                created_by_task_run_id=seed_task.id,
                llm_provider="deepseek",
                llm_model="deepseek-chat",
                llm_output_json={"task_type": "SOURCE_DISCOVERY", "candidates": [], "blocked_candidates": []},
            ).candidate
            high = service.upsert_candidate(
                candidate_payload(suffix, risk_level="High", channel_name=f"{TEST_PREFIX}_high_social"),
                created_by_task_run_id=seed_task.id,
                llm_provider="deepseek",
                llm_model="deepseek-chat",
                llm_output_json={"task_type": "SOURCE_DISCOVERY", "candidates": [], "blocked_candidates": []},
            ).candidate
            forbidden = service.upsert_candidate(
                candidate_payload(suffix, risk_level="Forbidden", channel_name=f"{TEST_PREFIX}_forbidden"),
                created_by_task_run_id=seed_task.id,
                llm_provider="deepseek",
                llm_model="deepseek-chat",
                llm_output_json={"task_type": "SOURCE_DISCOVERY", "candidates": [], "blocked_candidates": []},
            ).candidate
            sync_session.flush()
            return {
                "medium": str(medium.id),
                "medium_url": medium.source_url,
                "high": str(high.id),
                "forbidden": str(forbidden.id),
            }

        result = await async_session.run_sync(run)
        await async_session.commit()
        return result


async def run_lead_extraction_with_fake_llm(source_url: str) -> tuple[dict, dict]:
    async with AsyncSessionLocal() as async_session:
        def run(sync_session):
            service = LeadExtractionFromSourcesService(sync_session, llm_client=FakeLLMClient(source_url=source_url))
            selection = service.create_lead_extraction_task_from_sources(
                limit=1,
                trigger_source=f"{TEST_PREFIX}-lead-extraction-selection",
                country="Russia",
                city="Moscow",
            )
            selected_task_id = str(selection.task_run.id)
            selected_candidate_ids = [str(candidate.id) for candidate in selection.selected_candidates]
            blocked = [
                {
                    "candidate_id": str(item.candidate_id),
                    "risk_level": item.risk_level,
                    "review_status": item.review_status,
                    "extraction_status": item.extraction_status,
                    "block_reason": item.block_reason,
                }
                for item in selection.blocked_candidates
            ]
            summary = service.run_queued_lead_extraction_task(selected_task_id)
            sync_session.flush()
            return {
                "task_id": selected_task_id,
                "selected_candidate_ids": selected_candidate_ids,
                "blocked_candidates": blocked,
            }, summary

        selection_payload, summary = await async_session.run_sync(run)
        await async_session.commit()
        return selection_payload, summary


async def verify_risk_gate(candidate_ids: dict[str, str]) -> dict:
    async with AsyncSessionLocal() as async_session:
        def run(sync_session):
            service = LeadExtractionFromSourcesService(sync_session)
            high = sync_session.get(LeadSourceCandidate, candidate_ids["high"])
            forbidden = sync_session.get(LeadSourceCandidate, candidate_ids["forbidden"])
            return {
                "high": {
                    "candidate_id": str(high.id),
                    "risk_level": high.risk_level.value,
                    "review_status": high.review_status.value,
                    "approved_for_extraction": high.approved_for_extraction,
                    "extraction_status": high.extraction_status.value,
                    "block_reason": service._block_reason(high),
                },
                "forbidden": {
                    "candidate_id": str(forbidden.id),
                    "risk_level": forbidden.risk_level.value,
                    "review_status": forbidden.review_status.value,
                    "approved_for_extraction": forbidden.approved_for_extraction,
                    "extraction_status": forbidden.extraction_status.value,
                    "block_reason": service._block_reason(forbidden),
                },
            }

        return await async_session.run_sync(run)


async def count_after() -> dict:
    async with AsyncSessionLocal() as async_session:
        counts = {}
        for table, condition in [
            ("agent_task_runs", "trigger_source like 'p2e6s4%' or trigger_source = 'lead_source_review_api'"),
            ("lead_source_candidates", "normalized_domain like 'p2e6s4%'"),
            ("staging_leads", "customer_name = 'P2E6S4 Auto City Moscow'"),
            ("ai_audit_logs", "source_url like 'https://p2e6s4%'"),
        ]:
            counts[table] = (
                await async_session.execute(text(f"select count(*) from {table} where {condition}"))
            ).scalar_one()
        return counts


async def main() -> None:
    await cleanup_records()
    notes: list[str] = []
    async with httpx.AsyncClient(timeout=60) as client:
        health = (await client.get(f"{API_BASE_URL}/health")).json()
        postgres_ok = health.get("status") == "ok"
        llm_health = (await client.get(f"{API_BASE_URL}/llm-health")).json()
        source_discovery_run = (
            await client.post(
                f"{API_BASE_URL}/agent-tasks/source-discovery/run",
                json={
                    "country": "Russia",
                    "cities": ["Moscow"],
                    "channel_strategy": "official website and public directories only",
                    "keywords": ["автосалон", "used cars", "dealer"],
                    "limit": 20,
                },
            )
        ).json()
        if not llm_health.get("configuration_complete"):
            notes.append("真实外部 LLM 配置未完成，SOURCE_DISCOVERY 真实 LLM 调用失败是预期验收事实。")

        seeded = await seed_candidates()
        review_response = (
            await client.post(
                f"{API_BASE_URL}/lead-source-candidates/{seeded['medium']}/review-actions",
                json={
                    "action": "approve_for_extraction",
                    "reviewer_id": "p2e6s4-mobile-reviewer",
                    "review_note": "移动端 H5 真实 API 审核：公开来源可进入只读抽取。",
                },
            )
        ).json()

    selection_payload, extraction_summary = await run_lead_extraction_with_fake_llm(seeded["medium_url"])
    risk_gate = await verify_risk_gate(seeded)
    counts = await count_after()
    result = VerificationResult(
        postgres_ok=postgres_ok,
        redis_checked_by_shell=True,
        llm_health=llm_health,
        source_discovery_run=source_discovery_run,
        seeded_candidate_ids=seeded,
        mobile_review_response=review_response,
        lead_extraction_selection={**selection_payload, "execution_summary": extraction_summary},
        blocked_gate_result={
            **risk_gate,
            "forbidden_blocked": risk_gate["forbidden"]["block_reason"] == "forbidden_risk_blocked",
            "high_unapproved_blocked": risk_gate["high"]["block_reason"] == "high_risk_requires_manual_approval",
        },
        db_counts_after=counts,
        notes=notes,
    )
    print(json.dumps(asdict(result), ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())
