from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import quote_plus
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import ChannelPlan
from app.models.enums import ChannelPlanStatus, ChannelRiskLevel, SourcePlatform, SourceUsageType
from app.services.audit_risk import AuditRiskLogService
from app.services.channel_plans import ChannelPlanService
from app.services.raw_collection import CandidateUrlUpsertResult, RawCollectionService


@dataclass(frozen=True)
class DiscoveryPolicy:
    task_type: str
    source_usage_type: SourceUsageType
    queue_eligible: bool


@dataclass(frozen=True)
class DiscoveryTaskText:
    allowed_actions: str
    forbidden_actions: str


@dataclass(frozen=True)
class DiscoveryUrlSpec:
    url: str
    source_platform: SourcePlatform
    discovery_reason: str
    keyword: str


@dataclass(frozen=True)
class ChannelDiscoveryRunResult:
    task: object
    candidates: list[CandidateUrlUpsertResult]


class ChannelDiscoveryAgentService:
    AGENT_NAME = "channel_discovery_agent"
    ACTION = "run_channel_discovery"

    def __init__(self, session: Session) -> None:
        self.session = session
        self.raw_collection_service = RawCollectionService(session)
        self.audit_service = AuditRiskLogService(session)

    @staticmethod
    def validate_plan_for_discovery(plan: ChannelPlan) -> None:
        if ChannelRiskLevel(plan.risk_level) == ChannelRiskLevel.FORBIDDEN:
            raise ValueError("Forbidden 计划不允许执行渠道发现。")
        ChannelPlanService.validate_no_forbidden_actions(
            channel_name=plan.channel_name,
            channel_type=plan.channel_type,
            keywords=plan.keywords,
        )
        if ChannelPlanStatus(plan.status) in {ChannelPlanStatus.PAUSED, ChannelPlanStatus.ARCHIVED}:
            raise ValueError("暂停或归档渠道无法执行渠道发现。")
        if plan.daily_url_limit <= 0:
            raise ValueError("channel_plan daily_url_limit 必须大于 0。")

    @staticmethod
    def resolve_discovery_policy(plan: ChannelPlan) -> DiscoveryPolicy:
        risk = ChannelRiskLevel(plan.risk_level)
        if risk == ChannelRiskLevel.FORBIDDEN:
            raise ValueError("Forbidden 计划不允许执行渠道发现。")
        if risk == ChannelRiskLevel.HIGH:
            if SourceUsageType(plan.source_usage_type) != SourceUsageType.PUBLIC_DISCOVERY_ONLY:
                raise ValueError("High 计划只允许 public_discovery_only。")
            return DiscoveryPolicy(
                task_type=RawCollectionService.HIGH_RISK_PUBLIC_DISCOVERY_TASK_TYPE,
                source_usage_type=SourceUsageType.PUBLIC_DISCOVERY_ONLY,
                queue_eligible=False,
            )
        return DiscoveryPolicy(
            task_type="channel_discovery",
            source_usage_type=SourceUsageType(plan.source_usage_type),
            queue_eligible=True,
        )

    @staticmethod
    def build_task_text(plan: ChannelPlan) -> DiscoveryTaskText:
        return DiscoveryTaskText(
            allowed_actions=(
                "读取公开页面或公开搜索结果；生成候选 URL；记录发现关键词、城市、渠道类型和公开来源理由"
            ),
            forbidden_actions=(
                "不得登录平台；不得绕过搜索引擎或平台限制；不得触达客户；不得发送消息；不得请求建立联系人关系；不得加入群组"
            ),
        )

    @classmethod
    def infer_source_platform(cls, plan: ChannelPlan) -> SourcePlatform:
        text = f"{plan.channel_name} {plan.channel_type}".lower()
        if "official" in text or "官网" in text or "website" in text:
            return SourcePlatform.OFFICIAL_WEBSITE
        if "directory" in text or "目录" in text:
            return SourcePlatform.PUBLIC_DIRECTORY
        if "yandex" in text:
            return SourcePlatform.YANDEX_MAPS if "map" in text or "地图" in text else SourcePlatform.SEARCH_ENGINE
        if "google" in text and ("map" in text or "地图" in text):
            return SourcePlatform.GOOGLE_MAPS
        if "youtube" in text:
            return SourcePlatform.YOUTUBE
        if "drom" in text:
            return SourcePlatform.DROM
        if "search" in text or "搜索" in text:
            return SourcePlatform.SEARCH_ENGINE
        return SourcePlatform.OTHER

    @classmethod
    def build_discovery_url(cls, *, plan: ChannelPlan, keyword: str, source_platform: SourcePlatform) -> str:
        query = f"{keyword} {plan.city} {plan.country}".strip()
        encoded = quote_plus(query)
        path_encoded = quote_plus(query).replace("+", "%20")
        if source_platform == SourcePlatform.YANDEX_MAPS:
            return f"https://yandex.com/maps/?text={encoded}"
        if source_platform == SourcePlatform.GOOGLE_MAPS:
            return f"https://www.google.com/maps/search/{path_encoded}"
        if source_platform == SourcePlatform.YOUTUBE:
            return f"https://www.youtube.com/results?search_query={encoded}"
        if source_platform == SourcePlatform.DROM:
            return f"https://www.drom.ru/search/?text={encoded}"
        if source_platform == SourcePlatform.PUBLIC_DIRECTORY:
            return f"https://www.google.com/search?q={encoded}+business+directory"
        if source_platform == SourcePlatform.OFFICIAL_WEBSITE:
            return f"https://www.google.com/search?q={encoded}+official+dealer"
        return f"https://www.google.com/search?q={encoded}"

    @classmethod
    def build_discovery_specs(cls, plan: ChannelPlan, *, max_candidates: int | None = None) -> list[DiscoveryUrlSpec]:
        cls.validate_plan_for_discovery(plan)
        source_platform = cls.infer_source_platform(plan)
        limit = plan.daily_url_limit if max_candidates is None else min(plan.daily_url_limit, max_candidates)
        keywords = [keyword for keyword in (plan.keywords or []) if str(keyword).strip()]
        if not keywords:
            keywords = [f"{plan.channel_type} dealer"]
        specs: list[DiscoveryUrlSpec] = []
        for keyword in keywords[:limit]:
            normalized_keyword = str(keyword).strip()
            specs.append(
                DiscoveryUrlSpec(
                    url=cls.build_discovery_url(
                        plan=plan,
                        keyword=normalized_keyword,
                        source_platform=source_platform,
                    ),
                    source_platform=source_platform,
                    keyword=normalized_keyword,
                    discovery_reason=(
                        f"根据渠道计划 {plan.channel_name}，使用关键词 {normalized_keyword}、城市 {plan.city}、"
                        f"渠道类型 {plan.channel_type} 生成公开发现候选 URL。"
                    ),
                )
            )
        return specs

    def run_discovery(self, *, plan_id: UUID, max_candidates: int | None = None) -> ChannelDiscoveryRunResult:
        plan = self.session.get(ChannelPlan, plan_id)
        if plan is None:
            raise ValueError("channel plan 不存在。")
        self.validate_plan_for_discovery(plan)
        policy = self.resolve_discovery_policy(plan)
        task_text = self.build_task_text(plan)
        specs = self.build_discovery_specs(plan, max_candidates=max_candidates)
        task = self.raw_collection_service.create_collection_task(
            plan_id=plan.id,
            task_type=policy.task_type,
            channel_name=plan.channel_name,
            risk_level=plan.risk_level,
            source_usage_type=policy.source_usage_type,
            max_sample_size=len(specs) if ChannelRiskLevel(plan.risk_level) == ChannelRiskLevel.HIGH else None,
            allowed_actions=task_text.allowed_actions,
            forbidden_actions=task_text.forbidden_actions,
        )
        candidates = [
            self.raw_collection_service.upsert_candidate_url(
                task_id=task.id,
                url=spec.url,
                source_platform=spec.source_platform,
                source_risk_level=plan.risk_level,
                source_usage_type=policy.source_usage_type,
                discovery_reason=spec.discovery_reason,
            )
            for spec in specs
        ]
        self.audit_service.record_agent_run(
            task_id=str(task.id),
            agent_name=self.AGENT_NAME,
            action=self.ACTION,
            input_ref=str(plan.id),
            output_ref=f"候选 URL {len(candidates)} 条；新增 {sum(1 for item in candidates if item.created)} 条",
            result="success",
        )
        return ChannelDiscoveryRunResult(task=task, candidates=candidates)
