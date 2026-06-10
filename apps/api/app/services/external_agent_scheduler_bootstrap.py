from __future__ import annotations

import logging
from typing import Any
from uuid import UUID, uuid4

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import not_, select
from sqlalchemy.orm import selectinload

from app.agents.http_runtime import HttpAgentRuntime
from app.agents.scheduler_payloads import (
    build_external_deep_enrichment_batch_input,
    build_external_lead_cleanup_input,
    build_external_lead_extraction_grading_batch_input,
    build_external_lead_extraction_grading_input,
    build_external_source_discovery_input,
)
from app.db.session import AsyncSessionLocal
from app.models.agent_task_run import AgentTaskRun
from app.models.channel_plan import ChannelPlan
from app.models.enums import (
    AgentTaskRunStatus,
    ChannelPlanStatus,
    ChannelRiskLevel,
    LeadSourceCandidateExtractionStatus,
    CustomerGrade,
    StagingQueueStatus,
    StagingReviewStatus,
)
from app.models.staging_lead import StagingLead
from app.models.lead_source_candidate import LeadSourceCandidate
from app.services.agent_locks import AgentRedisLockManager
from app.services.agent_task_runs import AgentTaskRunService
from app.services.external_agent_result_consumer import ExternalAgentResultConsumer
from app.services.external_agent_scheduler import ExternalAgentSchedulerService
from app.services.lead_extraction_from_sources import LeadExtractionFromSourcesService
from app.services.external_agent_batch_consumer import ExternalAgentBatchConsumer
from app.services.staging_leads import StagingLeadService
from app.settings import settings


logger = logging.getLogger("uvicorn.error")


async def run_scheduled_external_source_discovery() -> dict[str, Any]:
    request_id = str(uuid4())
    logger.info("External Source Discovery Agent 定时任务启动：request_id=%s", request_id)
    prepared = await prepare_external_source_discovery_input(request_id=request_id)
    if prepared["status"] == "skipped":
        logger.info("External Source Discovery Agent 本轮跳过：%s", prepared)
        return prepared

    response = await HttpAgentRuntime().run_agent(
        "source-discovery",
        request_id=request_id,
        trigger_source="scheduler",
        agent_mode="active",
        input_payload=prepared["input_payload"],
        options={"timeout_seconds": settings.agents_timeout_seconds, "shadow_mode": False},
    )
    payload = _scheduled_response_summary(response)
    consumption = await consume_external_source_discovery_response(response)
    payload["consumption"] = consumption
    payload["channel_plan_count"] = prepared["channel_plan_count"]
    logger.info("External Source Discovery Agent 定时任务完成：%s", payload)
    return payload


async def run_scheduled_external_lead_extraction_grading() -> dict[str, Any]:
    request_id = str(uuid4())
    logger.info("External Lead Extraction/Grading Agent 定时任务启动：request_id=%s", request_id)

    prepared = await prepare_external_lead_extraction_grading_input(request_id=request_id)
    if prepared["status"] == "skipped":
        logger.info("External Lead Extraction/Grading Agent 本轮跳过：%s", prepared)
        return prepared

    try:
        response = await HttpAgentRuntime().run_agent(
            "lead-extraction-grading",
            request_id=request_id,
            trigger_source="scheduler",
            agent_mode="active",
            agent_task_run_id=prepared["agent_task_run_id"],
            input_payload=prepared["input_payload"],
            options={"timeout_seconds": settings.agents_timeout_seconds, "shadow_mode": False},
        )
        consumption = await consume_external_lead_extraction_grading_response(response)
        processed_items = list(consumption.get("processed_items") or [])
    except Exception as exc:
        processed_items = [
            {
                "source_candidate_id": item["source_candidate_id"],
                "source_url": item["source_url"],
                "request_id": item["request_id"],
                "status": "failed",
                "error_message": str(exc),
            }
            for item in prepared["items"]
        ]

    finalization = await finalize_external_lead_extraction_grading_batch(
        agent_task_run_id=prepared["agent_task_run_id"],
        prepared=prepared,
        processed_items=processed_items,
    )
    payload = {
        "status": finalization["status"],
        "request_id": request_id,
        "agent_type": "lead_extraction_grading",
        "agent_mode": "active",
        "writes_core_tables": False,
        "agent_task_run_id": prepared["agent_task_run_id"],
        "selected_count": prepared["selected_count"],
        "prepared_count": len(prepared["items"]),
        "preparation_failed_count": len(prepared.get("preparation_failed_items") or []),
        "processed_count": len(processed_items),
        "succeeded_count": finalization["succeeded_count"],
        "failed_count": finalization["failed_count"],
        "created_count": finalization["created_count"],
        "updated_count": finalization["updated_count"],
        "processed_items": processed_items,
    }
    logger.info("External Lead Extraction/Grading Agent 定时任务完成：%s", payload)
    return payload


