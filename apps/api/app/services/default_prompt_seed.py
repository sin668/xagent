from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import LLMPromptTaskType, LLMPromptTemplateStatus
from app.models.llm_prompt_template import LLMPromptTemplate
from app.services.llm_prompt_templates import LLMPromptTemplateService


SOURCE_DISCOVERY_DEFAULT_NAME = "source_discovery_query_planner_default"
SOURCE_DISCOVERY_DEFAULT_VERSION = "runtime-db-v1"


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
            "你是海外车辆采购 AI 获客系统的 Source Discovery 来源发现 Agent。"
            "你的任务是基于公开、无需登录、无需验证码、无需绕过反爬的 Low/Medium/High 风险渠道策略，"
            "主动生成公开搜索查询，并尽可能给出可人工核验的公开线索来源候选。"
            "只发现来源，不抽取客户，不自动触达，不生成私信，不绕过登录，不绕过验证码，不绕过反爬，不绕过平台限制。"
            "High 风险来源只允许进入人工复核；Forbidden 来源必须进入 blocked_candidates，不得进入 candidates。"
            "缺失信息输出空数组，不得编造。"
        )

    @staticmethod
    def _user_prompt_template() -> str:
        return (
            "目标市场：{{market}}\n"
            "渠道策略：{{channel_strategy}}\n"
            "规则兜底查询：{{fallback_queries}}\n"
            "请扩展 3 到 8 条可用于公开搜索的来源发现查询，并给出你能基于公开常识和公开入口建议人工核验的来源候选。"
            "候选必须包含 source_url、platform、risk_level、discovery_reason、evidence_note。"
            "不确定的字段用 Unknown；不得编造具体客户或联系方式；只输出 JSON。"
        )

    @staticmethod
    def _output_schema() -> dict[str, Any]:
        return {
            "type": "object",
            "additionalProperties": False,
            "required": ["queries", "candidates", "blocked_candidates"],
            "properties": {
                "queries": {"type": "array", "items": {"type": "string"}},
                "candidates": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": [
                            "source_url",
                            "platform",
                            "risk_level",
                            "discovery_reason",
                            "evidence_note",
                        ],
                        "properties": {
                            "source_url": {"type": "string"},
                            "platform": {"type": "string"},
                            "risk_level": {"type": "string", "enum": ["low", "medium", "high"]},
                            "discovery_reason": {"type": "string"},
                            "evidence_note": {"type": "string"},
                            "source_type": {
                                "type": "string",
                                "enum": ["official_website", "public_directory", "public_social", "marketplace", "unknown"],
                            },
                            "discovery_query": {"type": ["string", "null"]},
                        },
                    },
                },
                "blocked_candidates": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": True,
                        "properties": {
                            "source_url": {"type": "string"},
                            "reason": {"type": "string"},
                        },
                    },
                },
            },
        }
