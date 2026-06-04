from __future__ import annotations

import asyncio
from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import case, select
from sqlalchemy.orm import Session

from app.models.candidate_url import CandidateUrl
from app.models.agent_task_run import AgentTaskRun
from app.models.channel_plan import ChannelPlan
from app.models.enums import (
    AgentTaskRunStatus,
    AgentTaskType,
    CandidateUrlStatus,
    ChannelPlanStatus,
    ChannelRiskLevel,
    CollectionTaskStatus,
    LeadSourceCandidateExtractionStatus,
    LeadSourceCandidateReviewStatus,
    PageSnapshotReadStatus,
    SourceUsageType,
)
from app.models.lead_source_candidate import LeadSourceCandidate
from app.services.agent_thread_runner import AgentThreadRunner
from app.services.agent_task_runs import AgentTaskRunService
from app.services.llm_client import LLMClient
from app.services.llm_lead_extraction import LLMLeadExtractionService
from app.services.llm_lead_grading import LLMLeadGradingService
from app.services.raw_collection import RawCollectionService
from app.services.public_page_read_agent import PublicPageReadAgentService


@dataclass(frozen=True)
class BlockedLeadExtractionSource:
    candidate_id: object
    risk_level: str
    review_status: str
    extraction_status: str
    block_reason: str


@dataclass(frozen=True)
class LeadExtractionSourceSelectionResult:
    task_run: AgentTaskRun
    selected_candidates: list[LeadSourceCandidate]
    blocked_candidates: list[BlockedLeadExtractionSource]