async def run_scheduled_external_deep_enrichment() -> dict[str, Any]:
    request_id = str(uuid4())
    logger.info("External Deep Enrichment Agent 定时任务启动：request_id=%s", request_id)
    prepared = await prepare_external_deep_enrichment_input(request_id=request_id)
    if prepared["status"] == "skipped":
        logger.info("External Deep Enrichment Agent 本轮跳过：%s", prepared)
        return prepared

    response = await HttpAgentRuntime().run_agent(
        "deep-enrichment",
        request_id=request_id,
        trigger_source="scheduler",
        agent_mode="active",
        input_payload=prepared["input_payload"],
        options={"timeout_seconds": settings.agents_timeout_seconds, "shadow_mode": False},
    )
    consumption = await consume_external_deep_enrichment_response(response)
    payload = {
        **_scheduled_response_summary(response),
        "selected_count": prepared["selected_count"],
        **consumption,
    }
    logger.info("External Deep Enrichment Agent 定时任务完成：%s", payload)
    return payload


async def run_scheduled_external_lead_cleanup() -> dict[str, Any]:
    request_id = str(uuid4())
    logger.info("External Lead Cleanup Agent 定时任务启动：request_id=%s", request_id)
    prepared = await prepare_external_lead_cleanup_input(request_id=request_id)
    if prepared["status"] == "skipped":
        logger.info("External Lead Cleanup Agent 本轮跳过：%s", prepared)
        return prepared

    response = await HttpAgentRuntime().run_agent(
        "lead-cleanup",
        request_id=request_id,
        trigger_source="scheduler",
        agent_mode="active",
        input_payload=prepared["input_payload"],
        options={"timeout_seconds": settings.agents_timeout_seconds, "shadow_mode": False},
    )
    consumption = await consume_external_lead_cleanup_response(response)
    payload = {
        **_scheduled_response_summary(response),
        "selected_count": prepared["selected_count"],
        **consumption,
    }
    logger.info("External Lead Cleanup Agent 定时任务完成：%s", payload)
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


async def consume_external_deep_enrichment_response(response: dict[str, Any]) -> dict[str, Any]:
    async with AsyncSessionLocal() as async_session:
        def run(sync_session):
            result = ExternalAgentBatchConsumer(sync_session).consume_deep_enrichment_response(response)
            sync_session.commit()
            return result

        return await async_session.run_sync(run)


async def consume_external_lead_cleanup_response(response: dict[str, Any]) -> dict[str, Any]:
    async with AsyncSessionLocal() as async_session:
        def run(sync_session):
            result = ExternalAgentBatchConsumer(sync_session).consume_lead_cleanup_response(response)
            sync_session.commit()
            return result

        return await async_session.run_sync(run)


