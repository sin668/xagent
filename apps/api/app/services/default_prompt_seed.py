from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import LLMPromptTaskType, LLMPromptTemplateStatus
from app.models.llm_prompt_template import LLMPromptTemplate
from app.services.llm_prompt_templates import LLMPromptTemplateService


SOURCE_DISCOVERY_DEFAULT_NAME = "source_discovery_default"
SOURCE_DISCOVERY_DEFAULT_VERSION = "v1.0"


class SourceDiscoveryDefaultPromptSeed:
    @classmethod
    def build_payload(cls, *, provider: str, model: str) -> dict[str, Any]:
        return {
            "name": SOURCE_DISCOVERY_DEFAULT_NAME,
            "task_type": LLMPromptTaskType.SOURCE_DISCOVERY,
            "provider": provider,
            "model": model,
            "system_prompt": cls._system_prompt(),
            "user_prompt_template": cls._user_prompt_template(),
            "output_schema_json": cls._output_schema(),
            "version": SOURCE_DISCOVERY_DEFAULT_VERSION,
            "status": LLMPromptTemplateStatus.ACTIVE,
            "is_default": True,
            "created_by": "codex-phase-2-seed",
        }

    @classmethod
    def seed(cls, session: Session, *, provider: str, model: str) -> LLMPromptTemplate:
        existing = cls._find_existing_default(session, provider=provider, model=model)
        payload = cls.build_payload(provider=provider, model=model)

        if existing is not None:
            for field_name, value in payload.items():
                setattr(existing, field_name, value)
            session.add(existing)
            return existing

        existing_templates = [
            {
                "task_type": item.task_type,
                "provider": item.provider,
                "model": item.model,
                "status": item.status,
                "is_default": item.is_default,
            }
            for item in session.scalars(select(LLMPromptTemplate)).all()
        ]
        LLMPromptTemplateService.validate_default_template_uniqueness(
            existing_templates=existing_templates,
            task_type=payload["task_type"],
            provider=payload["provider"],
            model=payload["model"],
            status=payload["status"],
            is_default=payload["is_default"],
        )
        template = LLMPromptTemplate(**payload)
        session.add(template)
        return template

    @classmethod
    def _find_existing_default(cls, session: Session, *, provider: str, model: str) -> LLMPromptTemplate | None:
        return session.scalar(
            select(LLMPromptTemplate).where(
                LLMPromptTemplate.task_type == LLMPromptTaskType.SOURCE_DISCOVERY,
                LLMPromptTemplate.provider == provider,
                LLMPromptTemplate.model == model,
                LLMPromptTemplate.status == LLMPromptTemplateStatus.ACTIVE,
                LLMPromptTemplate.is_default.is_(True),
            )
        )

    @staticmethod
    def _system_prompt() -> str:
        return (
            "你是海外车辆采购 AI 获客系统的 Source Discovery Agent。"
            "你的唯一职责是发现潜在线索来源，不抽取客户名称、联系人、电话、邮箱或社交账号，"
            "不自动触达，不生成私信，不加好友，不发送短信或邮件。"
            "只能基于公开、无需登录、无需验证码、无需绕过反爬的页面和目录提出来源候选。"
            "不得绕过登录、不得绕过验证码、不得绕过反爬、不得绕过平台限制。"
            "High 风险来源只能进入人工复核，不得标记为自动抽取。"
            "Forbidden 来源必须进入 blocked_candidates，不得进入 candidates。"
            "缺失字段必须输出 Unknown、null 或空数组，不得编造 URL、平台、理由或证据。"
        )

    @staticmethod
    def _user_prompt_template() -> str:
        return (
            "请为国家 {country}、城市 {city}、渠道策略 {channel_strategy} 发现公开车辆经销商线索来源。"
            "只返回 JSON，不要输出解释文本。"
            "每个候选来源必须包含 source_url、platform、risk_level、discovery_reason、evidence_note。"
            "候选应优先来自官网、公开目录、搜索引擎结果、地图公开结果和公开行业页面。"
            "不抽取客户，不自动触达，不生成私信，不绕过登录，不绕过验证码，不绕过反爬，不绕过平台限制。"
            "High 风险来源必须标记为人工复核，approved_for_extraction 必须为 false。"
            "Forbidden 来源必须放入 blocked_candidates，并说明 blocked_reason。"
        )

    @staticmethod
    def _output_schema() -> dict[str, Any]:
        return {
            "type": "object",
            "additionalProperties": False,
            "required": ["task_type", "country", "city", "channel_strategy", "candidates", "blocked_candidates"],
            "properties": {
                "task_type": {"type": "string", "const": "SOURCE_DISCOVERY"},
                "country": {"type": "string"},
                "city": {"type": ["string", "null"]},
                "channel_strategy": {"type": "string"},
                "candidates": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": [
                            "source_url",
                            "platform",
                            "channel_name",
                            "country",
                            "city",
                            "risk_level",
                            "discovery_method",
                            "discovery_query",
                            "discovery_reason",
                            "evidence_note",
                            "evidence_links",
                            "confidence_score",
                            "recommended_review_status",
                            "approved_for_extraction",
                        ],
                        "properties": {
                            "source_url": {"type": "string"},
                            "platform": {"type": "string"},
                            "channel_name": {"type": "string"},
                            "country": {"type": "string"},
                            "city": {"type": ["string", "null"]},
                            "risk_level": {"type": "string", "enum": ["Low", "Medium", "High"]},
                            "discovery_method": {"type": "string"},
                            "discovery_query": {"type": ["string", "null"]},
                            "discovery_reason": {"type": "string"},
                            "evidence_note": {"type": "string"},
                            "evidence_links": {"type": "array", "items": {"type": "string"}},
                            "confidence_score": {"type": ["number", "null"], "minimum": 0, "maximum": 1},
                            "recommended_review_status": {
                                "type": "string",
                                "enum": ["auto_approved", "pending", "high_risk_review"],
                            },
                            "approved_for_extraction": {"type": "boolean"},
                        },
                    },
                },
                "blocked_candidates": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["source_url", "risk_level", "blocked_reason"],
                        "properties": {
                            "source_url": {"type": "string"},
                            "risk_level": {"type": "string", "enum": ["Forbidden", "High"]},
                            "blocked_reason": {"type": "string"},
                        },
                    },
                },
            },
        }
