from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlsplit
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, defer

from app.models.agent_task_run import AgentTaskRun
from app.models.enums import (
    AgentTaskRunStatus,
    AgentTaskType,
    ChannelRiskLevel,
    LeadSourceCandidateExtractionStatus,
    LeadSourceCandidateReviewStatus,
    SourcePlatform,
)
from app.models.lead_source_candidate import LeadSourceCandidate
from app.services.lead_source_candidate_rules import LeadSourceCandidateRules
from app.services.source_discovery_schema import SourceDiscoverySchemaService


@dataclass(frozen=True)
class LeadSourceCandidateUpsertResult:
    candidate: LeadSourceCandidate
    created: bool
    duplicate: bool


@dataclass(frozen=True)
class LeadSourceCandidateBatchResult:
    items: list[LeadSourceCandidateUpsertResult]

    @property
    def created_count(self) -> int:
        return sum(1 for item in self.items if item.created)

    @property
    def updated_count(self) -> int:
        return sum(1 for item in self.items if not item.created)

    @property
    def duplicate_count(self) -> int:
        return sum(1 for item in self.items if item.duplicate)

    @property
    def blocked_count(self) -> int:
        return sum(1 for item in self.items if item.candidate.risk_level == ChannelRiskLevel.FORBIDDEN)


@dataclass(frozen=True)
class LeadSourceCandidateReviewResult:
    candidate: LeadSourceCandidate
    audit_task_run: AgentTaskRun