async def prepare_external_source_discovery_input(*, request_id: str) -> dict[str, Any]:
    async with AsyncSessionLocal() as async_session:
        def run(sync_session):
            plans = list(
                sync_session.scalars(
                    select(ChannelPlan)
                    .where(
                        ChannelPlan.status == ChannelPlanStatus.ENABLED,
                        ChannelPlan.risk_level.in_(
                            [ChannelRiskLevel.LOW, ChannelRiskLevel.MEDIUM, ChannelRiskLevel.HIGH]
                        ),
                    )
                    .order_by(ChannelPlan.updated_at.desc(), ChannelPlan.id.asc())
                    .limit(20)
                ).all()
            )

            keywords: list[str] = []
            target_segments: list[str] = []
            seed_urls: list[str] = []
            search_results: list[dict[str, Any]] = []
            for plan in plans:
                plan_keywords = [str(item).strip() for item in (plan.keywords or []) if str(item).strip()]
                keywords.extend(plan_keywords)
                target_segments.append(plan.channel_type)
                seed_url = _discovery_seed_url_for_plan(plan, plan_keywords)
                seed_urls.append(seed_url)
                search_results.append(
                    {
                        "url": seed_url,
                        "title": f"{plan.channel_name} {plan.city} {plan.country}",
                        "snippet": (
                            f"渠道计划：{plan.channel_name}；类型：{plan.channel_type}；"
                            f"地区：{plan.city}, {plan.country}；风险：{plan.risk_level.value}。"
                        ),
                        "source_type": _source_type_for_plan(plan),
                        "discovery_query": " ".join([*(plan_keywords or [plan.channel_type]), plan.city, plan.country]).strip(),
                    }
                )

            if plans:
                market = _market_from_plans(plans)
                strategy_source = "channel_plans"
                channel_plan_ids = [str(plan.id) for plan in plans]
            else:
                market = "Russia"
                strategy_source = "default_source_discovery_agent"
                channel_plan_ids = []
                keywords.extend(
                    [
                        "автодилер",
                        "автосалон",
                        "used cars",
                        "import cars",
                        "Toyota dealer",
                        "vehicle export",
                    ]
                )
                target_segments.extend(
                    [
                        "used car dealers",
                        "vehicle import/export dealers",
                        "dealer directories",
                        "official dealer websites",
                        "public marketplace listings",
                    ]
                )

            input_payload = build_external_source_discovery_input(
                request_id=request_id,
                market=market,
                channel_strategy={
                    "keywords": _unique_strings(keywords),
                    "target_segments": _unique_strings(target_segments),
                    "risk_policy": (
                        "只允许公开来源发现；不得登录、私信、绕过验证码或绕过反爬；"
                        "Low/Medium 可自动审核通过进入后续抽取；High 仅进入人工复核；Forbidden 禁止进入自动任务。"
                    ),
                    "source": strategy_source,
                    "channel_plan_ids": channel_plan_ids,
                },
                seed_urls=_unique_strings(seed_urls),
                search_results=search_results,
            )
            return {
                "status": "prepared",
                "channel_plan_count": len(plans),
                "input_payload": input_payload,
            }

        return await async_session.run_sync(run)


