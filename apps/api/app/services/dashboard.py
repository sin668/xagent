from dataclasses import dataclass
from datetime import date, datetime, time

from sqlalchemy import false, select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    AIAuditLog,
    CandidateUrl,
    ChannelPlan,
    ChannelRiskRule,
    ComplianceReview,
    Customer,
    LeadSource,
    OutreachRecord,
    RiskEvent,
    RoiCostEntry,
    StagingLead,
)
from app.models.enums import (
    ChannelRiskLevel,
    ChannelPlanStatus,
    ComplianceReviewStatus,
    ContactMethodType,
    CustomerGrade,
    CustomerStatus,
    OutreachStatus,
    RiskEventSeverity,
    RiskEventStatus,
    SourcePlatform,
    StagingReviewStatus,
)


DISPLAY_NAMES = {
    SourcePlatform.OFFICIAL_WEBSITE.value: "官网/公开目录",
    SourcePlatform.PUBLIC_DIRECTORY.value: "公开目录",
    SourcePlatform.SEARCH_ENGINE.value: "搜索引擎",
    SourcePlatform.GOOGLE_MAPS.value: "Google 地图",
    SourcePlatform.YANDEX_MAPS.value: "Yandex 地图",
    SourcePlatform.YOUTUBE.value: "YouTube",
    SourcePlatform.DROM.value: "Drom",
    SourcePlatform.OTHER.value: "其他公开来源",
    "vkontakte": "VK",
    "facebook": "Facebook/Instagram",
}

SLA_HOURS = {
    CustomerGrade.B: 48,
    CustomerGrade.C: 24,
}

OUTREACH_SENT_STATUSES = {
    OutreachStatus.SENT,
    OutreachStatus.REPLIED,
    OutreachStatus.REJECTED,
    OutreachStatus.NO_RESPONSE,
    OutreachStatus.BAD_CONTACT,
}

OUTREACH_PENDING_STATUSES = {
    CustomerStatus.READY_FOR_CUSTOMER_SERVICE,
    CustomerStatus.CUSTOMER_SERVICE_FOLLOWING,
    CustomerStatus.READY_FOR_SALES,
    CustomerStatus.SALES_FOLLOWING,
}

ROI_COMPLIANCE_GUARDRAIL = "ROI 不能作为绕过合规限制的理由；High/Forbidden、勿扰和 C 级报价前合规复核规则仍必须优先。"

OPERATIONS_QUEUE_STATUSES = {CustomerStatus.PENDING_REVIEW}
CUSTOMER_SERVICE_QUEUE_STATUSES = {
    CustomerStatus.READY_FOR_CUSTOMER_SERVICE,
    CustomerStatus.CUSTOMER_SERVICE_FOLLOWING,
}
SALES_QUEUE_STATUSES = {
    CustomerStatus.READY_FOR_SALES,
    CustomerStatus.SALES_FOLLOWING,
}
PHASE_ONE_DAILY_CANDIDATE_TARGET = 100
PHASE_ONE_VALID_GRADES = {CustomerGrade.B, CustomerGrade.C}
PHASE_ONE_READONLY_RISKS = {ChannelRiskLevel.HIGH.value, ChannelRiskLevel.FORBIDDEN.value}
RISK_EVENT_SEVERITY_ORDER = {
    "critical": 0,
    "high": 1,
    "medium": 2,
    "low": 3,
}
RISK_EVENT_STATUS_ORDER = {
    "open": 0,
    "investigating": 1,
    "resolved": 2,
    "dismissed": 3,
}


@dataclass
class ChannelMetric:
    channel_name: str
    display_name: str
    risk_level: str
    risk_status: str
    investment_recommendation: str
    candidate_count: int = 0
    b_grade_count: int = 0
    c_grade_count: int = 0
    invalid_count: int = 0

    @property
    def bc_grade_count(self) -> int:
        return self.b_grade_count + self.c_grade_count

    @property
    def invalid_rate(self) -> float:
        if self.candidate_count == 0:
            return 0.0
        return self.invalid_count / self.candidate_count


def parse_date_boundary(value: str | date | None, *, end_of_day: bool = False) -> datetime | None:
    if not value:
        return None
    parsed = value if isinstance(value, date) else date.fromisoformat(value)
    return datetime.combine(parsed, time.max if end_of_day else time.min)


def risk_status_for(risk_level: str) -> str:
    if risk_level == ChannelRiskLevel.FORBIDDEN.value:
        return "blocked"
    if risk_level == ChannelRiskLevel.HIGH.value:
        return "researching"
    return "active"


def recommendation_for(risk_level: str, bc_grade_count: int) -> str:
    if risk_level in {ChannelRiskLevel.HIGH.value, ChannelRiskLevel.FORBIDDEN.value}:
        return "blocked"
    return "candidate" if bc_grade_count > 0 else "watch"


def enum_value(value) -> str:
    return value.value if hasattr(value, "value") else str(value)


def record_day(value: datetime) -> str:
    return value.date().isoformat()


def within_date_range(value: datetime, *, start: datetime | None, end: datetime | None) -> bool:
    if start is not None and value < start:
        return False
    if end is not None and value > end:
        return False
    return True


def source_matches(*, channel_name: str, risk_level: str, channel: str | None, risk_filter: str | None) -> bool:
    if channel and channel_name != channel:
        return False
    if risk_filter and risk_level != risk_filter:
        return False
    return True


def source_platform_filter_value(channel: str | None) -> SourcePlatform | None:
    if not channel:
        return None
    try:
        return SourcePlatform(channel)
    except ValueError:
        return None