class LeadSourceCandidateService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_candidates(
        self,
        *,
        risk_level: ChannelRiskLevel | None = None,
        review_status: LeadSourceCandidateReviewStatus | None = None,
        country: str | None = None,
        city: str | None = None,
        platform: SourcePlatform | None = None,
        channel_name: str | None = None,
        extraction_status: LeadSourceCandidateExtractionStatus | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[LeadSourceCandidate], int]:
        filters = self._candidate_filters(
            risk_level=risk_level,
            review_status=review_status,
            country=country,
            city=city,
            platform=platform,
            channel_name=channel_name,
            extraction_status=extraction_status,
        )
        total = self.session.scalar(select(func.count()).select_from(LeadSourceCandidate).where(*filters)) or 0
        items = self.session.scalars(
            select(LeadSourceCandidate)
            .options(defer(LeadSourceCandidate.llm_output_json))
            .where(*filters)
            .order_by(LeadSourceCandidate.created_at.desc(), LeadSourceCandidate.id.desc())
            .limit(limit)
            .offset(offset)
        ).all()
        return list(items), total

    def get_candidate(self, candidate_id: UUID) -> LeadSourceCandidate | None:
        return self.session.get(LeadSourceCandidate, candidate_id)

    def apply_review_action(
        self,
        candidate_id: UUID,
        *,
        action: str,
        reviewer_id: str,
        review_note: str,
    ) -> LeadSourceCandidateReviewResult:
        candidate = self.get_candidate(candidate_id)
        if candidate is None:
            raise ValueError("来源候选不存在。")

        now = datetime.now(UTC)
        if action == "approve_for_extraction":
            if candidate.risk_level == ChannelRiskLevel.FORBIDDEN:
                candidate.review_status = LeadSourceCandidateReviewStatus.REJECTED
                candidate.approved_for_extraction = False
                candidate.extraction_status = LeadSourceCandidateExtractionStatus.BLOCKED
                candidate.reviewer_id = reviewer_id
                candidate.review_note = review_note
                candidate.reviewed_at = now
                self._create_review_audit(
                    candidate,
                    action=action,
                    reviewer_id=reviewer_id,
                    review_note=review_note,
                    now=now,
                    status=AgentTaskRunStatus.FAILED,
                    error_message="Forbidden 来源不得 approve_for_extraction。",
                )
                self.session.flush()
                raise ValueError("Forbidden 来源不得 approve_for_extraction。")
            candidate.review_status = LeadSourceCandidateReviewStatus.APPROVED
            candidate.approved_for_extraction = True
            candidate.extraction_status = LeadSourceCandidateExtractionStatus.PENDING
        elif action == "reject":
            candidate.review_status = LeadSourceCandidateReviewStatus.REJECTED
            candidate.approved_for_extraction = False
            candidate.extraction_status = LeadSourceCandidateExtractionStatus.BLOCKED
        elif action == "mark_high_risk":
            candidate.risk_level = ChannelRiskLevel.HIGH
            candidate.review_status = LeadSourceCandidateReviewStatus.HIGH_RISK_REVIEW
            candidate.approved_for_extraction = False
            candidate.extraction_status = LeadSourceCandidateExtractionStatus.PENDING
        elif action == "pause_channel":
            candidate.review_status = LeadSourceCandidateReviewStatus.PAUSED
            candidate.approved_for_extraction = False
            candidate.extraction_status = LeadSourceCandidateExtractionStatus.BLOCKED
        elif action == "add_review_note":
            pass
        else:
            raise ValueError(f"不支持的来源审核动作：{action}")

        candidate.reviewer_id = reviewer_id
        candidate.review_note = review_note
        candidate.reviewed_at = now

        audit = self._create_review_audit(
            candidate,
            action=action,
            reviewer_id=reviewer_id,
            review_note=review_note,
            now=now,
            status=AgentTaskRunStatus.SUCCEEDED,
        )
        self.session.flush()
        return LeadSourceCandidateReviewResult(candidate=candidate, audit_task_run=audit)

    def upsert_from_source_discovery_output(
        self,
        output: dict[str, Any],
        *,
        created_by_task_run_id: str | UUID | None = None,
        llm_provider: str | None = None,
        llm_model: str | None = None,
        llm_output_json: dict[str, Any] | None = None,
    ) -> LeadSourceCandidateBatchResult:
        validated = SourceDiscoverySchemaService.validate_output(output)
        items: list[LeadSourceCandidateUpsertResult] = []

        for candidate in validated.candidates:
            items.append(
                self.upsert_candidate(
                    candidate,
                    created_by_task_run_id=created_by_task_run_id,
                    llm_provider=llm_provider,
                    llm_model=llm_model,
                    llm_output_json=llm_output_json,
                )
            )
        for blocked in validated.blocked_candidates:
            items.append(
                self.upsert_candidate(
                    self._blocked_to_candidate_payload(blocked, validated.normalized_output),
                    created_by_task_run_id=created_by_task_run_id,
                    llm_provider=llm_provider,
                    llm_model=llm_model,
                    llm_output_json=llm_output_json,
                )
            )

        return LeadSourceCandidateBatchResult(items=items)

    def upsert_candidate(
        self,
        candidate: dict[str, Any],
        *,
        created_by_task_run_id: str | UUID | None = None,
        llm_provider: str | None = None,
        llm_model: str | None = None,
        llm_output_json: dict[str, Any] | None = None,
    ) -> LeadSourceCandidateUpsertResult:
        source_url = str(candidate["source_url"]).strip()
        platform = self._resolve_platform(candidate.get("platform"))
        normalized_domain = self._normalized_domain(source_url)
        risk_level = ChannelRiskLevel(candidate["risk_level"])
        defaults = LeadSourceCandidateRules.resolve_defaults(risk_level)
        dedupe_key = LeadSourceCandidateRules.build_dedupe_key(
            source_url=source_url,
            normalized_domain=normalized_domain,
            platform=platform,
        )

        existing = self.session.scalar(
            select(LeadSourceCandidate).where(LeadSourceCandidate.dedupe_key == dedupe_key)
        )
        duplicate_of = None if existing is not None else self._find_domain_duplicate(normalized_domain, platform)

        if existing is not None:
            record = existing
            created = False
        else:
            record = LeadSourceCandidate(dedupe_key=dedupe_key)
            self.session.add(record)
            created = True

        record.source_url = source_url
        record.normalized_domain = normalized_domain
        record.platform = platform
        record.channel_name = str(candidate.get("channel_name") or "Unknown")
        record.country = str(candidate.get("country") or "Unknown")
        record.city = candidate.get("city")
        record.risk_level = risk_level
        record.review_status = defaults.review_status
        record.approved_for_extraction = defaults.approved_for_extraction
        record.discovery_method = str(candidate.get("discovery_method") or "Unknown")
        record.discovery_query = candidate.get("discovery_query")
        record.discovery_reason = str(candidate.get("discovery_reason") or "Unknown")
        record.evidence_note = str(candidate.get("evidence_note") or "Unknown")
        record.evidence_links = list(candidate.get("evidence_links") or [source_url])
        record.llm_provider = llm_provider
        record.llm_model = llm_model
        record.llm_output_json = llm_output_json
        record.confidence_score = candidate.get("confidence_score")
        record.extraction_status = defaults.extraction_status
        record.retry_count = record.retry_count or 0
        record.created_by_task_run_id = self._uuid_or_none(created_by_task_run_id)

        if duplicate_of is not None:
            record.is_duplicate = True
            record.duplicate_of_id = duplicate_of.id
        elif record.duplicate_of_id is None:
            record.is_duplicate = False

        return LeadSourceCandidateUpsertResult(candidate=record, created=created, duplicate=record.is_duplicate)

    def _create_review_audit(
        self,
        candidate: LeadSourceCandidate,
        *,
        action: str,
        reviewer_id: str,
        review_note: str,
        now: datetime,
        status: AgentTaskRunStatus,
        error_message: str | None = None,
    ) -> AgentTaskRun:
        audit = AgentTaskRun(
            task_type=AgentTaskType.SOURCE_DISCOVERY,
            status=status,
            trigger_source="lead_source_review_api",
            input_json={
                "candidate_id": str(candidate.id),
                "action": action,
                "reviewer_id": reviewer_id,
                "review_note": review_note,
            },
            output_summary_json={
                "candidate_id": str(candidate.id),
                "risk_level": candidate.risk_level.value,
                "review_status": candidate.review_status.value,
                "approved_for_extraction": candidate.approved_for_extraction,
                "extraction_status": candidate.extraction_status.value,
            },
            error_message=error_message,
            started_at=now,
            finished_at=now,
        )
        self.session.add(audit)
        return audit

    def _find_domain_duplicate(self, normalized_domain: str, platform: SourcePlatform) -> LeadSourceCandidate | None:
        return self.session.scalar(
            select(LeadSourceCandidate)
            .where(
                LeadSourceCandidate.normalized_domain == normalized_domain,
                LeadSourceCandidate.platform == platform,
                LeadSourceCandidate.is_duplicate.is_(False),
            )
            .order_by(LeadSourceCandidate.created_at)
        )

    def _candidate_filters(
        self,
        *,
        risk_level: ChannelRiskLevel | None,
        review_status: LeadSourceCandidateReviewStatus | None,
        country: str | None,
        city: str | None,
        platform: SourcePlatform | None,
        channel_name: str | None,
        extraction_status: LeadSourceCandidateExtractionStatus | None,
    ) -> list:
        filters = []
        if risk_level is not None:
            filters.append(LeadSourceCandidate.risk_level == risk_level)
        if review_status is not None:
            filters.append(LeadSourceCandidate.review_status == review_status)
        if country:
            filters.append(LeadSourceCandidate.country == country)
        if city:
            filters.append(LeadSourceCandidate.city == city)
        if platform is not None:
            filters.append(LeadSourceCandidate.platform == platform)
        if channel_name:
            filters.append(LeadSourceCandidate.channel_name == channel_name)
        if extraction_status is not None:
            filters.append(LeadSourceCandidate.extraction_status == extraction_status)
        return filters

    def _blocked_to_candidate_payload(self, blocked: dict[str, Any], output: dict[str, Any]) -> dict[str, Any]:
        return {
            "source_url": blocked["source_url"],
            "platform": blocked.get("platform") or "other",
            "channel_name": blocked.get("channel_name") or "blocked_candidate",
            "country": output.get("country") or "Unknown",
            "city": output.get("city"),
            "risk_level": blocked["risk_level"],
            "discovery_method": "source_discovery_blocked",
            "discovery_query": None,
            "discovery_reason": blocked.get("blocked_reason") or "来源被风险规则阻断。",
            "evidence_note": blocked.get("blocked_reason") or "来源被风险规则阻断。",
            "evidence_links": [blocked["source_url"]],
            "confidence_score": None,
        }

    def _normalized_domain(self, source_url: str) -> str:
        parsed = urlsplit(source_url.strip())
        return (parsed.netloc or parsed.path.split("/")[0]).lower()

    def _resolve_platform(self, value: Any) -> SourcePlatform:
        try:
            return SourcePlatform(str(value or "other"))
        except ValueError:
            return SourcePlatform.OTHER

    def _uuid_or_none(self, value: str | UUID | None) -> UUID | None:
        if value is None:
            return None
        if isinstance(value, UUID):
            return value
        return UUID(str(value))