async def prepare_external_lead_extraction_grading_input(*, request_id: str) -> dict[str, Any]:
    async with AsyncSessionLocal() as async_session:
        def run(sync_session):
            service = LeadExtractionFromSourcesService(sync_session)
            try:
                selection = service.create_lead_extraction_task_from_sources(
                    limit=settings.external_agent_lead_extraction_grading_batch_size,
                    trigger_source="scheduler_external_lead_extraction_grading_selection",
                    country="Russia",
                )
            except ValueError as exc:
                sync_session.rollback()
                return {
                    "status": "skipped",
                    "reason": "no_eligible_approved_sources",
                    "message": str(exc),
                }

            task_run = selection.task_run
            service._apply_task_payload(task_run, AgentTaskRunService.start(service._task_to_payload(task_run)))
            items: list[dict[str, Any]] = []
            preparation_failed_items: list[dict[str, Any]] = []
            source_content_lengths: dict[str, int] = {}
            for candidate in selection.selected_candidates:
                try:
                    candidate_url = service._ensure_candidate_url_bridge(candidate)
                    source_content = service._read_public_text_for_candidate(candidate, candidate_url=candidate_url)
                except ValueError as exc:
                    error_type = service._error_type_for_candidate_failure(str(exc))
                    candidate.extraction_status = (
                        LeadSourceCandidateExtractionStatus.RETRY
                        if service._candidate_failure_is_retryable(error_type)
                        else LeadSourceCandidateExtractionStatus.BLOCKED
                    )
                    preparation_failed_items.append(
                        {
                            "source_candidate_id": str(candidate.id),
                            "source_url": candidate.source_url,
                            "status": "failed",
                            "error_type": error_type,
                            "error_message": str(exc),
                            "retryable": service._candidate_failure_is_retryable(error_type),
                        }
                    )
                    continue

                item_request_id = str(uuid4())
                source_content_lengths[str(candidate.id)] = len(source_content)
                source_payload = {
                    "request_id": item_request_id,
                    "source_candidate_id": str(candidate.id),
                    "candidate_url_id": str(candidate_url.id),
                    "source_url": candidate.source_url,
                    "source_content": source_content,
                    "risk_flags": [],
                    "existing_grade": None,
                    "expected_contacts": {},
                }
                input_payload = build_external_lead_extraction_grading_input(
                    request_id=item_request_id,
                    source_candidate_id=source_payload["source_candidate_id"],
                    candidate_url_id=source_payload["candidate_url_id"],
                    source_url=source_payload["source_url"],
                    source_content=source_payload["source_content"],
                    risk_flags=source_payload["risk_flags"],
                    existing_grade=source_payload["existing_grade"],
                    expected_contacts=source_payload["expected_contacts"],
                )
                items.append(
                    {
                        "request_id": item_request_id,
                        "source_candidate_id": str(candidate.id),
                        "candidate_url_id": str(candidate_url.id),
                        "source_url": candidate.source_url,
                        "source_content": source_content,
                        "input_payload": input_payload,
                        "source_payload": source_payload,
                    }
                )

            if not items:
                task_run.status = AgentTaskRunStatus.FAILED
                task_run.error_message = "本轮来源公开文本读取全部失败。"
                task_run.output_summary_json = {
                    **(task_run.output_summary_json or {}),
                    "selected_count": len(selection.selected_candidates),
                    "prepared_count": 0,
                    "preparation_failed_count": len(preparation_failed_items),
                    "preparation_failed_items": preparation_failed_items,
                }
                sync_session.flush()
                return {
                    "status": "skipped",
                    "reason": "public_page_read_failed",
                    "message": "本轮来源公开文本读取全部失败。",
                    "agent_task_run_id": str(task_run.id),
                    "selected_count": len(selection.selected_candidates),
                    "preparation_failed_items": preparation_failed_items,
                }

            task_run.input_json = {
                **(task_run.input_json or {}),
                "external_agent_request_id": request_id,
                "external_agent_runtime": "apps_agents",
                "external_agent_batch_size": settings.external_agent_lead_extraction_grading_batch_size,
                "prepared_candidate_ids": [item["source_candidate_id"] for item in items],
                "prepared_source_urls": [item["source_url"] for item in items],
            }
            task_run.output_summary_json = {
                **(task_run.output_summary_json or {}),
                "external_agent_status": "pending",
                "selected_count": len(selection.selected_candidates),
                "prepared_count": len(items),
                "preparation_failed_count": len(preparation_failed_items),
                "preparation_failed_items": preparation_failed_items,
                "source_content_lengths": source_content_lengths,
            }
            sync_session.flush()
            first_item = items[0]
            batch_input_payload = build_external_lead_extraction_grading_batch_input(
                request_id=request_id,
                sources=[item["source_payload"] for item in items],
            )
            return {
                "status": "prepared",
                "selected_count": len(selection.selected_candidates),
                "prepared_count": len(items),
                "agent_task_run_id": str(task_run.id),
                "items": items,
                "preparation_failed_items": preparation_failed_items,
                "source_candidate_id": first_item["source_candidate_id"],
                "input_payload": batch_input_payload,
            }

        payload = await async_session.run_sync(run)
        await async_session.commit()
        return payload


