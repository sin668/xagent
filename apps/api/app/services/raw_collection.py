from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CandidateUrl, ChannelPlan, CollectionTask, PageSnapshot
from app.models.enums import (
    CandidateUrlStatus,
    ChannelPlanStatus,
    ChannelRiskLevel,
    CollectionTaskStatus,
    PageSnapshotReadStatus,
    SourcePlatform,
    SourceUsageType,
)


@dataclass(frozen=True)
class CandidateUrlUpsertResult:
    candidate_url: CandidateUrl
    created: bool


@dataclass(frozen=True)
class PageSnapshotUpsertResult:
    page_snapshot: PageSnapshot
    latest_for_candidate: PageSnapshot


@dataclass(frozen=True)
class CollectionTaskDefaults:
    source_usage_type: SourceUsageType
    max_sample_size: int | None


class RawCollectionService:
    HIGH_RISK_PUBLIC_DISCOVERY_TASK_TYPE = "high_risk_public_discovery"
    DEFAULT_HIGH_RISK_MAX_SAMPLE_SIZE = 20

    def __init__(self, session: Session) -> None:
        self.session = session

    @staticmethod
    def normalize_url(url: str) -> str:
        parsed = urlsplit(url.strip())
        scheme = (parsed.scheme or "https").lower()
        netloc = parsed.netloc.lower()
        path = parsed.path or "/"
        if path != "/":
            path = path.rstrip("/")
        query = urlencode(sorted(parse_qsl(parsed.query, keep_blank_values=True)), doseq=True)
        return urlunsplit((scheme, netloc, path, query, ""))

    @classmethod
    def hash_url(cls, url: str) -> str:
        normalized = cls.normalize_url(url)
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    @staticmethod
    def resolve_source_usage_type(
        *,
        risk_level: ChannelRiskLevel,
        requested_usage_type: str | SourceUsageType | None,
    ) -> SourceUsageType:
        if risk_level == ChannelRiskLevel.FORBIDDEN:
            raise ValueError("Forbidden 渠道不得创建可执行任务。")

        if requested_usage_type is None:
            return (
                SourceUsageType.PUBLIC_DISCOVERY_ONLY
                if risk_level == ChannelRiskLevel.HIGH
                else SourceUsageType.AUTOMATIC_COLLECTION
            )

        usage_type = SourceUsageType(requested_usage_type)
        if risk_level == ChannelRiskLevel.HIGH and usage_type != SourceUsageType.PUBLIC_DISCOVERY_ONLY:
            raise ValueError("High 风险渠道只能 public_discovery_only，不得进入自动采集或触达队列。")
        return usage_type

    @classmethod
    def resolve_task_defaults(
        cls,
        *,
        task_type: str,
        risk_level: str | ChannelRiskLevel,
        requested_usage_type: str | SourceUsageType | None,
        max_sample_size: int | None,
    ) -> CollectionTaskDefaults:
        risk = ChannelRiskLevel(risk_level)
        if task_type == cls.HIGH_RISK_PUBLIC_DISCOVERY_TASK_TYPE:
            if risk != ChannelRiskLevel.HIGH:
                raise ValueError("high_risk_public_discovery 必须使用 High 风险等级。")
            return CollectionTaskDefaults(
                source_usage_type=SourceUsageType.PUBLIC_DISCOVERY_ONLY,
                max_sample_size=max_sample_size or cls.DEFAULT_HIGH_RISK_MAX_SAMPLE_SIZE,
            )
        return CollectionTaskDefaults(
            source_usage_type=cls.resolve_source_usage_type(
                risk_level=risk,
                requested_usage_type=requested_usage_type,
            ),
            max_sample_size=max_sample_size,
        )

    @staticmethod
    def requires_secondary_verification(risk_level: ChannelRiskLevel) -> bool:
        return risk_level == ChannelRiskLevel.HIGH

    @staticmethod
    def default_queue_eligible(risk_level: ChannelRiskLevel | str) -> bool:
        return ChannelRiskLevel(risk_level) != ChannelRiskLevel.HIGH

    @staticmethod
    def validate_plan_allows_new_task(status: str | ChannelPlanStatus) -> None:
        if ChannelPlanStatus(status) in {ChannelPlanStatus.PAUSED, ChannelPlanStatus.ARCHIVED}:
            raise ValueError("暂停或归档渠道无法启动新任务。")

    @classmethod
    def task_status_after_snapshot(
        cls,
        *,
        task_type: str,
        risk_level: str | ChannelRiskLevel,
        read_status: str | PageSnapshotReadStatus,
    ) -> CollectionTaskStatus | None:
        normalized_status = cls.normalize_read_status(read_status)
        if (
            task_type == cls.HIGH_RISK_PUBLIC_DISCOVERY_TASK_TYPE
            and ChannelRiskLevel(risk_level) == ChannelRiskLevel.HIGH
            and normalized_status == PageSnapshotReadStatus.NEEDS_MANUAL_REVIEW
        ):
            return CollectionTaskStatus.BLOCKED
        return None

    @staticmethod
    def validate_candidate_task_id(task_id: UUID | str | None) -> None:
        if task_id is None or str(task_id).strip() == "":
            raise ValueError("candidate URL 必须关联 task_id。")

    @staticmethod
    def validate_candidate_url_id(candidate_url_id: UUID | str | None) -> None:
        if candidate_url_id is None or str(candidate_url_id).strip() == "":
            raise ValueError("page snapshot 必须关联 candidate_url_id。")

    @staticmethod
    def normalize_evidence_note(evidence_note: str | None) -> str:
        return (evidence_note or "").strip()

    @staticmethod
    def normalize_read_status(read_status: str | PageSnapshotReadStatus) -> PageSnapshotReadStatus:
        status = str(read_status).strip()
        if status in {"captcha", "login_wall", "access_error", "policy_wall"}:
            return PageSnapshotReadStatus.NEEDS_MANUAL_REVIEW
        return PageSnapshotReadStatus(status)

    def create_collection_task(
        self,
        *,
        channel_name: str,
        task_type: str,
        risk_level: str | ChannelRiskLevel,
        allowed_actions: str,
        forbidden_actions: str,
        source_usage_type: str | SourceUsageType | None = None,
        plan_id: UUID | None = None,
        status: str | CollectionTaskStatus | None = None,
        max_sample_size: int | None = None,
    ) -> CollectionTask:
        risk = ChannelRiskLevel(risk_level)
        if plan_id is not None:
            plan = self.session.get(ChannelPlan, plan_id)
            if plan is None:
                raise ValueError("collection task 关联的 channel_plan 不存在。")
            self.validate_plan_allows_new_task(plan.status)
        defaults = self.resolve_task_defaults(
            task_type=task_type,
            risk_level=risk,
            requested_usage_type=source_usage_type,
            max_sample_size=max_sample_size,
        )
        task_status = CollectionTaskStatus(status) if status is not None else CollectionTaskStatus.PENDING
        task = CollectionTask(
            plan_id=plan_id,
            task_type=task_type,
            channel_name=channel_name,
            risk_level=risk,
            source_usage_type=defaults.source_usage_type,
            max_sample_size=defaults.max_sample_size,
            allowed_actions=allowed_actions,
            forbidden_actions=forbidden_actions,
            status=task_status,
            created_at=datetime.utcnow(),
        )
        self.session.add(task)
        self.session.flush()
        return task

    def list_collection_tasks(self, *, limit: int = 100) -> list[CollectionTask]:
        return list(
            self.session.scalars(
                select(CollectionTask).order_by(CollectionTask.created_at.desc()).limit(limit)
            ).all()
        )

    def upsert_candidate_url(
        self,
        *,
        task_id: UUID | str | None,
        url: str,
        source_platform: str | SourcePlatform,
        source_risk_level: str | ChannelRiskLevel,
        source_usage_type: str | SourceUsageType | None,
        discovery_reason: str,
        status: str | CandidateUrlStatus | None = None,
    ) -> CandidateUrlUpsertResult:
        self.validate_candidate_task_id(task_id)
        risk = ChannelRiskLevel(source_risk_level)
        usage = self.resolve_source_usage_type(risk_level=risk, requested_usage_type=source_usage_type)
        url_hash = self.hash_url(url)
        existing = self.session.scalar(select(CandidateUrl).where(CandidateUrl.url_hash == url_hash))
        candidate_status = CandidateUrlStatus(status) if status is not None else CandidateUrlStatus.NEW

        if existing is not None:
            existing.discovery_reason = discovery_reason
            existing.source_platform = SourcePlatform(source_platform)
            existing.source_risk_level = risk
            existing.source_usage_type = usage
            existing.requires_secondary_verification = self.requires_secondary_verification(risk)
            existing.queue_eligible = self.default_queue_eligible(risk)
            existing.status = candidate_status
            existing.updated_at = datetime.utcnow()
            self.session.flush()
            return CandidateUrlUpsertResult(existing, False)

        candidate = CandidateUrl(
            task_id=UUID(str(task_id)),
            url=self.normalize_url(url),
            url_hash=url_hash,
            source_platform=SourcePlatform(source_platform),
            source_risk_level=risk,
            source_usage_type=usage,
            requires_secondary_verification=self.requires_secondary_verification(risk),
            queue_eligible=self.default_queue_eligible(risk),
            discovery_reason=discovery_reason,
            status=candidate_status,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        self.session.add(candidate)
        self.session.flush()
        return CandidateUrlUpsertResult(candidate, True)

    def list_candidate_urls(self, *, task_id: UUID | None = None, limit: int = 100) -> list[CandidateUrl]:
        statement = select(CandidateUrl).order_by(CandidateUrl.created_at.desc()).limit(limit)
        if task_id is not None:
            statement = statement.where(CandidateUrl.task_id == task_id)
        return list(self.session.scalars(statement).all())

    def create_page_snapshot(
        self,
        *,
        candidate_url_id: UUID | str | None,
        page_title: str | None,
        text_excerpt: str | None,
        evidence_note: str | None,
        read_status: str | PageSnapshotReadStatus,
        robots_or_policy_note: str | None = None,
        captured_at: datetime | None = None,
    ) -> PageSnapshotUpsertResult:
        self.validate_candidate_url_id(candidate_url_id)
        snapshot = PageSnapshot(
            candidate_url_id=UUID(str(candidate_url_id)),
            page_title=page_title,
            text_excerpt=text_excerpt,
            evidence_note=self.normalize_evidence_note(evidence_note),
            read_status=self.normalize_read_status(read_status),
            robots_or_policy_note=robots_or_policy_note,
            captured_at=captured_at or datetime.utcnow(),
            created_at=datetime.utcnow(),
        )
        self.session.add(snapshot)
        candidate = self.session.get(CandidateUrl, UUID(str(candidate_url_id)))
        if candidate is not None and candidate.task is not None:
            next_status = self.task_status_after_snapshot(
                task_type=candidate.task.task_type,
                risk_level=candidate.task.risk_level,
                read_status=read_status,
            )
            if next_status is not None:
                candidate.task.status = next_status
                candidate.task.error_message = "High 风险公开发现遇到验证码、登录墙或访问策略墙，任务已阻断。"
                candidate.task.finished_at = datetime.utcnow()
        self.session.flush()
        return PageSnapshotUpsertResult(snapshot, self.latest_page_snapshot_for_candidate(UUID(str(candidate_url_id))))

    def latest_page_snapshot_for_candidate(self, candidate_url_id: UUID) -> PageSnapshot:
        statement = (
            select(PageSnapshot)
            .where(PageSnapshot.candidate_url_id == candidate_url_id)
            .order_by(PageSnapshot.captured_at.desc(), PageSnapshot.created_at.desc())
            .limit(1)
        )
        snapshot = self.session.scalar(statement)
        if snapshot is None:
            raise ValueError("candidate URL 尚未保存 page snapshot。")
        return snapshot

    def list_page_snapshots(self, *, candidate_url_id: UUID | None = None, limit: int = 100) -> list[PageSnapshot]:
        statement = select(PageSnapshot).order_by(PageSnapshot.captured_at.desc()).limit(limit)
        if candidate_url_id is not None:
            statement = statement.where(PageSnapshot.candidate_url_id == candidate_url_id)
        return list(self.session.scalars(statement).all())
