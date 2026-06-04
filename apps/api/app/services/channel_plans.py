from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ChannelPlan
from app.models.enums import ChannelPlanStatus, ChannelRiskLevel, SourceUsageType
from app.services.audit_risk import AuditRiskLogService


class ChannelPlanService:
    FORBIDDEN_ACTION_TERMS = (
        "自动私信",
        "私信群发",
        "自动加好友",
        "加好友",
        "登录采集",
        "登录后采集",
        "批量私信",
        "auto dm",
        "automatic dm",
        "direct message",
        "friend request",
        "add friend",
        "logged-in scraping",
        "login scraping",
        "автоматическая рассылка",
        "личные сообщения",
        "добавить в друзья",
        "добавление в друзья",
        "массовая рассылка",
    )

    def __init__(self, session: Session) -> None:
        self.session = session

    @staticmethod
    def validate_daily_url_limit(daily_url_limit: int | None) -> None:
        if daily_url_limit is None or daily_url_limit <= 0:
            raise ValueError("daily_url_limit 不得为空且必须大于 0。")

    @classmethod
    def validate_no_forbidden_actions(
        cls,
        *,
        channel_name: str,
        channel_type: str,
        keywords: list[str] | None,
    ) -> None:
        text = " ".join([channel_name or "", channel_type or "", *(keywords or [])]).lower()
        if any(term in text for term in cls.FORBIDDEN_ACTION_TERMS):
            raise ValueError("不允许创建包含自动私信、加好友、登录采集的计划。")

    @staticmethod
    def resolve_plan_policy(
        *,
        risk_level: str | ChannelRiskLevel,
        status: str | ChannelPlanStatus,
        requested_usage_type: str | SourceUsageType | None,
    ) -> SourceUsageType:
        risk = ChannelRiskLevel(risk_level)
        plan_status = ChannelPlanStatus(status)
        if risk == ChannelRiskLevel.FORBIDDEN and plan_status == ChannelPlanStatus.ENABLED:
            raise ValueError("Forbidden 计划不能启用。")

        usage_type = (
            SourceUsageType.PUBLIC_DISCOVERY_ONLY
            if risk == ChannelRiskLevel.HIGH
            else SourceUsageType.AUTOMATIC_COLLECTION
        )
        if requested_usage_type is not None:
            usage_type = SourceUsageType(requested_usage_type)

        if risk == ChannelRiskLevel.HIGH and plan_status == ChannelPlanStatus.ENABLED:
            if usage_type != SourceUsageType.PUBLIC_DISCOVERY_ONLY:
                raise ValueError("High 计划启用时必须限定 public_discovery_only。")
        return usage_type

    @staticmethod
    def validate_resume_resolution_note(
        *,
        old_status: str | ChannelPlanStatus,
        new_status: str | ChannelPlanStatus,
        resolution_note: str | None,
    ) -> None:
        if (
            ChannelPlanStatus(old_status) == ChannelPlanStatus.PAUSED
            and ChannelPlanStatus(new_status) == ChannelPlanStatus.ENABLED
            and not (resolution_note or "").strip()
        ):
            raise ValueError("恢复渠道必须记录处理说明。")

    def create_channel_plan(
        self,
        *,
        country: str,
        city: str,
        channel_name: str,
        channel_type: str,
        risk_level: str | ChannelRiskLevel,
        keywords: list[str] | None,
        daily_url_limit: int | None,
        daily_lead_limit: int | None = None,
        status: str | ChannelPlanStatus = ChannelPlanStatus.DRAFT,
        owner: str | None = None,
        source_usage_type: str | SourceUsageType | None = None,
    ) -> ChannelPlan:
        self.validate_daily_url_limit(daily_url_limit)
        self.validate_no_forbidden_actions(
            channel_name=channel_name,
            channel_type=channel_type,
            keywords=keywords,
        )
        risk = ChannelRiskLevel(risk_level)
        plan_status = ChannelPlanStatus(status)
        usage = self.resolve_plan_policy(
            risk_level=risk,
            status=plan_status,
            requested_usage_type=source_usage_type,
        )
        plan = ChannelPlan(
            country=country,
            city=city,
            channel_name=channel_name,
            channel_type=channel_type,
            risk_level=risk,
            source_usage_type=usage,
            keywords=keywords or [],
            daily_url_limit=daily_url_limit,
            daily_lead_limit=daily_lead_limit,
            status=plan_status,
            owner=owner,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        self.session.add(plan)
        self.session.flush()
        return plan

    def get_channel_plan(self, plan_id: UUID) -> ChannelPlan | None:
        return self.session.get(ChannelPlan, plan_id)

    def list_channel_plans(
        self,
        *,
        country: str | None = None,
        city: str | None = None,
        status: str | ChannelPlanStatus | None = None,
        limit: int = 100,
    ) -> list[ChannelPlan]:
        statement = select(ChannelPlan).order_by(ChannelPlan.created_at.desc()).limit(limit)
        if country is not None:
            statement = statement.where(ChannelPlan.country == country)
        if city is not None:
            statement = statement.where(ChannelPlan.city == city)
        if status is not None:
            statement = statement.where(ChannelPlan.status == ChannelPlanStatus(status))
        return list(self.session.scalars(statement).all())

    def update_channel_plan(self, plan_id: UUID, **changes) -> ChannelPlan:
        plan = self.get_channel_plan(plan_id)
        if plan is None:
            raise ValueError("channel plan 不存在。")

        country = changes.get("country", plan.country)
        city = changes.get("city", plan.city)
        channel_name = changes.get("channel_name", plan.channel_name)
        channel_type = changes.get("channel_type", plan.channel_type)
        risk_level = ChannelRiskLevel(changes.get("risk_level", plan.risk_level))
        keywords = changes.get("keywords", plan.keywords)
        daily_url_limit = changes.get("daily_url_limit", plan.daily_url_limit)
        daily_lead_limit = changes.get("daily_lead_limit", plan.daily_lead_limit)
        status = ChannelPlanStatus(changes.get("status", plan.status))
        owner = changes.get("owner", plan.owner)
        source_usage_type = changes.get("source_usage_type", plan.source_usage_type)
        resolution_note = changes.get("resolution_note")
        resolved_by = changes.get("resolved_by")

        self.validate_resume_resolution_note(
            old_status=plan.status,
            new_status=status,
            resolution_note=resolution_note,
        )
        self.validate_daily_url_limit(daily_url_limit)
        self.validate_no_forbidden_actions(
            channel_name=channel_name,
            channel_type=channel_type,
            keywords=keywords,
        )
        usage = self.resolve_plan_policy(
            risk_level=risk_level,
            status=status,
            requested_usage_type=source_usage_type,
        )

        plan.country = country
        plan.city = city
        plan.channel_name = channel_name
        plan.channel_type = channel_type
        plan.risk_level = risk_level
        plan.source_usage_type = usage
        plan.keywords = keywords or []
        plan.daily_url_limit = daily_url_limit
        plan.daily_lead_limit = daily_lead_limit
        plan.status = status
        plan.owner = owner
        plan.updated_at = datetime.utcnow()
        if plan.status == ChannelPlanStatus.ENABLED and resolution_note:
            AuditRiskLogService(self.session).record_review_log(
                task_id=str(plan.id),
                agent_name=None,
                action="resume_channel_plan",
                reviewer=resolved_by,
                input_ref=plan.channel_name,
                output_ref=resolution_note.strip(),
                result="resolved",
            )
        self.session.flush()
        return plan

    def archive_channel_plan(self, plan_id: UUID) -> ChannelPlan:
        return self.update_channel_plan(plan_id, status=ChannelPlanStatus.ARCHIVED)