async def prepare_external_deep_enrichment_input(*, request_id: str) -> dict[str, Any]:
    async with AsyncSessionLocal() as async_session:
        def run(sync_session):
            leads = list(
                sync_session.scalars(
                    select(StagingLead)
                    .options(selectinload(StagingLead.candidate_url))
                    .where(
                        StagingLead.recommended_grade.in_([CustomerGrade.A, CustomerGrade.B, CustomerGrade.C]),
                        StagingLead.review_status.not_in([StagingReviewStatus.APPROVED, StagingReviewStatus.REJECTED]),
                        StagingLead.queue_status.not_in([StagingQueueStatus.ELIGIBLE, StagingQueueStatus.BLOCKED]),
                        not_(StagingLeadService.manual_grade_update_exists()),
                    )
                    .order_by(StagingLead.updated_at.asc(), StagingLead.id.asc())
                    .limit(settings.external_agent_deep_enrichment_batch_size)
                ).all()
            )
            if not leads:
                return {"status": "skipped", "reason": "no_abc_staging_leads", "message": "没有 A/B/C 线索可深挖。"}
            items = [
                {
                    "request_id": str(uuid4()),
                    "staging_lead_id": str(lead.id),
                    "lead_snapshot": _staging_lead_snapshot(lead),
                    "missing_fields": list(lead.missing_fields or []),
                    "requested_actions": [],
                }
                for lead in leads
            ]
            return {
                "status": "prepared",
                "selected_count": len(leads),
                "items": items,
                "input_payload": build_external_deep_enrichment_batch_input(request_id=request_id, leads=items),
            }

        return await async_session.run_sync(run)


async def prepare_external_lead_cleanup_input(*, request_id: str) -> dict[str, Any]:
    async with AsyncSessionLocal() as async_session:
        def run(sync_session):
            leads = list(
                sync_session.scalars(
                    select(StagingLead)
                    .options(selectinload(StagingLead.candidate_url))
                    .where(
                        StagingLead.recommended_grade.in_([CustomerGrade.WATCH, CustomerGrade.INVALID]),
                        StagingLead.review_status.not_in([StagingReviewStatus.REJECTED, StagingReviewStatus.DUPLICATE]),
                        not_(StagingLeadService.manual_grade_update_exists()),
                    )
                    .order_by(StagingLead.updated_at.asc(), StagingLead.id.asc())
                    .limit(settings.external_agent_lead_cleanup_batch_size)
                ).all()
            )
            if not leads:
                return {"status": "skipped", "reason": "no_watch_invalid_staging_leads", "message": "没有 Watch/Invalid 线索可清洗。"}
            items = [_staging_lead_snapshot(lead) for lead in leads]
            return {
                "status": "prepared",
                "selected_count": len(leads),
                "items": items,
                "input_payload": build_external_lead_cleanup_input(request_id=request_id, leads=items),
            }

        return await async_session.run_sync(run)


