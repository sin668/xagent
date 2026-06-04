from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AIAuditLog, ChannelRiskRule
from app.models.enums import AITaskType, ChannelRiskLevel, SourceUsageType
from app.services.audit_risk import AuditRiskLogService


@dataclass(frozen=True)
class ChannelRiskDecision:
    allowed: bool
    channel_name: str
    risk_level: str
    block_reason: str | None = None
    audit_logged: bool = False


class ChannelActionPolicyValidator:
    GLOBAL_FORBIDDEN_ACTIONS = {
        "login",
        "message",
        "friend_request",
        "join_group",
        "scrape_comments",
        "scrape_followers",
        "bypass_rate_limit",
    }
    HIGH_ALLOWED_ACTIONS = {
        "read_public_page",
        "extract_business_contact",
        "capture_limited_evidence",
    }

    @classmethod
    def evaluate(
        cls,
        *,
        risk_level: str | ChannelRiskLevel,
        requested_action: str,
        allowed_actions: str,
        forbidden_actions: str,
        source_usage_type: str | SourceUsageType | None,
    ) -> ChannelRiskDecision:
        risk = ChannelRiskLevel(risk_level)
        action = cls.normalize_action(requested_action)
        usage = cls.resolve_source_usage_type(risk, source_usage_type)

        if risk == ChannelRiskLevel.FORBIDDEN:
            return ChannelRiskDecision(False, "", risk.value, "Forbidden 渠道或行为禁止执行。")

        if action in cls.GLOBAL_FORBIDDEN_ACTIONS:
            return ChannelRiskDecision(False, "", risk.value, f"请求动作 {action} 属于全局禁止动作。")

        if cls.action_matches_list(action, forbidden_actions):
            return ChannelRiskDecision(False, "", risk.value, f"请求动作命中渠道禁止动作：{requested_action}")

        if risk == ChannelRiskLevel.HIGH:
            if usage != SourceUsageType.PUBLIC_DISCOVERY_ONLY:
                return ChannelRiskDecision(False, "", risk.value, "High 渠道必须使用 public_discovery_only。")
            if action not in cls.HIGH_ALLOWED_ACTIONS:
                return ChannelRiskDecision(
                    False,
                    "",
                    risk.value,
                    "High 风险渠道只允许只读公开动作：read_public_page、extract_business_contact、capture_limited_evidence。",
                )

        if not cls.action_matches_list(action, allowed_actions):
            return ChannelRiskDecision(False, "", risk.value, f"请求动作 {requested_action} 不在渠道允许动作列表。")

        return ChannelRiskDecision(True, "", risk.value)

    @staticmethod
    def normalize_action(requested_action: str) -> str:
        return requested_action.strip().lower().replace("-", "_").replace(" ", "_")

    @staticmethod
    def split_action_list(actions: str) -> list[str]:
        normalized = actions.replace("；", ";").replace("、", ";").replace(",", ";").replace("\n", ";")
        return [part.strip().lower().replace("-", "_").replace(" ", "_") for part in normalized.split(";") if part.strip()]

    @classmethod
    def action_matches_list(cls, action: str, actions: str) -> bool:
        if not action:
            return False
        return any(part == action or part in action or action in part for part in cls.split_action_list(actions))

    @staticmethod
    def resolve_source_usage_type(
        risk_level: ChannelRiskLevel,
        source_usage_type: str | SourceUsageType | None,
    ) -> SourceUsageType:
        if source_usage_type is not None:
            return SourceUsageType(source_usage_type)
        return (
            SourceUsageType.PUBLIC_DISCOVERY_ONLY
            if risk_level == ChannelRiskLevel.HIGH
            else SourceUsageType.AUTOMATIC_COLLECTION
        )