class DashboardService:
    def __init__(self, session: Session) -> None:
        self.session = session

    @staticmethod
    def _empty_funnel_bucket(date_label: str | None = None, channel_name: str | None = None, risk_level: str | None = None) -> dict:
        bucket = {
            "candidate_url_count": 0,
            "staging_lead_count": 0,
            "core_customer_ids": set(),
            "core_valid_ids": set(),
            "touchable_effective_ids": set(),
            "high_readonly_excluded_ids": set(),
            "do_not_contact_excluded_ids": set(),
        }
        if date_label is not None:
            bucket["date"] = date_label
        if channel_name is not None:
            bucket["channel_name"] = channel_name
            bucket["display_name"] = DISPLAY_NAMES.get(channel_name, channel_name)
        if risk_level is not None:
            bucket["risk_level"] = risk_level
        return bucket

    @staticmethod
    def _serialize_funnel_bucket(bucket: dict, *, daily_candidate_target: int | None = None) -> dict:
        candidate_count = bucket["candidate_url_count"]
        result = {
            key: bucket[key]
            for key in ("date", "channel_name", "display_name", "risk_level")
            if key in bucket
        }
        result.update(
            {
                "candidate_url_count": candidate_count,
                "staging_lead_count": bucket["staging_lead_count"],
                "core_customer_count": len(bucket["core_customer_ids"]),
                "core_valid_lead_count": len(bucket["core_valid_ids"]),
                "touchable_effective_lead_count": len(bucket["touchable_effective_ids"]),
                "high_readonly_excluded_count": len(bucket["high_readonly_excluded_ids"]),
                "do_not_contact_excluded_count": len(bucket["do_not_contact_excluded_ids"]),
            }
        )
        if daily_candidate_target is not None:
            result["daily_candidate_target"] = daily_candidate_target
            result["candidate_target_completion_rate"] = (
                round(candidate_count / daily_candidate_target, 4) if daily_candidate_target else 0.0
            )
            result["candidate_target_met"] = candidate_count >= daily_candidate_target
        return result

    @classmethod
    def _add_core_customer_to_bucket(cls, bucket: dict, *, customer, risk_level: str) -> None:
        customer_id = str(customer.id)
        grade = customer.grade if isinstance(customer.grade, CustomerGrade) else CustomerGrade(customer.grade)
        bucket["core_customer_ids"].add(customer_id)
        if grade not in PHASE_ONE_VALID_GRADES:
            return
        bucket["core_valid_ids"].add(customer_id)
        if risk_level in PHASE_ONE_READONLY_RISKS:
            bucket["high_readonly_excluded_ids"].add(customer_id)
            return
        if bool(getattr(customer, "do_not_contact", False)):
            bucket["do_not_contact_excluded_ids"].add(customer_id)
            return
        bucket["touchable_effective_ids"].add(customer_id)

    @classmethod
    def phase_one_funnel_from_records(
        cls,
        *,
        candidates: list,
        staging_leads: list,
        core_sources: list[tuple],
        date_from: str | date | None = None,
        date_to: str | date | None = None,
        channel: str | None = None,
        risk_level: str | None = None,
        daily_candidate_target: int = PHASE_ONE_DAILY_CANDIDATE_TARGET,
    ) -> dict[str, object]:
        start = parse_date_boundary(date_from)
        end = parse_date_boundary(date_to, end_of_day=True)
        daily: dict[str, dict] = {}
        channels: dict[tuple[str, str], dict] = {}
        summary = cls._empty_funnel_bucket()

        def daily_bucket(date_label: str) -> dict:
            return daily.setdefault(date_label, cls._empty_funnel_bucket(date_label=date_label))

        def channel_bucket(channel_name: str, item_risk_level: str) -> dict:
            return channels.setdefault(
                (channel_name, item_risk_level),
                cls._empty_funnel_bucket(channel_name=channel_name, risk_level=item_risk_level),
            )

        for candidate in candidates:
            created_at = candidate.created_at
            channel_name = enum_value(candidate.source_platform)
            candidate_risk = enum_value(candidate.source_risk_level)
            if not within_date_range(created_at, start=start, end=end):
                continue
            if not source_matches(channel_name=channel_name, risk_level=candidate_risk, channel=channel, risk_filter=risk_level):
                continue
            for bucket in (summary, daily_bucket(record_day(created_at)), channel_bucket(channel_name, candidate_risk)):
                bucket["candidate_url_count"] += 1

        for lead in staging_leads:
            created_at = lead.created_at
            candidate = getattr(lead, "candidate_url", None)
            channel_name = enum_value(getattr(candidate, "source_platform", "unknown"))
            lead_risk = enum_value(getattr(candidate, "source_risk_level", "Unknown"))
            if not within_date_range(created_at, start=start, end=end):
                continue
            if not source_matches(channel_name=channel_name, risk_level=lead_risk, channel=channel, risk_filter=risk_level):
                continue
            for bucket in (summary, daily_bucket(record_day(created_at)), channel_bucket(channel_name, lead_risk)):
                bucket["staging_lead_count"] += 1

        for customer, source in core_sources:
            collected_at = getattr(source, "collected_at", None) or getattr(customer, "created_at")
            channel_name = enum_value(source.platform)
            source_risk = enum_value(source.channel_risk_level)
            if not within_date_range(collected_at, start=start, end=end):
                continue
            if not source_matches(channel_name=channel_name, risk_level=source_risk, channel=channel, risk_filter=risk_level):
                continue
            for bucket in (summary, daily_bucket(record_day(collected_at)), channel_bucket(channel_name, source_risk)):
                cls._add_core_customer_to_bucket(bucket, customer=customer, risk_level=source_risk)

        serialized_daily = [
            cls._serialize_funnel_bucket(bucket, daily_candidate_target=daily_candidate_target)
            for _date, bucket in sorted(daily.items())
        ]
        serialized_channels = [
            cls._serialize_funnel_bucket(bucket)
            for _key, bucket in sorted(channels.items(), key=lambda item: (item[0][0], item[0][1]))
        ]

        return {
            "summary": cls._serialize_funnel_bucket(summary, daily_candidate_target=daily_candidate_target),
            "daily": serialized_daily,
            "channels": serialized_channels,
            "filters": {
                "date_from": date_from.isoformat() if isinstance(date_from, date) else date_from,
                "date_to": date_to.isoformat() if isinstance(date_to, date) else date_to,
                "channel": channel,
                "risk_level": risk_level,
            },
            "guardrail": "High/Forbidden 只读或政策研究结果不得计入可触达有效线索。",
        }

    def phase_one_funnel_metrics(
        self,
        *,
        date_from: str | date | None = None,
        date_to: str | date | None = None,
        channel: str | None = None,
        risk_level: str | None = None,
        daily_candidate_target: int = PHASE_ONE_DAILY_CANDIDATE_TARGET,
    ) -> dict[str, object]:
        start = parse_date_boundary(date_from)
        end = parse_date_boundary(date_to, end_of_day=True)

        candidate_query = select(CandidateUrl)
        if start is not None:
            candidate_query = candidate_query.where(CandidateUrl.created_at >= start)
        if end is not None:
            candidate_query = candidate_query.where(CandidateUrl.created_at <= end)
        if channel:
            platform = source_platform_filter_value(channel)
            candidate_query = candidate_query.where(CandidateUrl.source_platform == platform if platform is not None else false())
        if risk_level:
            candidate_query = candidate_query.where(CandidateUrl.source_risk_level == ChannelRiskLevel(risk_level))

        staging_query = select(StagingLead).options(selectinload(StagingLead.candidate_url)).join(CandidateUrl)
        if start is not None:
            staging_query = staging_query.where(StagingLead.created_at >= start)
        if end is not None:
            staging_query = staging_query.where(StagingLead.created_at <= end)
        if channel:
            platform = source_platform_filter_value(channel)
            staging_query = staging_query.where(CandidateUrl.source_platform == platform if platform is not None else false())
        if risk_level:
            staging_query = staging_query.where(CandidateUrl.source_risk_level == ChannelRiskLevel(risk_level))

        core_query = select(Customer, LeadSource).join(LeadSource, LeadSource.customer_id == Customer.id)
        if start is not None:
            core_query = core_query.where(LeadSource.collected_at >= start)
        if end is not None:
            core_query = core_query.where(LeadSource.collected_at <= end)
        if channel:
            platform = source_platform_filter_value(channel)
            core_query = core_query.where(LeadSource.platform == platform if platform is not None else false())
        if risk_level:
            core_query = core_query.where(LeadSource.channel_risk_level == ChannelRiskLevel(risk_level))

        return self.phase_one_funnel_from_records(
            candidates=list(self.session.scalars(candidate_query).all()),
            staging_leads=list(self.session.scalars(staging_query).all()),
            core_sources=list(self.session.execute(core_query).all()),
            date_from=date_from,
            date_to=date_to,
            channel=channel,
            risk_level=risk_level,
            daily_candidate_target=daily_candidate_target,
        )

    @staticmethod
    def _empty_channel_quality_bucket(channel_name: str, risk_level: str) -> dict:
        return {
            "channel_name": channel_name,
            "display_name": DISPLAY_NAMES.get(channel_name, channel_name),
            "risk_category": risk_level,
            "candidate_url_count": 0,
            "staging_lead_count": 0,
            "core_customer_ids": set(),
            "a_grade_count": 0,
            "b_grade_count": 0,
            "c_grade_count": 0,
            "invalid_count": 0,
            "watch_count": 0,
            "contact_present_count": 0,
            "evidence_present_count": 0,
            "duplicate_review_count": 0,
            "dedupe_keys": [],
            "high_secondary_review_required_count": 0,
            "high_secondary_review_passed_count": 0,
            "risk_event_count": 0,
            "pause_suggested_count": 0,
        }

    @staticmethod
    def _rate(numerator: int, denominator: int) -> float:
        return numerator / denominator if denominator else 0.0

    @classmethod
    def _quality_conclusion(cls, *, risk_level: str, bc_rate: float, duplicate_rate: float, invalid_watch_rate: float, pause_count: int) -> str:
        if risk_level == ChannelRiskLevel.FORBIDDEN.value:
            return "forbidden"
        if risk_level == ChannelRiskLevel.HIGH.value:
            return "policy_research"
        if pause_count:
            return "pause_or_review"
        if bc_rate >= 0.3 and duplicate_rate <= 0.2 and invalid_watch_rate <= 0.5:
            return "quality"
        if duplicate_rate > 0.3 or invalid_watch_rate > 0.5:
            return "adjust"
        return "watch"

    @classmethod
    def _serialize_channel_quality_bucket(cls, bucket: dict) -> dict:
        staging_count = bucket["staging_lead_count"]
        bc_count = bucket["b_grade_count"] + bucket["c_grade_count"]
        invalid_watch_count = bucket["invalid_count"] + bucket["watch_count"]
        duplicate_key_excess = 0
        key_counts: dict[str, int] = {}
        for key in bucket["dedupe_keys"]:
            if not key:
                continue
            key_counts[key] = key_counts.get(key, 0) + 1
        for count in key_counts.values():
            if count > 1:
                duplicate_key_excess += count - 1
        duplicate_count = max(bucket["duplicate_review_count"], duplicate_key_excess)
        high_required = bucket["high_secondary_review_required_count"]
        bc_rate = cls._rate(bc_count, staging_count)
        duplicate_rate = cls._rate(duplicate_count, staging_count)
        invalid_watch_rate = cls._rate(invalid_watch_count, staging_count)
        return {
            "channel_name": bucket["channel_name"],
            "display_name": bucket["display_name"],
            "risk_category": bucket["risk_category"],
            "candidate_url_count": bucket["candidate_url_count"],
            "staging_lead_count": staging_count,
            "core_customer_count": len(bucket["core_customer_ids"]),
            "a_grade_count": bucket["a_grade_count"],
            "b_grade_count": bucket["b_grade_count"],
            "c_grade_count": bucket["c_grade_count"],
            "bc_grade_count": bc_count,
            "invalid_count": bucket["invalid_count"],
            "watch_count": bucket["watch_count"],
            "invalid_watch_count": invalid_watch_count,
            "bc_rate": bc_rate,
            "contact_completeness_rate": cls._rate(bucket["contact_present_count"], staging_count),
            "evidence_completeness_rate": cls._rate(bucket["evidence_present_count"], staging_count),
            "duplicate_count": duplicate_count,
            "duplicate_rate": duplicate_rate,
            "high_secondary_review_required_count": high_required,
            "high_secondary_review_passed_count": bucket["high_secondary_review_passed_count"],
            "high_secondary_review_pass_rate": cls._rate(bucket["high_secondary_review_passed_count"], high_required),
            "risk_event_count": bucket["risk_event_count"],
            "pause_suggested_count": bucket["pause_suggested_count"],
            "quality_conclusion": cls._quality_conclusion(
                risk_level=bucket["risk_category"],
                bc_rate=bc_rate,
                duplicate_rate=duplicate_rate,
                invalid_watch_rate=invalid_watch_rate,
                pause_count=bucket["pause_suggested_count"],
            ),
        }

    @staticmethod
    def _risk_event_sort_key(event: dict[str, object]) -> tuple:
        return (
            RISK_EVENT_SEVERITY_ORDER.get(str(event["severity"]).lower(), 99),
            RISK_EVENT_STATUS_ORDER.get(str(event["resolution_status"]).lower(), 99),
            -datetime.fromisoformat(str(event["created_at"])).timestamp(),
            str(event["id"]),
        )

    @classmethod
    def _empty_risk_event_dashboard_plan(cls, plan) -> dict[str, object]:
        return {
            "id": str(plan.id),
            "country": plan.country,
            "city": plan.city,
            "channel_name": plan.channel_name,
            "channel_type": plan.channel_type,
            "risk_level": enum_value(plan.risk_level),
            "status": enum_value(plan.status),
            "owner": plan.owner,
            "daily_url_limit": plan.daily_url_limit,
            "daily_lead_limit": plan.daily_lead_limit,
            "latest_block_reason": None,
            "latest_event_status": None,
            "latest_event_severity": None,
            "latest_event_created_at": None,
            "resume_requires_resolution_note": True,
            "keywords": list(plan.keywords or []),
        }

    @staticmethod
    def _serialize_risk_event_dashboard_event(event) -> dict[str, object]:
        return {
            "id": str(event.id),
            "channel_plan_id": str(event.channel_plan_id) if getattr(event, "channel_plan_id", None) else None,
            "channel_name": enum_value(getattr(event, "channel", "")),
            "risk_level": enum_value(event.risk_level),
            "severity": enum_value(event.severity),
            "resolution_status": enum_value(event.resolution_status),
            "event_type": event.event_type,
            "block_reason": event.block_reason,
            "pause_suggested": bool(getattr(event, "pause_suggested", False)),
            "task_id": getattr(event, "task_id", None),
            "agent_name": getattr(event, "agent_name", None),
            "action": getattr(event, "action", None),
            "result": getattr(event, "result", "blocked"),
            "resolution_note": getattr(event, "resolution_note", None),
            "resolved_by": getattr(event, "resolved_by", None),
            "created_at": event.created_at.isoformat(),
            "resolved_at": event.resolved_at.isoformat() if getattr(event, "resolved_at", None) else None,
        }

    @classmethod
    def risk_event_dashboard_from_records(
        cls,
        *,
        risk_events: list,
        channel_plans: list,
        date_from: str | date | None = None,
        date_to: str | date | None = None,
        channel: str | None = None,
        risk_level: str | None = None,
        severity: str | None = None,
        resolution_status: str | None = None,
    ) -> dict[str, object]:
        start = parse_date_boundary(date_from)
        end = parse_date_boundary(date_to, end_of_day=True)

        event_items: list[dict[str, object]] = []
        paused_plan_lookup: dict[str, list] = {}

        for event in risk_events:
            created_at = event.created_at
            event_channel = enum_value(getattr(event, "channel", ""))
            event_risk = enum_value(event.risk_level)
            event_severity = enum_value(event.severity)
            event_resolution_status = enum_value(event.resolution_status)
            if not within_date_range(created_at, start=start, end=end):
                continue
            if channel and event_channel != channel:
                continue
            if risk_level and event_risk != risk_level:
                continue
            if severity and event_severity != severity:
                continue
            if resolution_status and event_resolution_status != resolution_status:
                continue
            event_item = cls._serialize_risk_event_dashboard_event(event)
            event_items.append(event_item)
            if getattr(event, "channel_plan_id", None) is not None:
                paused_plan_lookup.setdefault(str(event.channel_plan_id), []).append(event)

        event_items.sort(key=cls._risk_event_sort_key)

        paused_plans: list[dict[str, object]] = []
        for plan in channel_plans:
            plan_status = enum_value(plan.status)
            plan_channel = enum_value(plan.channel_name)
            plan_risk = enum_value(plan.risk_level)
            if plan_status != ChannelPlanStatus.PAUSED.value:
                continue
            if channel and plan_channel != channel:
                continue
            if risk_level and plan_risk != risk_level:
                continue
            latest_events = sorted(
                paused_plan_lookup.get(str(plan.id), []),
                key=lambda item: (
                    -item.created_at.timestamp(),
                    str(item.id),
                ),
            )
            latest_event = latest_events[0] if latest_events else None
            plan_item = cls._empty_risk_event_dashboard_plan(plan)
            if latest_event is not None:
                plan_item["latest_block_reason"] = latest_event.block_reason
                plan_item["latest_event_status"] = enum_value(latest_event.resolution_status)
                plan_item["latest_event_severity"] = enum_value(latest_event.severity)
                plan_item["latest_event_created_at"] = latest_event.created_at.isoformat()
            paused_plans.append(plan_item)

        paused_plans.sort(
            key=lambda item: (
                RISK_EVENT_SEVERITY_ORDER.get(str(item["latest_event_severity"]).lower(), 99),
                str(item["channel_name"]),
                str(item["city"]),
            )
        )

        summary = {
            "risk_event_count": len(event_items),
            "open_risk_event_count": sum(1 for item in event_items if item["resolution_status"] == RiskEventStatus.OPEN.value),
            "investigating_risk_event_count": sum(
                1 for item in event_items if item["resolution_status"] == RiskEventStatus.INVESTIGATING.value
            ),
            "resolved_risk_event_count": sum(1 for item in event_items if item["resolution_status"] == RiskEventStatus.RESOLVED.value),
            "dismissed_risk_event_count": sum(1 for item in event_items if item["resolution_status"] == RiskEventStatus.DISMISSED.value),
            "critical_risk_event_count": sum(1 for item in event_items if item["severity"] == RiskEventSeverity.CRITICAL.value),
            "high_risk_event_count": sum(1 for item in event_items if item["severity"] == RiskEventSeverity.HIGH.value),
            "pause_suggested_count": sum(1 for item in event_items if item["pause_suggested"]),
            "paused_channel_plan_count": len(paused_plans),
        }
        return {
            "summary": summary,
            "events": event_items,
            "paused_channel_plans": paused_plans,
            "filters": {
                "date_from": date_from.isoformat() if isinstance(date_from, date) else date_from,
                "date_to": date_to.isoformat() if isinstance(date_to, date) else date_to,
                "channel": channel,
                "risk_level": risk_level,
                "severity": severity,
                "resolution_status": resolution_status,
            },
            "guardrail": "风险事件与暂停渠道只能查看和复核，不得物理删除；恢复暂停渠道必须说明处理原因。",
        }

    def risk_event_dashboard(
        self,
        *,
        date_from: str | date | None = None,
        date_to: str | date | None = None,
        channel: str | None = None,
        risk_level: str | None = None,
        severity: str | None = None,
        resolution_status: str | None = None,
    ) -> dict[str, object]:
        event_query = select(RiskEvent)
        plan_query = select(ChannelPlan)

        start = parse_date_boundary(date_from)
        end = parse_date_boundary(date_to, end_of_day=True)
        if start is not None:
            event_query = event_query.where(RiskEvent.created_at >= start)
        if end is not None:
            event_query = event_query.where(RiskEvent.created_at <= end)
        if channel:
            event_query = event_query.where(RiskEvent.channel == channel)
            plan_query = plan_query.where(ChannelPlan.channel_name == channel)
        if risk_level:
            event_query = event_query.where(RiskEvent.risk_level == ChannelRiskLevel(risk_level))
            plan_query = plan_query.where(ChannelPlan.risk_level == ChannelRiskLevel(risk_level))
        if severity:
            event_query = event_query.where(RiskEvent.severity == RiskEventSeverity(severity))
        if resolution_status:
            event_query = event_query.where(RiskEvent.resolution_status == RiskEventStatus(resolution_status))
        plan_query = plan_query.where(ChannelPlan.status == ChannelPlanStatus.PAUSED)

        return self.risk_event_dashboard_from_records(
            risk_events=list(self.session.scalars(event_query).all()),
            channel_plans=list(self.session.scalars(plan_query).all()),
            date_from=date_from,
            date_to=date_to,
            channel=channel,
            risk_level=risk_level,
            severity=severity,
            resolution_status=resolution_status,
        )

    @classmethod
    def channel_quality_from_records(
        cls,
        *,
        candidates: list,
        staging_leads: list,
        core_sources: list[tuple],
        risk_events: list,
        date_from: str | date | None = None,
        date_to: str | date | None = None,
        channel: str | None = None,
        risk_level: str | None = None,
    ) -> dict[str, object]:
        start = parse_date_boundary(date_from)
        end = parse_date_boundary(date_to, end_of_day=True)
        buckets: dict[tuple[str, str], dict] = {}

        def bucket_for(channel_name: str, item_risk_level: str) -> dict:
            return buckets.setdefault((channel_name, item_risk_level), cls._empty_channel_quality_bucket(channel_name, item_risk_level))

        for candidate in candidates:
            created_at = candidate.created_at
            channel_name = enum_value(candidate.source_platform)
            candidate_risk = enum_value(candidate.source_risk_level)
            if not within_date_range(created_at, start=start, end=end):
                continue
            if not source_matches(channel_name=channel_name, risk_level=candidate_risk, channel=channel, risk_filter=risk_level):
                continue
            bucket = bucket_for(channel_name, candidate_risk)
            bucket["candidate_url_count"] += 1
            if candidate_risk == ChannelRiskLevel.HIGH.value and getattr(candidate, "requires_secondary_verification", False):
                bucket["high_secondary_review_required_count"] += 1

        for lead in staging_leads:
            created_at = lead.created_at
            candidate = getattr(lead, "candidate_url", None)
            channel_name = enum_value(getattr(candidate, "source_platform", "unknown"))
            lead_risk = enum_value(getattr(candidate, "source_risk_level", "Unknown"))
            if not within_date_range(created_at, start=start, end=end):
                continue
            if not source_matches(channel_name=channel_name, risk_level=lead_risk, channel=channel, risk_filter=risk_level):
                continue
            bucket = bucket_for(channel_name, lead_risk)
            bucket["staging_lead_count"] += 1
            grade = lead.recommended_grade if isinstance(lead.recommended_grade, CustomerGrade) else CustomerGrade(lead.recommended_grade)
            if grade == CustomerGrade.A:
                bucket["a_grade_count"] += 1
            elif grade == CustomerGrade.B:
                bucket["b_grade_count"] += 1
            elif grade == CustomerGrade.C:
                bucket["c_grade_count"] += 1
            elif grade == CustomerGrade.INVALID:
                bucket["invalid_count"] += 1
            elif grade == CustomerGrade.WATCH:
                bucket["watch_count"] += 1
            if getattr(lead, "contacts_json", []):
                bucket["contact_present_count"] += 1
            if str(getattr(lead, "source_evidence", "") or "").strip():
                bucket["evidence_present_count"] += 1
            if enum_value(getattr(lead, "review_status", "")) == StagingReviewStatus.DUPLICATE.value:
                bucket["duplicate_review_count"] += 1
            if getattr(lead, "dedupe_key", None):
                bucket["dedupe_keys"].append(lead.dedupe_key)
            if lead_risk == ChannelRiskLevel.HIGH.value and enum_value(getattr(lead, "review_status", "")) == StagingReviewStatus.APPROVED.value:
                bucket["high_secondary_review_passed_count"] += 1

        for customer, source in core_sources:
            collected_at = getattr(source, "collected_at", None) or getattr(customer, "created_at")
            channel_name = enum_value(source.platform)
            source_risk = enum_value(source.channel_risk_level)
            if not within_date_range(collected_at, start=start, end=end):
                continue
            if not source_matches(channel_name=channel_name, risk_level=source_risk, channel=channel, risk_filter=risk_level):
                continue
            bucket_for(channel_name, source_risk)["core_customer_ids"].add(str(customer.id))

        for event in risk_events:
            created_at = event.created_at
            event_channel = enum_value(event.channel)
            event_risk = enum_value(event.risk_level)
            if not within_date_range(created_at, start=start, end=end):
                continue
            if not source_matches(channel_name=event_channel, risk_level=event_risk, channel=channel, risk_filter=risk_level):
                continue
            bucket = bucket_for(event_channel, event_risk)
            bucket["risk_event_count"] += 1
            if getattr(event, "pause_suggested", False):
                bucket["pause_suggested_count"] += 1

        channels = [
            cls._serialize_channel_quality_bucket(bucket)
            for _key, bucket in sorted(buckets.items(), key=lambda item: (item[0][0], item[0][1]))
        ]
        summary = {
            "candidate_url_count": sum(item["candidate_url_count"] for item in channels),
            "staging_lead_count": sum(item["staging_lead_count"] for item in channels),
            "core_customer_count": sum(item["core_customer_count"] for item in channels),
            "bc_grade_count": sum(item["bc_grade_count"] for item in channels),
            "invalid_watch_count": sum(item["invalid_watch_count"] for item in channels),
            "duplicate_count": sum(item["duplicate_count"] for item in channels),
            "risk_event_count": sum(item["risk_event_count"] for item in channels),
        }
        summary["bc_rate"] = cls._rate(summary["bc_grade_count"], summary["staging_lead_count"])
        summary["duplicate_rate"] = cls._rate(summary["duplicate_count"], summary["staging_lead_count"])
        return {
            "summary": summary,
            "channels": channels,
            "filters": {
                "date_from": date_from.isoformat() if isinstance(date_from, date) else date_from,
                "date_to": date_to.isoformat() if isinstance(date_to, date) else date_to,
                "channel": channel,
                "risk_level": risk_level,
            },
            "guardrail": "渠道质量指标只用于调整配额，不得绕过 High/Forbidden、二次复核、勿扰和合规复核规则。",
        }

    def channel_quality_metrics(
        self,
        *,
        date_from: str | date | None = None,
        date_to: str | date | None = None,
        channel: str | None = None,
        risk_level: str | None = None,
    ) -> dict[str, object]:
        start = parse_date_boundary(date_from)
        end = parse_date_boundary(date_to, end_of_day=True)

        candidate_query = select(CandidateUrl)
        staging_query = select(StagingLead).options(selectinload(StagingLead.candidate_url)).join(CandidateUrl)
        core_query = select(Customer, LeadSource).join(LeadSource, LeadSource.customer_id == Customer.id)
        event_query = select(RiskEvent)

        if start is not None:
            candidate_query = candidate_query.where(CandidateUrl.created_at >= start)
            staging_query = staging_query.where(StagingLead.created_at >= start)
            core_query = core_query.where(LeadSource.collected_at >= start)
            event_query = event_query.where(RiskEvent.created_at >= start)
        if end is not None:
            candidate_query = candidate_query.where(CandidateUrl.created_at <= end)
            staging_query = staging_query.where(StagingLead.created_at <= end)
            core_query = core_query.where(LeadSource.collected_at <= end)
            event_query = event_query.where(RiskEvent.created_at <= end)
        if channel:
            platform = source_platform_filter_value(channel)
            if platform is None:
                candidate_query = candidate_query.where(false())
                staging_query = staging_query.where(false())
                core_query = core_query.where(false())
            else:
                candidate_query = candidate_query.where(CandidateUrl.source_platform == platform)
                staging_query = staging_query.where(CandidateUrl.source_platform == platform)
                core_query = core_query.where(LeadSource.platform == platform)
            event_query = event_query.where(RiskEvent.channel == channel)
        if risk_level:
            candidate_query = candidate_query.where(CandidateUrl.source_risk_level == ChannelRiskLevel(risk_level))
            staging_query = staging_query.where(CandidateUrl.source_risk_level == ChannelRiskLevel(risk_level))
            core_query = core_query.where(LeadSource.channel_risk_level == ChannelRiskLevel(risk_level))
            event_query = event_query.where(RiskEvent.risk_level == ChannelRiskLevel(risk_level))

        return self.channel_quality_from_records(
            candidates=list(self.session.scalars(candidate_query).all()),
            staging_leads=list(self.session.scalars(staging_query).all()),
            core_sources=list(self.session.execute(core_query).all()),
            risk_events=list(self.session.scalars(event_query).all()),
            date_from=date_from,
            date_to=date_to,
            channel=channel,
            risk_level=risk_level,
        )

    def channel_lead_metrics(self, *, date_from: str | None = None, date_to: str | None = None) -> dict[str, object]:
        start = parse_date_boundary(date_from)
        end = parse_date_boundary(date_to, end_of_day=True)

        rules = self.session.scalars(select(ChannelRiskRule)).all()
        metrics: dict[str, ChannelMetric] = {}

        for rule in rules:
            channel_name = rule.channel_name
            risk_level = rule.risk_level.value
            metrics[channel_name] = ChannelMetric(
                channel_name=channel_name,
                display_name=DISPLAY_NAMES.get(channel_name, channel_name),
                risk_level=risk_level,
                risk_status=risk_status_for(risk_level),
                investment_recommendation="blocked"
                if risk_level in {ChannelRiskLevel.HIGH.value, ChannelRiskLevel.FORBIDDEN.value}
                else "watch",
            )

        query = select(LeadSource, Customer).join(Customer, LeadSource.customer_id == Customer.id)
        if start is not None:
            query = query.where(LeadSource.collected_at >= start)
        if end is not None:
            query = query.where(LeadSource.collected_at <= end)

        for source, customer in self.session.execute(query).all():
            channel_name = source.platform.value
            risk_level = source.channel_risk_level.value
            metric = metrics.setdefault(
                channel_name,
                ChannelMetric(
                    channel_name=channel_name,
                    display_name=DISPLAY_NAMES.get(channel_name, channel_name),
                    risk_level=risk_level,
                    risk_status=risk_status_for(risk_level),
                    investment_recommendation="watch",
                ),
            )

            metric.candidate_count += 1
            if customer.grade == CustomerGrade.B:
                metric.b_grade_count += 1
            elif customer.grade == CustomerGrade.C:
                metric.c_grade_count += 1
            elif customer.grade in {CustomerGrade.INVALID, CustomerGrade.WATCH}:
                metric.invalid_count += 1

        channels = sorted(
            metrics.values(),
            key=lambda item: (item.bc_grade_count, item.candidate_count, item.channel_name),
            reverse=True,
        )
        for metric in channels:
            metric.investment_recommendation = recommendation_for(metric.risk_level, metric.bc_grade_count)

        summary_candidate_count = sum(item.candidate_count for item in channels)
        summary_b_count = sum(item.b_grade_count for item in channels)
        summary_c_count = sum(item.c_grade_count for item in channels)
        summary_invalid_count = sum(item.invalid_count for item in channels)

        return {
            "summary": {
                "candidate_count": summary_candidate_count,
                "b_grade_count": summary_b_count,
                "c_grade_count": summary_c_count,
                "bc_grade_count": summary_b_count + summary_c_count,
                "invalid_count": summary_invalid_count,
                "invalid_rate": summary_invalid_count / summary_candidate_count if summary_candidate_count else 0.0,
            },
            "channels": [
                {
                    "channel_name": item.channel_name,
                    "display_name": item.display_name,
                    "risk_level": item.risk_level,
                    "risk_status": item.risk_status,
                    "investment_recommendation": item.investment_recommendation,
                    "candidate_count": item.candidate_count,
                    "b_grade_count": item.b_grade_count,
                    "c_grade_count": item.c_grade_count,
                    "bc_grade_count": item.bc_grade_count,
                    "invalid_count": item.invalid_count,
                    "invalid_rate": item.invalid_rate,
                }
                for item in channels
            ],
        }

    def latest_compliance_status(self, customer_id) -> str | None:
        review = self.session.scalar(
            select(ComplianceReview)
            .where(ComplianceReview.customer_id == customer_id)
            .order_by(ComplianceReview.created_at.desc(), ComplianceReview.id.desc())
        )
        return review.status.value if review else None

    def outreach_sla_metrics(
        self,
        *,
        owner: str | None = None,
        grade: str | None = None,
        channel: str | None = None,
    ) -> dict[str, object]:
        normalized_grade = CustomerGrade(grade) if grade else None
        normalized_channel = ContactMethodType(channel) if channel else None
        now = datetime.utcnow()

        outreach_query = select(OutreachRecord, Customer).join(Customer, OutreachRecord.customer_id == Customer.id)
        outreach_query = outreach_query.where(OutreachRecord.status.in_(OUTREACH_SENT_STATUSES))
        if owner:
            outreach_query = outreach_query.where(OutreachRecord.owner == owner)
        if normalized_grade:
            outreach_query = outreach_query.where(Customer.grade == normalized_grade)
        if normalized_channel:
            outreach_query = outreach_query.where(OutreachRecord.channel == normalized_channel)

        outreach_records = self.session.execute(outreach_query).all()
        sent_count = len(outreach_records)
        replied_count = sum(1 for record, _customer in outreach_records if record.status == OutreachStatus.REPLIED)

        customer_query = select(Customer).where(
            Customer.do_not_contact.is_(False),
            Customer.grade.in_([CustomerGrade.B, CustomerGrade.C]),
            Customer.status.in_(OUTREACH_PENDING_STATUSES),
        )
        if owner:
            customer_query = customer_query.where(Customer.owner == owner)
        if normalized_grade:
            customer_query = customer_query.where(Customer.grade == normalized_grade)
        if normalized_channel:
            customer_query = customer_query.where(
                Customer.id.in_(
                    select(OutreachRecord.customer_id).where(OutreachRecord.channel == normalized_channel)
                )
            )

        queue = []
        overdue_count = 0
        compliance_waiting_count = 0

        for customer in self.session.scalars(customer_query).all():
            sla_hours = SLA_HOURS[customer.grade]
            waiting_hours = max((now - customer.updated_at.replace(tzinfo=None)).total_seconds() / 3600, 0)
            compliance_status = self.latest_compliance_status(customer.id) if customer.grade == CustomerGrade.C else None

            if customer.grade == CustomerGrade.C and compliance_status != ComplianceReviewStatus.APPROVED.value:
                risk_status = "compliance_waiting"
                next_action = "等待合规复核"
                compliance_waiting_count += 1
            elif waiting_hours > sla_hours:
                risk_status = "overdue"
                next_action = "立即跟进"
                overdue_count += 1
            elif waiting_hours >= sla_hours * 0.8:
                risk_status = "warning"
                next_action = "优先跟进"
            else:
                risk_status = "on_track"
                next_action = "按 SLA 跟进"

            queue.append(
                {
                    "customer_id": str(customer.id),
                    "customer_name": customer.name,
                    "grade": customer.grade.value,
                    "owner": customer.owner,
                    "status": customer.status.value,
                    "sla_hours": sla_hours,
                    "waiting_hours": round(waiting_hours, 2),
                    "risk_status": risk_status,
                    "compliance_status": compliance_status,
                    "next_action": next_action,
                }
            )

        queue.sort(
            key=lambda item: (
                {"overdue": 0, "compliance_waiting": 1, "warning": 2, "on_track": 3}.get(item["risk_status"], 4),
                -item["waiting_hours"],
            )
        )

        return {
            "summary": {
                "sent_count": sent_count,
                "replied_count": replied_count,
                "response_rate": replied_count / sent_count if sent_count else 0.0,
                "pending_count": len(queue),
                "overdue_count": overdue_count,
                "compliance_waiting_count": compliance_waiting_count,
                "sla_risk_count": overdue_count + compliance_waiting_count,
            },
            "queue": queue,
        }

    def create_roi_cost(
        self,
        *,
        external_id: str | None,
        cost_type: str,
        amount: float | None,
        currency: str,
        labor_hours: float | None,
        hourly_rate: float | None,
        channel_name: str | None,
        notes: str | None,
    ) -> RoiCostEntry:
        if cost_type == "labor":
            if labor_hours is None or hourly_rate is None:
                raise ValueError("人工成本需要 labor_hours 和 hourly_rate。")
            amount = labor_hours * hourly_rate
        elif amount is None:
            raise ValueError("AI/API 和工具成本需要 amount。")

        entry = RoiCostEntry(
            external_id=external_id,
            cost_type=cost_type,
            amount=amount,
            currency=currency,
            labor_hours=labor_hours,
            hourly_rate=hourly_rate,
            channel_name=channel_name,
            notes=notes,
        )
        self.session.add(entry)
        self.session.flush()
        return entry

    def roi_metrics(
        self,
        *,
        channel: str | None = None,
        date_from: str | date | None = None,
        date_to: str | date | None = None,
    ) -> dict[str, object]:
        cost_query = select(RoiCostEntry)
        audit_query = select(AIAuditLog)
        staging_query = select(StagingLead).options(selectinload(StagingLead.candidate_url)).join(CandidateUrl)
        core_query = select(Customer, LeadSource).join(LeadSource, LeadSource.customer_id == Customer.id)
        reply_query = select(OutreachRecord).where(OutreachRecord.status == OutreachStatus.REPLIED)

        start = parse_date_boundary(date_from)
        end = parse_date_boundary(date_to, end_of_day=True)
        if start is not None:
            cost_query = cost_query.where(RoiCostEntry.occurred_at >= start)
            audit_query = audit_query.where(AIAuditLog.executed_at >= start)
            staging_query = staging_query.where(StagingLead.created_at >= start)
            core_query = core_query.where(LeadSource.collected_at >= start)
            reply_query = reply_query.where(OutreachRecord.sent_at >= start)
        if end is not None:
            cost_query = cost_query.where(RoiCostEntry.occurred_at <= end)
            audit_query = audit_query.where(AIAuditLog.executed_at <= end)
            staging_query = staging_query.where(StagingLead.created_at <= end)
            core_query = core_query.where(LeadSource.collected_at <= end)
            reply_query = reply_query.where(OutreachRecord.sent_at <= end)
        if channel:
            cost_query = cost_query.where(RoiCostEntry.channel_name == channel)
            audit_query = audit_query.where(AIAuditLog.channel_name == channel)
            platform = source_platform_filter_value(channel)
            if platform is None:
                staging_query = staging_query.where(false())
                core_query = core_query.where(false())
                reply_query = reply_query.where(false())
            else:
                staging_query = staging_query.where(CandidateUrl.source_platform == platform)
                core_query = core_query.where(LeadSource.platform == platform)
                reply_query = reply_query.where(
                    OutreachRecord.customer_id.in_(
                        select(LeadSource.customer_id).where(LeadSource.platform == platform)
                    )
                )

        return self.roi_metrics_from_records(
            cost_entries=list(self.session.scalars(cost_query).all()),
            audit_logs=list(self.session.scalars(audit_query).all()),
            staging_leads=list(self.session.scalars(staging_query).all()),
            core_sources=list(self.session.execute(core_query).all()),
            outreach_records=list(self.session.scalars(reply_query).all()),
            date_from=date_from,
            date_to=date_to,
            channel=channel,
        )

    @classmethod
    def roi_metrics_from_records(
        cls,
        *,
        cost_entries: list,
        audit_logs: list,
        staging_leads: list,
        core_sources: list[tuple],
        outreach_records: list | None = None,
        date_from: str | date | None = None,
        date_to: str | date | None = None,
        channel: str | None = None,
    ) -> dict[str, object]:
        start = parse_date_boundary(date_from)
        end = parse_date_boundary(date_to, end_of_day=True)

        matched_costs = [
            entry
            for entry in cost_entries
            if within_date_range(getattr(entry, "occurred_at", start or datetime.utcnow()), start=start, end=end)
            and (not channel or getattr(entry, "channel_name", None) == channel)
        ]
        matched_audits = [
            log
            for log in audit_logs
            if within_date_range(getattr(log, "executed_at", start or datetime.utcnow()), start=start, end=end)
            and (not channel or getattr(log, "channel_name", None) == channel)
        ]
        matched_staging = []
        for lead in staging_leads:
            created_at = getattr(lead, "created_at", None)
            if created_at is None or not within_date_range(created_at, start=start, end=end):
                continue
            candidate = getattr(lead, "candidate_url", None)
            lead_channel = enum_value(getattr(candidate, "source_platform", ""))
            if channel and lead_channel != channel:
                continue
            matched_staging.append(lead)

        matched_core_sources = []
        for customer, source in core_sources:
            collected_at = getattr(source, "collected_at", None) or getattr(customer, "created_at")
            if not within_date_range(collected_at, start=start, end=end):
                continue
            if channel and enum_value(source.platform) != channel:
                continue
            matched_core_sources.append((customer, source))

        labor_cost = sum(float(getattr(item, "amount", 0) or 0) for item in matched_costs if getattr(item, "cost_type", None) == "labor")
        ai_api_cost = sum(float(getattr(item, "amount", 0) or 0) for item in matched_costs if getattr(item, "cost_type", None) == "ai_api")
        tool_cost = sum(float(getattr(item, "amount", 0) or 0) for item in matched_costs if getattr(item, "cost_type", None) == "tool")
        total_cost = labor_cost + ai_api_cost + tool_cost
        effective_customers = [
            customer
            for customer, _source in matched_core_sources
            if getattr(customer, "grade", None) in {CustomerGrade.B, CustomerGrade.C}
        ]
        effective_customer_ids = {getattr(customer, "id", None) for customer in effective_customers}
        reply_count = sum(
            1
            for record in (outreach_records or [])
            if getattr(record, "customer_id", None) in effective_customer_ids
        )
        sales_opportunity_count = sum(1 for customer in effective_customers if getattr(customer, "grade", None) == CustomerGrade.C)
        llm_call_count = len(matched_audits)
        llm_failure_count = sum(
            1
            for log in matched_audits
            if bool(getattr(log, "risk_blocked", False)) or getattr(log, "output_json", getattr(log, "output_payload", None)) in (None, {})
        )
        llm_token_count = 0
        llm_cost_total = 0.0
        for log in matched_audits:
            tokens = getattr(log, "total_tokens", None)
            if tokens is None:
                tokens = (getattr(log, "input_tokens", None) or 0) + (getattr(log, "output_tokens", None) or 0)
            llm_token_count += int(tokens or 0)
            llm_cost_total += float(getattr(log, "cost_amount", 0) or 0)

        completed_reviews = []
        for lead in matched_staging:
            if enum_value(getattr(lead, "review_status", "")) not in {
                StagingReviewStatus.APPROVED.value,
                StagingReviewStatus.REJECTED.value,
                StagingReviewStatus.DUPLICATE.value,
            }:
                continue
            completed_reviews.append(
                max((getattr(lead, "updated_at", lead.created_at) - lead.created_at).total_seconds() / 3600, 0)
            )
        review_completed_count = len(completed_reviews)
        avg_review_duration_hours = (
            round(sum(completed_reviews) / review_completed_count, 2) if review_completed_count else None
        )

        def cost_per(denominator: int) -> float | None:
            return round(total_cost / denominator, 2) if denominator else None

        def ai_cost_per(denominator: int) -> float | None:
            return round(llm_cost_total / denominator, 4) if denominator else None

        return {
            "summary": {
                "total_cost": round(total_cost, 2),
                "labor_cost": round(labor_cost, 2),
                "ai_api_cost": round(ai_api_cost, 2),
                "tool_cost": round(tool_cost, 2),
                "effective_lead_count": len(effective_customers),
                "reply_count": reply_count,
                "sales_opportunity_count": sales_opportunity_count,
                "cost_per_effective_lead": cost_per(len(effective_customers)),
                "cost_per_reply": cost_per(reply_count),
                "cost_per_sales_opportunity": cost_per(sales_opportunity_count),
                "llm_call_count": llm_call_count,
                "llm_failure_count": llm_failure_count,
                "llm_failure_rate": llm_failure_count / llm_call_count if llm_call_count else 0.0,
                "llm_token_count": llm_token_count,
                "llm_cost_total": round(llm_cost_total, 4),
                "review_completed_count": review_completed_count,
                "avg_review_duration_hours": avg_review_duration_hours,
                "ai_cost_per_effective_lead": ai_cost_per(len(effective_customers)),
            },
            "compliance_guardrail": ROI_COMPLIANCE_GUARDRAIL,
        }

    def _team_queue(self, statuses: set[CustomerStatus]) -> dict[str, object]:
        customers = list(
            self.session.scalars(
                select(Customer)
                .where(
                    Customer.do_not_contact.is_(False),
                    Customer.status.in_(list(statuses)),
                )
                .order_by(Customer.updated_at.asc(), Customer.id.asc())
            ).all()
        )
        return {
            "count": len(customers),
            "items": [
                {
                    "customer_id": str(customer.id),
                    "customer_name": customer.name,
                    "grade": customer.grade.value,
                    "status": customer.status.value,
                    "owner": customer.owner,
                    "updated_at": customer.updated_at.isoformat(),
                }
                for customer in customers
            ],
        }

    def _risk_events(self) -> list[dict[str, object]]:
        events = list(
            self.session.scalars(
                select(AIAuditLog)
                .where(AIAuditLog.risk_blocked.is_(True))
                .order_by(AIAuditLog.executed_at.desc(), AIAuditLog.id.desc())
                .limit(20)
            ).all()
        )
        return [
            {
                "id": str(event.id),
                "customer_id": str(event.customer_id) if event.customer_id else None,
                "task_type": event.task_type.value,
                "model_name": event.model_name,
                "prompt_version": event.prompt_version,
                "source_url": event.source_url,
                "risk_blocked": event.risk_blocked,
                "risk_block_reason": event.risk_block_reason,
                "executed_at": event.executed_at.isoformat(),
            }
            for event in events
        ]

    def admin_overview(self) -> dict[str, object]:
        channel_dashboard = self.channel_lead_metrics()
        sla_dashboard = self.outreach_sla_metrics()
        channel_summary = channel_dashboard["summary"]
        sla_summary = sla_dashboard["summary"]
        risk_events = self._risk_events()

        return {
            "summary": {
                "candidate_count": channel_summary["candidate_count"],
                "b_grade_count": channel_summary["b_grade_count"],
                "c_grade_count": channel_summary["c_grade_count"],
                "bc_grade_count": channel_summary["bc_grade_count"],
                "response_rate": sla_summary["response_rate"],
                "sla_risk_count": sla_summary["sla_risk_count"],
            },
            "channel_outputs": channel_dashboard["channels"],
            "team_queues": {
                "operations": self._team_queue(OPERATIONS_QUEUE_STATUSES),
                "customer_service": self._team_queue(CUSTOMER_SERVICE_QUEUE_STATUSES),
                "sales": self._team_queue(SALES_QUEUE_STATUSES),
            },
            "risk_events": risk_events,
            "blocked_tasks": [event for event in risk_events if event["risk_blocked"]],
        }