async def finalize_external_lead_extraction_grading_source(
    *,
    candidate_id: str,
    agent_task_run_id: str,
    succeeded: bool,
    output_summary_json: dict[str, Any] | None = None,
    error_message: str | None = None,
) -> None:
    async with AsyncSessionLocal() as async_session:
        def run(sync_session):
            candidate = sync_session.get(LeadSourceCandidate, UUID(str(candidate_id)))
            task_run = sync_session.get(AgentTaskRun, UUID(str(agent_task_run_id)))
            if candidate is not None:
                candidate.extraction_status = (
                    LeadSourceCandidateExtractionStatus.SUCCEEDED
                    if succeeded
                    else LeadSourceCandidateExtractionStatus.RETRY
                )
            if task_run is not None:
                if succeeded:
                    payload = AgentTaskRunService.succeed(
                        {
                            "task_type": task_run.task_type,
                            "status": task_run.status,
                            "trigger_source": task_run.trigger_source,
                            "input_json": task_run.input_json,
                            "output_summary_json": task_run.output_summary_json,
                            "retry_count": task_run.retry_count,
                            "created_at": task_run.created_at,
                            "updated_at": task_run.updated_at,
                        },
                        output_summary_json={
                            **(task_run.output_summary_json or {}),
                            **(output_summary_json or {}),
                        },
                    )
                else:
                    payload = AgentTaskRunService.fail(
                        {
                            "task_type": task_run.task_type,
                            "status": task_run.status,
                            "trigger_source": task_run.trigger_source,
                            "input_json": task_run.input_json,
                            "output_summary_json": task_run.output_summary_json,
                            "retry_count": task_run.retry_count,
                            "created_at": task_run.created_at,
                            "updated_at": task_run.updated_at,
                        },
                        error_message=error_message or "External Lead Extraction/Grading 消费失败。",
                        error={"type": "external_agent_result_error", "message": error_message or "External agent failed."},
                    )
                for key, value in payload.items():
                    if hasattr(task_run, key):
                        setattr(task_run, key, value)
            sync_session.flush()

        await async_session.run_sync(run)
        await async_session.commit()


async def finalize_external_lead_extraction_grading_batch(
    *,
    agent_task_run_id: str,
    prepared: dict[str, Any],
    processed_items: list[dict[str, Any]],
) -> dict[str, Any]:
    async with AsyncSessionLocal() as async_session:
        def run(sync_session):
            task_run = sync_session.get(AgentTaskRun, UUID(str(agent_task_run_id)))
            if task_run is None:
                raise ValueError("External Lead Extraction/Grading 批次任务不存在。")

            created_count = sum(int((item.get("consumption") or {}).get("created_count") or 0) for item in processed_items)
            updated_count = sum(int((item.get("consumption") or {}).get("updated_count") or 0) for item in processed_items)
            succeeded_items = [item for item in processed_items if item.get("status") == "succeeded"]
            failed_items = [item for item in processed_items if item.get("status") != "succeeded"]
            preparation_failed_items = list(prepared.get("preparation_failed_items") or [])

            for item in processed_items:
                candidate = sync_session.get(LeadSourceCandidate, UUID(str(item["source_candidate_id"])))
                if candidate is None:
                    continue
                if item.get("status") == "succeeded":
                    candidate.extraction_status = LeadSourceCandidateExtractionStatus.SUCCEEDED
                else:
                    candidate.extraction_status = LeadSourceCandidateExtractionStatus.RETRY
                candidate.updated_at = AgentTaskRunService._now()
                if item.get("status") == "succeeded":
                    candidate.last_extracted_at = candidate.updated_at

            summary = {
                **(task_run.output_summary_json or {}),
                "status": "succeeded" if succeeded_items else "failed",
                "selected_count": prepared.get("selected_count", 0),
                "prepared_count": len(prepared.get("items") or []),
                "processed_count": len(processed_items),
                "succeeded_count": len(succeeded_items),
                "failed_count": len(failed_items) + len(preparation_failed_items),
                "preparation_failed_count": len(preparation_failed_items),
                "created_count": created_count,
                "updated_count": updated_count,
                "processed_items": processed_items,
                "preparation_failed_items": preparation_failed_items,
            }
            task_payload = {
                "task_type": task_run.task_type,
                "status": task_run.status,
                "trigger_source": task_run.trigger_source,
                "input_json": task_run.input_json,
                "output_summary_json": task_run.output_summary_json,
                "retry_count": task_run.retry_count,
                "created_at": task_run.created_at,
                "updated_at": task_run.updated_at,
            }
            if succeeded_items:
                payload = AgentTaskRunService.succeed(task_payload, output_summary_json=summary)
            else:
                payload = AgentTaskRunService.fail(
                    task_payload,
                    error_message="External Lead Extraction/Grading 本轮全部来源处理失败。",
                    error={
                        "type": "external_agent_batch_failed",
                        "message": "External Lead Extraction/Grading 本轮全部来源处理失败。",
                        "failed_count": summary["failed_count"],
                    },
                )
                payload["output_summary_json"] = {
                    **(payload.get("output_summary_json") or {}),
                    **summary,
                }
            for key, value in payload.items():
                if hasattr(task_run, key):
                    setattr(task_run, key, value)
            sync_session.flush()
            return summary

        result = await async_session.run_sync(run)
        await async_session.commit()
        return result