class LeadExtractionFromSourcesService:
    ALLOWED_REVIEW_STATUSES = {
        LeadSourceCandidateReviewStatus.AUTO_APPROVED,
        LeadSourceCandidateReviewStatus.APPROVED,
    }
    ALLOWED_EXTRACTION_STATUSES = {
        LeadSourceCandidateExtractionStatus.PENDING,
        LeadSourceCandidateExtractionStatus.RETRY,
    }
    LEAD_EXTRACTION_OUTPUT_SCHEMA = {
        "type": "object",
        "required": ["schema_version", "task_type", "source", "risk_blocked", "lead", "audit"],
        "properties": {
            "schema_version": {"type": "string"},
            "task_type": {"type": "string"},
            "source": {
                "type": "object",
                "required": ["source_url"],
                "properties": {
                    "source_url": {"type": "string"},
                    "source_platform": {"type": "string"},
                    "channel_risk_level": {"type": "string"},
                    "search_keyword": {"type": ["string", "null"]},
                    "collected_at": {"type": ["string", "null"]},
                    "operator": {"type": ["string", "null"]},
                },
            },
            "risk_blocked": {"type": "boolean"},
            "risk_block_reason": {"type": ["string", "null"]},
            "lead": {
                "type": "object",
                "required": [
                    "customer_name",
                    "country",
                    "city",
                    "customer_type",
                    "activity_signal",
                    "scale_signal",
                    "import_used_relevance",
                    "contacts",
                    "source_evidence",
                    "missing_fields",
                ],
                "properties": {
                    "customer_name": {"type": "string"},
                    "country": {"type": "string"},
                    "city": {"type": "string"},
                    "customer_type": {"type": "string"},
                    "business_scope": {"type": ["string", "null"]},
                    "sells_used_or_imported_cars": {"type": ["string", "null"]},
                    "activity_signal": {"type": "string"},
                    "scale_signal": {"type": "string"},
                    "import_used_relevance": {"type": "string"},
                    "contacts": {
                        "type": "object",
                        "required": ["emails", "phones", "whatsapp", "telegram", "wechat", "website_forms"],
                        "properties": {
                            "emails": {"type": "array", "items": {"type": "string"}},
                            "phones": {"type": "array", "items": {"type": "string"}},
                            "whatsapp": {"type": "array", "items": {"type": "string"}},
                            "telegram": {"type": "array", "items": {"type": "string"}},
                            "wechat": {"type": "array", "items": {"type": "string"}},
                            "website_forms": {"type": "array", "items": {"type": "string"}},
                        },
                    },
                    "official_website": {"type": ["string", "null"]},
                    "source_evidence": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["claim", "evidence_text", "source_url"],
                            "properties": {
                                "claim": {"type": "string"},
                                "evidence_text": {"type": "string"},
                                "source_url": {"type": "string"},
                            },
                        },
                    },
                    "missing_fields": {"type": "array", "items": {"type": "string"}},
                },
            },
            "recommended_next_action": {"type": ["string", "null"]},
            "touch_queue_allowed": {"type": ["boolean", "null"]},
            "audit": {"type": "object"},
        },
    }
    LEAD_GRADING_OUTPUT_SCHEMA = {
        "type": "object",
        "required": [
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
        ],
        "properties": {
            "schema_version": {"type": "string"},
            "task_type": {"type": "string"},
            "lead_id": {"type": ["string", "null"]},
            "recommended_grade": {"type": "string"},
            "recommended_reason": {"type": "string"},
            "reason_codes": {"type": "array", "items": {"type": "string"}},
            "evidence_refs": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["claim", "evidence_text", "source_url"],
                    "properties": {
                        "claim": {"type": "string"},
                        "evidence_text": {"type": "string"},
                        "source_url": {"type": "string"},
                    },
                },
            },
            "missing_fields": {"type": "array", "items": {"type": "string"}},
            "next_action": {"type": "string"},
            "suggested_handoff_team": {"type": "string"},
            "touch_queue_allowed": {"type": "boolean"},
            "touch_channel_limit": {"type": ["string", "null"]},
            "compliance_review_required": {"type": "boolean"},
            "human_review_required": {"type": ["boolean", "null"]},
            "risk_flags": {"type": "array", "items": {"type": "string"}},
            "audit": {"type": "object"},
        },
    }

    def __init__(self, session: Session, *, llm_client: LLMClient | None = None) -> None:
        self.session = session
        self.llm_client = llm_client or LLMClient()
        self.raw_collection_service = RawCollectionService(session)
        self.public_page_read_service = PublicPageReadAgentService(session)
        self.extraction_service = LLMLeadExtractionService(session)
        self.grading_service = LLMLeadGradingService(session)

    def create_lead_extraction_task_from_sources(
        self,
        *,
        limit: int = 20,
        trigger_source: str = "lead_extraction_source_selection_api",
        country: str | None = None,
        city: str | None = None,
    ) -> LeadExtractionSourceSelectionResult:
        self._recover_orphaned_queued_sources(country=country, city=city)
        self._auto_approve_low_medium_sources(country=country, city=city)
        candidates = self._load_candidate_pool(country=country, city=city, limit=max(limit * 10, 100))
        blocked: list[BlockedLeadExtractionSource] = []
        selected: list[LeadSourceCandidate] = []

        for candidate in candidates:
            block_reason = self._block_reason(candidate)
            if block_reason is not None:
                blocked.append(self._blocked(candidate, block_reason))
                continue
            selected.append(candidate)
            if len(selected) >= limit:
                break

        if not selected:
            raise ValueError("没有符合准入条件的 approved 来源可进入 LEAD_EXTRACTION。")

        now = datetime.now(UTC)
        for candidate in selected:
            candidate.extraction_status = LeadSourceCandidateExtractionStatus.QUEUED
            candidate.updated_at = now

        task_run = AgentTaskRun(
            task_type=AgentTaskType.LEAD_EXTRACTION,
            status=AgentTaskRunStatus.PENDING,
            trigger_source=trigger_source,
            input_json={
                "candidate_ids": [str(candidate.id) for candidate in selected],
                "source_urls": [candidate.source_url for candidate in selected],
                "source_selection_rule": "approved_pending_or_retry_only",
                "country": country,
                "city": city,
                "limit": limit,
                "risk_policy": {
                    "allowed_review_statuses": [status.value for status in sorted(self.ALLOWED_REVIEW_STATUSES)],
                    "allowed_extraction_statuses": [status.value for status in sorted(self.ALLOWED_EXTRACTION_STATUSES)],
                    "forbidden_blocked": True,
                    "high_requires_manual_approval": True,
                    "paused_channel_blocked": True,
                },
            },
            output_summary_json={
                "selected_count": len(selected),
                "blocked_count": len(blocked),
                "blocked_candidates": [
                    {
                        "candidate_id": str(item.candidate_id),
                        "risk_level": item.risk_level,
                        "review_status": item.review_status,
                        "extraction_status": item.extraction_status,
                        "block_reason": item.block_reason,
                    }
                    for item in blocked
                ],
            },
        )
        self.session.add(task_run)
        self.session.flush()
        return LeadExtractionSourceSelectionResult(
            task_run=task_run,
            selected_candidates=selected,
            blocked_candidates=blocked,
        )

    def _recover_orphaned_queued_sources(self, *, country: str | None, city: str | None) -> int:
        running_count = self.session.scalar(
            select(AgentTaskRun.id)
            .where(
                AgentTaskRun.task_type == AgentTaskType.LEAD_EXTRACTION,
                AgentTaskRun.status == AgentTaskRunStatus.RUNNING,
            )
            .limit(1)
        )
        if running_count is not None:
            return 0

        statement = select(LeadSourceCandidate).where(
            LeadSourceCandidate.extraction_status == LeadSourceCandidateExtractionStatus.QUEUED,
        )
        if country:
            statement = statement.where(LeadSourceCandidate.country == country)
        if city:
            statement = statement.where(LeadSourceCandidate.city == city)

        recovered = 0
        now = datetime.now(UTC)
        for candidate in self.session.scalars(statement).all():
            candidate.extraction_status = LeadSourceCandidateExtractionStatus.PENDING
            candidate.updated_at = now
            recovered += 1
        if recovered:
            self.session.flush()
        return recovered

    def run_queued_lead_extraction_task(self, task_run_id: str | UUID) -> dict[str, Any]:
        task_run = self.session.get(AgentTaskRun, UUID(str(task_run_id)))
        if task_run is None:
            raise ValueError("LEAD_EXTRACTION agent_task_run 不存在。")
        if task_run.task_type != AgentTaskType.LEAD_EXTRACTION:
            raise ValueError("agent_task_run 不是 LEAD_EXTRACTION 类型。")
        if task_run.status not in {AgentTaskRunStatus.PENDING, AgentTaskRunStatus.RETRY_PENDING}:
            raise ValueError("只有 pending 或 retry_pending 的 LEAD_EXTRACTION 任务可以执行。")

        task_payload = AgentTaskRunService.start(self._task_to_payload(task_run))
        self._apply_task_payload(task_run, task_payload)
        candidate_ids = [UUID(str(item)) for item in (task_run.input_json or {}).get("candidate_ids", [])]
        self._requeue_retry_candidates_for_task(task_run=task_run, candidate_ids=candidate_ids)
        processed: list[dict[str, Any]] = []
        succeeded_count = 0
        failed_count = 0
        skipped_count = 0
        retryable_failed_count = 0

        for candidate_id in candidate_ids:
            candidate = self.session.get(LeadSourceCandidate, candidate_id)
            if candidate is None:
                failed_count += 1
                processed.append(
                    {
                        "candidate_id": str(candidate_id),
                        "status": "failed",
                        "error": "来源候选不存在。",
                        "error_type": "schema_validation_error",
                    }
                )
                continue
            if candidate.extraction_status == LeadSourceCandidateExtractionStatus.SUCCEEDED:
                skipped_count += 1
                processed.append(
                    {
                        "candidate_id": str(candidate.id),
                        "status": "skipped",
                        "reason": "source_already_succeeded",
                    }
                )
                continue
            try:
                staging_lead = self._process_one_candidate(candidate, task_run=task_run)
            except ValueError as exc:
                failed_count += 1
                error_type = self._error_type_for_candidate_failure(str(exc))
                if self._candidate_failure_is_retryable(error_type):
                    retryable_failed_count += 1
                    candidate.extraction_status = LeadSourceCandidateExtractionStatus.RETRY
                else:
                    candidate.extraction_status = LeadSourceCandidateExtractionStatus.BLOCKED
                candidate.updated_at = datetime.now(UTC)
                processed.append(
                    {
                        "candidate_id": str(candidate.id),
                        "status": "failed",
                        "error": str(exc),
                        "error_type": error_type,
                    }
                )
                continue

            succeeded_count += 1
            candidate.extraction_status = LeadSourceCandidateExtractionStatus.SUCCEEDED
            candidate.last_extracted_at = datetime.now(UTC)
            candidate.updated_at = candidate.last_extracted_at
            processed.append(
                {
                    "candidate_id": str(candidate.id),
                    "status": "succeeded",
                    "staging_lead_id": str(staging_lead.id),
                }
            )

        summary = {
            "processed_count": len(processed),
            "succeeded_count": succeeded_count,
            "failed_count": failed_count,
            "retryable_failed_count": retryable_failed_count,
            "skipped_count": skipped_count,
            "processed_candidates": processed,
        }
        if failed_count:
            task_error_type = "timeout_error" if retryable_failed_count else "schema_validation_error"
            failed_payload = AgentTaskRunService.fail(
                self._task_to_payload(task_run),
                error_message="部分或全部来源抽取失败。",
                error={"type": task_error_type, "message": "部分或全部来源抽取失败。"},
            )
            failed_payload["output_summary_json"] = {
                **(failed_payload.get("output_summary_json") or {}),
                **summary,
            }
            self._apply_task_payload(task_run, failed_payload)
        else:
            succeeded_payload = AgentTaskRunService.succeed(self._task_to_payload(task_run), output_summary_json=summary)
            self._apply_task_payload(task_run, succeeded_payload)
        self.session.flush()
        return summary

    @staticmethod
    def _candidate_failure_is_retryable(error_type: str) -> bool:
        return error_type in {"network_error", "timeout_error", "rate_limit_error"}

    @staticmethod
    def _error_type_for_candidate_failure(message: str) -> str:
        normalized = message.lower()
        if any(term in normalized for term in ("timeout", "timed out", "network", "connection", "连接")):
            return "network_error"
        if any(term in normalized for term in ("rate limit", "429")):
            return "rate_limit_error"
        if any(
            term in normalized
            for term in (
                "登录墙",
                "验证码",
                "访问限制",
                "access",
                "captcha",
                "login",
                "forbidden",
                "high/forbidden",
                "风险阻断",
            )
        ):
            return "source_risk_exception"
        if any(term in normalized for term in ("不在公开文本中", "编造", "fabrication")):
            return "suspected_fabrication"
        if any(term in normalized for term in ("缺少来源证据", "evidence_refs", "来源证据")):
            return "schema_validation_error"
        return "schema_validation_error"

    def _requeue_retry_candidates_for_task(self, *, task_run: AgentTaskRun, candidate_ids: list[UUID]) -> None:
        if task_run.status != AgentTaskRunStatus.RUNNING:
            return
        for candidate_id in candidate_ids:
            candidate = self.session.get(LeadSourceCandidate, candidate_id)
            if candidate is None:
                continue
            if candidate.extraction_status == LeadSourceCandidateExtractionStatus.RETRY:
                candidate.extraction_status = LeadSourceCandidateExtractionStatus.QUEUED
                candidate.updated_at = datetime.now(UTC)
        self.session.flush()

    def _process_one_candidate(self, candidate: LeadSourceCandidate, *, task_run: AgentTaskRun):
        if candidate.extraction_status != LeadSourceCandidateExtractionStatus.QUEUED:
            raise ValueError("来源候选未处于 queued 状态，不能执行抽取。")
        if self._block_reason_for_execution(candidate) is not None:
            raise ValueError("来源候选不符合抽取执行准入条件。")

        candidate_url = self._ensure_candidate_url_bridge(candidate)
        public_text = self._read_public_text_for_candidate(candidate, candidate_url=candidate_url)
        extraction_result = self._generate_json(
            task_type="LEAD_EXTRACTION",
            system_prompt="你是海外车辆采购公开来源线索抽取助手。只能依据公开文本输出，不得编造。",
            user_prompt=f"来源URL：{candidate.source_url}\n公开文本：\n{public_text}",
            output_schema=self.LEAD_EXTRACTION_OUTPUT_SCHEMA,
        )
        if extraction_result.error:
            raise ValueError(extraction_result.error.get("message") or extraction_result.error.get("type") or "LLM 抽取失败。")
        if not isinstance(extraction_result.output_json, dict):
            raise ValueError("LLM 抽取输出不是 JSON object。")
        extraction_output = self._canonicalize_extraction_source_urls(
            extraction_result.output_json,
            source_url=candidate.source_url,
            public_text=public_text,
        )

        staging = self.extraction_service.run_extraction(
            candidate_url_id=candidate_url.id,
            llm_output_json=self._with_audit_defaults(
                extraction_output,
                model=extraction_result.model,
                prompt_version=LLMLeadExtractionService.PROMPT_VERSION,
            ),
            agent_task_run_id=task_run.id,
        ).staging_lead
        grading_result = self._generate_json(
            task_type="LEAD_GRADING",
            system_prompt="你是海外车辆采购线索分级助手。必须引用来源证据，Invalid 和 Watch 不得进入触达队列。",
            user_prompt=f"staging_lead_id：{staging.id}\n来源URL：{candidate.source_url}\n公开证据：{staging.source_evidence}",
            output_schema=self.LEAD_GRADING_OUTPUT_SCHEMA,
        )
        if grading_result.error:
            raise ValueError(grading_result.error.get("message") or grading_result.error.get("type") or "LLM 分级失败。")
        if not isinstance(grading_result.output_json, dict):
            raise ValueError("LLM 分级输出不是 JSON object。")
        grading_output = self._canonicalize_grading_source_urls(
            grading_result.output_json,
            source_url=candidate.source_url,
            source_evidence=staging.source_evidence,
        )
        self.grading_service.run_grading(
            staging_lead_id=staging.id,
            llm_output_json=self._with_audit_defaults(
                grading_output,
                model=grading_result.model,
                prompt_version=LLMLeadGradingService.PROMPT_VERSION,
            ),
            do_not_contact=False,
            agent_task_run_id=task_run.id,
        )
        return staging

    def _read_public_text_for_candidate(self, candidate: LeadSourceCandidate, *, candidate_url: CandidateUrl) -> str:
        page_read = self.public_page_read_service.read_candidate_page(candidate_url_id=candidate_url.id)
        snapshot = page_read.snapshot_result.page_snapshot
        if snapshot.read_status == PageSnapshotReadStatus.SUCCESS and (snapshot.text_excerpt or "").strip():
            return snapshot.text_excerpt.strip()
        if snapshot.read_status in {PageSnapshotReadStatus.BLOCKED, PageSnapshotReadStatus.NEEDS_MANUAL_REVIEW}:
            raise ValueError("公开页面读取遇到登录墙、验证码或访问限制，停止抽取。")

        fallback_text = self._public_text_for_candidate(candidate)
        self.raw_collection_service.create_page_snapshot(
            candidate_url_id=candidate_url.id,
            page_title=f"Lead source candidate {candidate.channel_name}",
            text_excerpt=fallback_text,
            evidence_note=f"公开页面读取失败，退回来源候选摘要：{candidate.source_url}",
            read_status=PageSnapshotReadStatus.SUCCESS,
            robots_or_policy_note="未登录；未绕过验证码；未规避反爬；仅使用来源发现阶段公开摘要。",
        )
        return fallback_text

    def _load_candidate_pool(
        self,
        *,
        country: str | None,
        city: str | None,
        limit: int,
    ) -> list[LeadSourceCandidate]:
        statement = select(LeadSourceCandidate)
        if country:
            statement = statement.where(LeadSourceCandidate.country == country)
        if city:
            statement = statement.where(LeadSourceCandidate.city == city)
        return list(
            self.session.scalars(
                statement.order_by(
                    case(
                        (
                            LeadSourceCandidate.extraction_status.in_(
                                [
                                    LeadSourceCandidateExtractionStatus.PENDING,
                                    LeadSourceCandidateExtractionStatus.RETRY,
                                ]
                            ),
                            0,
                        ),
                        else_=1,
                    ),
                    LeadSourceCandidate.created_at.asc(),
                    LeadSourceCandidate.id.asc(),
                ).limit(limit)
            ).all()
        )

    def _auto_approve_low_medium_sources(self, *, country: str | None, city: str | None) -> None:
        statement = select(LeadSourceCandidate).where(
            LeadSourceCandidate.risk_level.in_([ChannelRiskLevel.LOW, ChannelRiskLevel.MEDIUM]),
            LeadSourceCandidate.review_status.in_(
                [
                    LeadSourceCandidateReviewStatus.PENDING,
                    LeadSourceCandidateReviewStatus.NEEDS_RECHECK,
                    LeadSourceCandidateReviewStatus.AUTO_APPROVED,
                    LeadSourceCandidateReviewStatus.APPROVED,
                ]
            ),
            LeadSourceCandidate.extraction_status.in_(
                [
                    LeadSourceCandidateExtractionStatus.PENDING,
                    LeadSourceCandidateExtractionStatus.RETRY,
                ]
            ),
        )
        if country:
            statement = statement.where(LeadSourceCandidate.country == country)
        if city:
            statement = statement.where(LeadSourceCandidate.city == city)

        now = datetime.now(UTC)
        for candidate in self.session.scalars(statement).all():
            candidate.review_status = LeadSourceCandidateReviewStatus.AUTO_APPROVED
            candidate.approved_for_extraction = True
            candidate.updated_at = now

    def _block_reason(self, candidate: LeadSourceCandidate) -> str | None:
        if candidate.risk_level == ChannelRiskLevel.FORBIDDEN:
            return "forbidden_risk_blocked"
        if (
            candidate.risk_level == ChannelRiskLevel.HIGH
            and candidate.review_status != LeadSourceCandidateReviewStatus.APPROVED
        ):
            return "high_risk_requires_manual_approval"
        if candidate.review_status not in self.ALLOWED_REVIEW_STATUSES:
            return "review_status_not_approved"
        if not candidate.approved_for_extraction:
            return "not_approved_for_extraction"
        if candidate.extraction_status not in self.ALLOWED_EXTRACTION_STATUSES:
            return "extraction_status_not_pending_or_retry"
        if self._channel_is_paused_or_archived(candidate):
            return "channel_paused_or_archived"
        return None

    def _block_reason_for_execution(self, candidate: LeadSourceCandidate) -> str | None:
        if candidate.risk_level == ChannelRiskLevel.FORBIDDEN:
            return "forbidden_risk_blocked"
        if (
            candidate.risk_level == ChannelRiskLevel.HIGH
            and candidate.review_status != LeadSourceCandidateReviewStatus.APPROVED
        ):
            return "high_risk_requires_manual_approval"
        if candidate.review_status not in self.ALLOWED_REVIEW_STATUSES:
            return "review_status_not_approved"
        if not candidate.approved_for_extraction:
            return "not_approved_for_extraction"
        if self._channel_is_paused_or_archived(candidate):
            return "channel_paused_or_archived"
        return None

    def _channel_is_paused_or_archived(self, candidate: LeadSourceCandidate) -> bool:
        return self.session.scalar(
            select(ChannelPlan.id)
            .where(
                ChannelPlan.country == candidate.country,
                ChannelPlan.city == (candidate.city or ""),
                ChannelPlan.channel_name == candidate.channel_name,
                ChannelPlan.status.in_([ChannelPlanStatus.PAUSED, ChannelPlanStatus.ARCHIVED]),
            )
            .limit(1)
        ) is not None

    def _blocked(self, candidate: LeadSourceCandidate, block_reason: str) -> BlockedLeadExtractionSource:
        return BlockedLeadExtractionSource(
            candidate_id=candidate.id,
            risk_level=candidate.risk_level.value,
            review_status=candidate.review_status.value,
            extraction_status=candidate.extraction_status.value,
            block_reason=block_reason,
        )

    def _ensure_candidate_url_bridge(self, candidate: LeadSourceCandidate) -> CandidateUrl:
        task = self.raw_collection_service.create_collection_task(
            channel_name=f"lead_source_candidate:{candidate.channel_name}",
            task_type="lead_extraction_from_source_candidate",
            risk_level=candidate.risk_level,
            allowed_actions="公开页面文本读取；LLM 抽取；LLM 分级；写入 staging 和 audit。",
            forbidden_actions="不登录；不绕过验证码；不反爬规避；不自动私信；不自动加好友。",
            source_usage_type=SourceUsageType.PUBLIC_DISCOVERY_ONLY
            if candidate.risk_level == ChannelRiskLevel.HIGH
            else SourceUsageType.AUTOMATIC_COLLECTION,
            status=CollectionTaskStatus.RUNNING,
            max_sample_size=1,
        )
        return self.raw_collection_service.upsert_candidate_url(
            task_id=task.id,
            url=candidate.source_url,
            source_platform=candidate.platform,
            source_risk_level=candidate.risk_level,
            source_usage_type=task.source_usage_type,
            discovery_reason=candidate.discovery_reason,
            status=CandidateUrlStatus.STAGED,
        ).candidate_url

    def _public_text_for_candidate(self, candidate: LeadSourceCandidate) -> str:
        text = "\n".join(
            str(item)
            for item in [
                candidate.evidence_note,
                candidate.discovery_reason,
                *(candidate.evidence_links or []),
            ]
            if item
        )
        if PublicPageReadAgentService.contains_access_wall(text):
            raise ValueError("公开文本检测到登录墙、验证码或访问限制，停止抽取。")
        return text[: PublicPageReadAgentService.DEFAULT_TEXT_EXCERPT_LIMIT]

    def _generate_json(self, *, task_type: str, system_prompt: str, user_prompt: str, output_schema: dict[str, Any]):
        async def call():
            return await self.llm_client.generate_json(task_type, system_prompt, user_prompt, output_schema)

        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(call())

        return AgentThreadRunner.submit(name=f"{task_type.lower()}-llm-call", target=lambda: asyncio.run(call())).result()

    def _canonicalize_extraction_source_urls(
        self,
        output_json: dict[str, Any],
        *,
        source_url: str,
        public_text: str,
    ) -> dict[str, Any]:
        output = deepcopy(output_json)
        audit = output.setdefault("audit", {})
        reported_schema_version = output.get("schema_version")
        if reported_schema_version != "poc-ai-output-v1":
            audit["llm_reported_schema_version"] = reported_schema_version
            audit["schema_version_canonicalized"] = True
        output["schema_version"] = "poc-ai-output-v1"
        reported_task_type = output.get("task_type")
        if reported_task_type != "lead_extraction":
            audit["llm_reported_task_type"] = reported_task_type
            audit["task_type_canonicalized"] = True
        output["task_type"] = "lead_extraction"
        source = output.setdefault("source", {})
        reported_source_url = source.get("source_url")
        if reported_source_url and reported_source_url != source_url:
            audit["llm_reported_source_url"] = reported_source_url
        source["source_url"] = source_url

        reported_evidence_urls: list[str] = []
        for item in (output.get("lead") or {}).get("source_evidence") or []:
            if isinstance(item, dict):
                reported = item.get("source_url")
                if reported and reported != source_url:
                    reported_evidence_urls.append(str(reported))
                item["source_url"] = source_url
        if reported_evidence_urls:
            audit["llm_reported_evidence_source_urls"] = reported_evidence_urls
        self._add_fallback_source_evidence_if_missing(output, source_url=source_url, public_text=public_text)
        return output

    def _add_fallback_source_evidence_if_missing(
        self,
        output: dict[str, Any],
        *,
        source_url: str,
        public_text: str,
    ) -> None:
        lead = output.setdefault("lead", {})
        evidence_items = lead.get("source_evidence") or []
        if evidence_items:
            return

        evidence_text = (public_text or "").strip()
        if not evidence_text:
            return

        lead["source_evidence"] = [
            {
                "claim": "source_candidate_public_text",
                "evidence_text": evidence_text[:500],
                "source_url": source_url,
            }
        ]
        audit = output.setdefault("audit", {})
        audit["source_evidence_fallback_applied"] = True
        audit["source_evidence_fallback_reason"] = "llm_missing_source_evidence"

    def _canonicalize_grading_source_urls(
        self,
        output_json: dict[str, Any],
        *,
        source_url: str,
        source_evidence: str,
    ) -> dict[str, Any]:
        output = deepcopy(output_json)
        audit = output.setdefault("audit", {})
        reported_schema_version = output.get("schema_version")
        if reported_schema_version != "poc-ai-output-v1":
            audit["llm_reported_schema_version"] = reported_schema_version
            audit["schema_version_canonicalized"] = True
        output["schema_version"] = "poc-ai-output-v1"
        reported_task_type = output.get("task_type")
        if reported_task_type != "lead_grading":
            audit["llm_reported_task_type"] = reported_task_type
            audit["task_type_canonicalized"] = True
        output["task_type"] = "lead_grading"
        reported_urls: list[str] = []
        for item in output.get("evidence_refs") or []:
            if isinstance(item, dict):
                reported = item.get("source_url")
                if reported and reported != source_url:
                    reported_urls.append(str(reported))
                item["source_url"] = source_url
        if reported_urls:
            audit["llm_reported_evidence_ref_source_urls"] = reported_urls
        self._add_fallback_grading_evidence_refs_if_missing(
            output,
            source_url=source_url,
            source_evidence=source_evidence,
        )
        return output

    def _add_fallback_grading_evidence_refs_if_missing(
        self,
        output: dict[str, Any],
        *,
        source_url: str,
        source_evidence: str,
    ) -> None:
        evidence_refs = output.get("evidence_refs") or []
        if evidence_refs:
            return

        evidence_text = (source_evidence or "").strip()
        if not evidence_text:
            return

        output["evidence_refs"] = [
            {
                "claim": "staging_source_evidence",
                "evidence_text": evidence_text[:500],
                "source_url": source_url,
            }
        ]
        audit = output.setdefault("audit", {})
        audit["evidence_refs_fallback_applied"] = True
        audit["evidence_refs_fallback_reason"] = "llm_missing_evidence_refs"

    def _with_audit_defaults(self, output_json: dict[str, Any], *, model: str, prompt_version: str) -> dict[str, Any]:
        output = dict(output_json)
        audit = dict(output.get("audit") or {})
        audit.setdefault("model", model)
        audit.setdefault("prompt_version", prompt_version)
        audit.setdefault("input_saved", True)
        audit.setdefault("output_saved", True)
        output["audit"] = audit
        return output

    def _task_to_payload(self, task_run: AgentTaskRun) -> dict[str, Any]:
        return {
            "task_type": task_run.task_type,
            "status": task_run.status,
            "trigger_source": task_run.trigger_source,
            "input_json": task_run.input_json,
            "output_summary_json": task_run.output_summary_json,
            "llm_provider": task_run.llm_provider,
            "llm_model": task_run.llm_model,
            "prompt_template_id": task_run.prompt_template_id,
            "prompt_version": task_run.prompt_version,
            "token_usage_json": task_run.token_usage_json,
            "latency_ms": task_run.latency_ms,
            "error_message": task_run.error_message,
            "retry_count": task_run.retry_count,
            "started_at": task_run.started_at,
            "finished_at": task_run.finished_at,
            "created_at": task_run.created_at,
            "updated_at": task_run.updated_at,
        }

    def _apply_task_payload(self, task_run: AgentTaskRun, payload: dict[str, Any]) -> None:
        for key, value in payload.items():
            if hasattr(task_run, key):
                setattr(task_run, key, value)