class ChannelRiskService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_rules(self) -> list[ChannelRiskRule]:
        return list(self.session.scalars(select(ChannelRiskRule).order_by(ChannelRiskRule.channel_name)).all())

    def get_rule(self, channel_name: str) -> ChannelRiskRule | None:
        return self.session.scalar(select(ChannelRiskRule).where(ChannelRiskRule.channel_name == channel_name))

    def upsert_rule(
        self,
        *,
        channel_name: str,
        channel_type: str,
        risk_level: str,
        allowed_actions: str,
        forbidden_actions: str,
        policy_source_url: str | None = None,
        notes: str | None = None,
        external_id: str | None = None,
        collection_allowed: bool | None = None,
        updated_by: str | None = None,
    ) -> ChannelRiskRule:
        risk = ChannelRiskLevel(risk_level)
        rule = self.get_rule(channel_name)
        if rule is None:
            rule = ChannelRiskRule(channel_name=channel_name)
            self.session.add(rule)

        rule.external_id = external_id or rule.external_id
        rule.channel_name = channel_name
        rule.channel_type = channel_type
        rule.risk_level = risk
        if risk in {ChannelRiskLevel.HIGH, ChannelRiskLevel.FORBIDDEN}:
            rule.collection_allowed = False
        else:
            rule.collection_allowed = self._default_collection_allowed(risk) if collection_allowed is None else collection_allowed
        rule.ai_processing_allowed = risk in {ChannelRiskLevel.LOW, ChannelRiskLevel.MEDIUM}
        rule.allowed_actions = allowed_actions
        rule.forbidden_actions = forbidden_actions
        rule.policy_source_url = policy_source_url
        rule.notes = notes
        rule.updated_by = updated_by or rule.updated_by or "unknown"
        rule.updated_at = datetime.utcnow()
        return rule

    def evaluate_ai_task(
        self,
        *,
        channel_name: str,
        task_type: str,
        requested_action: str,
        source_usage_type: str | SourceUsageType | None = None,
        source_url: str | None,
        model_name: str,
        prompt_version: str,
    ) -> ChannelRiskDecision:
        rule = self.get_rule(channel_name)
        if rule is None:
            reason = f"渠道 {channel_name} 未配置风险规则，AI 任务不可执行。"
            self._record_blocked_audit(
                task_type=task_type,
                source_url=source_url,
                model_name=model_name,
                prompt_version=prompt_version,
                channel_name=channel_name,
                requested_action=requested_action,
                risk_level=None,
                reason=reason,
            )
            return ChannelRiskDecision(False, channel_name, "Unknown", reason, True)

        decision = ChannelActionPolicyValidator.evaluate(
            risk_level=rule.risk_level,
            requested_action=requested_action,
            allowed_actions=rule.allowed_actions,
            forbidden_actions=rule.forbidden_actions,
            source_usage_type=source_usage_type,
        )

        if decision.allowed:
            return ChannelRiskDecision(True, channel_name, rule.risk_level.value)

        self._record_blocked_audit(
            task_type=task_type,
            source_url=source_url,
            model_name=model_name,
            prompt_version=prompt_version,
            channel_name=channel_name,
            requested_action=requested_action,
            risk_level=rule.risk_level.value,
            reason=decision.block_reason or "",
        )
        return ChannelRiskDecision(False, channel_name, rule.risk_level.value, decision.block_reason, True)

    @staticmethod
    def _default_collection_allowed(risk: ChannelRiskLevel) -> bool:
        return risk in {ChannelRiskLevel.LOW, ChannelRiskLevel.MEDIUM}

    def _record_blocked_audit(
        self,
        *,
        task_type: str,
        source_url: str | None,
        model_name: str,
        prompt_version: str,
        channel_name: str,
        requested_action: str,
        risk_level: str | None,
        reason: str,
    ) -> None:
        self.session.add(
            AIAuditLog(
                task_type=AITaskType(task_type),
                model_name=model_name,
                prompt_version=prompt_version,
                source_url=source_url,
                source_urls=[source_url] if source_url else [],
                input_payload={
                    "channel_name": channel_name,
                    "requested_action": requested_action,
                    "risk_level": risk_level,
                },
                output_payload={"allowed": False, "block_reason": reason},
                output_json={"allowed": False, "block_reason": reason},
                risk_blocked=True,
                risk_block_reason=reason,
                executed_at=datetime.utcnow(),
            )
        )
        AuditRiskLogService(self.session).record_risk_event(
            channel=channel_name,
            risk_level=risk_level or ChannelRiskLevel.FORBIDDEN.value,
            event_type="rule_block",
            block_reason=reason,
            action=requested_action,
            input_ref=source_url,
            result="blocked",
        )