def _scheduled_response_summary(response: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": response.get("status"),
        "agent_service_run_id": response.get("agent_service_run_id"),
        "request_id": response.get("request_id"),
        "agent_type": response.get("agent_type"),
        "agent_mode": response.get("agent_mode"),
        "writes_core_tables": (response.get("audit") or {}).get("writes_core_tables"),
    }


def _staging_lead_snapshot(lead: StagingLead) -> dict[str, Any]:
    candidate = getattr(lead, "candidate_url", None)
    return {
        "staging_lead_id": str(lead.id),
        "customer_name": lead.customer_name,
        "country": lead.country,
        "city": lead.city,
        "customer_type": lead.customer_type.value if getattr(lead, "customer_type", None) else None,
        "contacts_json": lead.contacts_json or [],
        "activity_level": lead.activity_level,
        "scale_signal": lead.scale_signal,
        "import_used_car_relevance": lead.import_used_car_relevance,
        "source_evidence": lead.source_evidence,
        "recommended_grade": lead.recommended_grade.value if getattr(lead, "recommended_grade", None) else None,
        "recommended_reason": lead.recommended_reason,
        "missing_fields": lead.missing_fields or [],
        "source_url": getattr(candidate, "url", None),
        "source_risk_level": getattr(getattr(candidate, "source_risk_level", None), "value", None),
    }


def _market_from_plans(plans: list[ChannelPlan]) -> str:
    countries = _unique_strings([plan.country for plan in plans if plan.country])
    return countries[0] if len(countries) == 1 else ", ".join(countries)


def _source_type_for_plan(plan: ChannelPlan) -> str:
    text = f"{plan.channel_name} {plan.channel_type}".lower()
    if "official" in text or "官网" in text or "website" in text:
        return "official_website"
    if "directory" in text or "目录" in text:
        return "public_directory"
    if "social" in text or "社媒" in text or "vk" in text or "telegram" in text:
        return "public_social"
    if plan.risk_level == ChannelRiskLevel.HIGH:
        return "public_social"
    return "public_directory"


def _discovery_seed_url_for_plan(plan: ChannelPlan, keywords: list[str]) -> str:
    from urllib.parse import quote_plus

    query = " ".join([*(keywords or [plan.channel_type]), plan.city, plan.country]).strip()
    encoded = quote_plus(query)
    source_type = _source_type_for_plan(plan)
    if source_type == "official_website":
        return f"https://www.google.com/search?q={encoded}+official+dealer"
    if source_type == "public_social":
        return f"https://www.google.com/search?q={encoded}+public+profile"
    return f"https://www.google.com/search?q={encoded}+business+directory"


def _unique_strings(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for item in values:
        value = str(item).strip()
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


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
            "external_deep_enrichment": {
                "enabled": settings.external_agent_deep_enrichment_enabled,
                "interval_seconds": settings.external_agent_deep_enrichment_interval_seconds,
            },
            "external_lead_cleanup": {
                "enabled": settings.external_agent_lead_cleanup_enabled,
                "interval_seconds": settings.external_agent_lead_cleanup_interval_seconds,
            },
        },
        handlers={
            "external_source_discovery": run_scheduled_external_source_discovery,
            "external_lead_extraction_grading": run_scheduled_external_lead_extraction_grading,
            "external_deep_enrichment": run_scheduled_external_deep_enrichment,
            "external_lead_cleanup": run_scheduled_external_lead_cleanup,
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
