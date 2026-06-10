"""Seed agent runtime prompt templates.

Revision ID: 20260608_0037
Revises: 20260605_0036
Create Date: 2026-06-08
"""

from __future__ import annotations

import json
from uuid import uuid4

from alembic import op
import sqlalchemy as sa


revision = "20260608_0037"
down_revision = "20260605_0036"
branch_labels = None
depends_on = None


TASK_TYPE_VALUES = ("DEEP_ENRICHMENT", "LEAD_CLEANUP", "EMAIL_REPLY")
PROVIDER = "deepseek"
MODEL = "deepseek-chat"
VERSION = "runtime-db-v1"
CREATED_BY = "codex-20260608-runtime-prompt-seed"


def upgrade() -> None:
    context = op.get_context()
    with context.autocommit_block():
        for value in TASK_TYPE_VALUES:
            op.execute(sa.text(f"ALTER TYPE llmprompttasktype ADD VALUE IF NOT EXISTS '{value}'"))

    for payload in _default_prompt_payloads():
        _upsert_default_prompt(payload)


def downgrade() -> None:
    op.execute(
        sa.text(
            "DELETE FROM llm_prompt_templates "
            "WHERE created_by = :created_by AND version = :version"
        ).bindparams(created_by=CREATED_BY, version=VERSION)
    )


def _upsert_default_prompt(payload: dict) -> None:
    op.execute(
        sa.text(
            "UPDATE llm_prompt_templates "
            "SET status = 'paused', is_default = false "
            "WHERE task_type::text = :task_type "
            "AND provider = :provider "
            "AND model = :model "
            "AND status::text = 'active' "
            "AND is_default = true"
        ).bindparams(task_type=payload["task_type"], provider=payload["provider"], model=payload["model"])
    )
    op.execute(
        sa.text(
            "INSERT INTO llm_prompt_templates ("
            "id, name, task_type, provider, model, system_prompt, user_prompt_template, "
            "output_schema_json, version, status, is_default, created_by, change_summary, validation_status, "
            "created_at, updated_at"
            ") VALUES ("
            "CAST(:id AS uuid), :name, CAST(:task_type AS llmprompttasktype), :provider, :model, :system_prompt, :user_prompt_template, "
            "CAST(:output_schema_json AS jsonb), :version, CAST(:status AS llmprompttemplatestatus), "
            ":is_default, :created_by, :change_summary, :validation_status, now(), now()"
            ")"
        ).bindparams(
            id=str(uuid4()),
            name=payload["name"],
            task_type=payload["task_type"],
            provider=payload["provider"],
            model=payload["model"],
            system_prompt=payload["system_prompt"],
            user_prompt_template=payload["user_prompt_template"],
            output_schema_json=json.dumps(payload["output_schema_json"], ensure_ascii=False),
            version=payload["version"],
            status=payload["status"],
            is_default=payload["is_default"],
            created_by=payload["created_by"],
            change_summary=payload["change_summary"],
            validation_status=payload["validation_status"],
        )
    )


def _default_prompt_payloads() -> list[dict]:
    return [
        _payload(
            name="source_discovery_query_planner_default",
            task_type="SOURCE_DISCOVERY",
            system_prompt=(
                "你是海外车辆采购 AI 获客系统的 Source Discovery 来源发现 Agent。"
                "你的任务是基于公开、无需登录、无需验证码、无需绕过反爬的 Low/Medium/High 风险渠道策略，"
                "主动生成公开搜索查询，并尽可能给出可人工核验的公开线索来源候选。"
                "只发现来源，不抽取客户，不自动触达，不生成私信，不绕过登录，不绕过验证码，不绕过反爬，不绕过平台限制。"
                "High 风险来源只允许进入人工复核；Forbidden 来源必须进入 blocked_candidates，不得进入 candidates。"
                "缺失信息输出空数组，不得编造。"
            ),
            user_prompt_template=(
                "目标市场：{{market}}\n"
                "渠道策略：{{channel_strategy}}\n"
                "规则兜底查询：{{fallback_queries}}\n"
                "请扩展 3 到 8 条可用于公开搜索的来源发现查询，并给出你能基于公开常识和公开入口建议人工核验的来源候选。"
                "候选必须包含 source_url、platform、risk_level、discovery_reason、evidence_note。"
                "不确定的字段用 Unknown；不得编造具体客户或联系方式；只输出 JSON。"
            ),
            output_schema_json={
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
                                    "enum": [
                                        "official_website",
                                        "public_directory",
                                        "public_social",
                                        "marketplace",
                                        "unknown",
                                    ],
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
            },
        ),
        _payload(
            name="lead_extraction_runtime_default",
            task_type="LEAD_EXTRACTION",
            system_prompt=(
                "你是公开网页线索抽取 Agent。只从输入的公开文本抽取字段；缺失字段必须返回 null，禁止编造。"
                "你必须尽可能抽取来源中出现的多个客户/门店/业务主体，以及每个主体的全部公开联系方式。"
                "联系方式包括 email、phone、WhatsApp、Telegram、VK、OK、TikTok、Max 等；联系方式、经营信号、城市和网站必须能在源文本中找到证据。"
            ),
            user_prompt_template=(
                "来源链接：{{source_url}}\n"
                "公开文本：\n{{source_content}}\n\n"
                "请输出 leads 数组；如果来源只包含一个客户，也必须输出一条 lead。"
                "每条 lead 的 contacts 数组必须包含该来源文本中能找到的全部邮箱、电话和社交软件联系方式，不能只返回第一个。"
                "为了兼容旧链路，每条 lead.fields.email 和 lead.fields.phone 分别填写该 lead 的第一个邮箱和第一个电话；缺失填 null。"
            ),
            output_schema_json={
                "type": "object",
                "additionalProperties": False,
                "required": ["leads"],
                "properties": {
                    "leads": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["fields", "contacts"],
                            "properties": {
                                "fields": {
                                    "type": "object",
                                    "additionalProperties": False,
                                    "properties": {
                                        "company_name": {"type": ["string", "null"]},
                                        "email": {"type": ["string", "null"]},
                                        "phone": {"type": ["string", "null"]},
                                        "country": {"type": ["string", "null"]},
                                        "city": {"type": ["string", "null"]},
                                        "vehicle_interest": {"type": ["string", "null"]},
                                        "export_intent": {"type": ["string", "null"]},
                                        "website": {"type": ["string", "null"]},
                                    },
                                },
                                "contacts": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "additionalProperties": False,
                                        "required": ["type", "value"],
                                        "properties": {
                                            "type": {
                                                "type": "string",
                                                "enum": [
                                                    "email",
                                                    "phone",
                                                    "whatsapp",
                                                    "telegram",
                                                    "vk",
                                                    "vkontakte",
                                                    "ok",
                                                    "odnoklassniki",
                                                    "tiktok",
                                                    "max",
                                                    "website",
                                                    "other",
                                                ],
                                            },
                                            "value": {"type": "string"},
                                            "usage": {"type": ["string", "null"]},
                                        },
                                    },
                                },
                            },
                        },
                    }
                },
            },
        ),
        _payload(
            name="lead_grading_runtime_default",
            task_type="LEAD_GRADING",
            system_prompt=(
                "你是线索分级解释 Agent。只能基于已抽取字段、硬规则推荐等级和原因生成解释。"
                "不得覆盖推荐等级，不得建议自动晋级客户，不得编造证据。"
            ),
            user_prompt_template=(
                "硬规则推荐等级：{{recommended_grade}}\n"
                "硬规则原因：{{reasons}}\n"
                "线索：{{lead}}\n"
                "请输出简洁解释。"
            ),
            output_schema_json={
                "type": "object",
                "additionalProperties": False,
                "required": ["explanations"],
                "properties": {"explanations": {"type": "object", "additionalProperties": {"type": "string"}}},
            },
        ),
        _payload(
            name="deep_enrichment_runtime_default",
            task_type="DEEP_ENRICHMENT",
            system_prompt=(
                "你是线索深挖补全 Agent。只从公开页面快照抽取候选字段。"
                "缺失字段返回空数组，禁止编造；每个候选必须包含 source_url 和 evidence_note。"
            ),
            user_prompt_template=(
                "线索快照：{{lead_snapshot}}\n"
                "缺失字段：{{missing_fields}}\n"
                "公开页面快照：{{page_snapshots}}\n"
                "请输出可人工复核的候选补全字段。"
            ),
            output_schema_json={
                "type": "object",
                "additionalProperties": False,
                "required": ["field_candidates"],
                "properties": {
                    "field_candidates": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": True,
                            "required": ["field_name", "candidate_value", "source_type", "source_url", "evidence_note"],
                            "properties": {
                                "field_name": {"type": "string"},
                                "candidate_value": {},
                                "source_type": {"type": "string"},
                                "source_url": {"type": ["string", "null"]},
                                "evidence_note": {"type": "string"},
                                "confidence_score": {"type": ["number", "null"]},
                            },
                        },
                    }
                },
            },
        ),
        _payload(
            name="lead_cleanup_runtime_default",
            task_type="LEAD_CLEANUP",
            system_prompt=(
                "你是 Watch/Invalid 线索清洗复核 Agent。只能输出人工复核建议，"
                "禁止自动删除、自动恢复 Invalid、自动执行清洗。"
            ),
            user_prompt_template="待清洗线索：{{leads}}\n请输出去重、误杀恢复或确认无效的人工复核建议。",
            output_schema_json={
                "type": "object",
                "additionalProperties": False,
                "required": ["suggestions"],
                "properties": {
                    "suggestions": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": True,
                            "required": ["staging_lead_id", "suggestion_type", "reason", "recommended_action"],
                            "properties": {
                                "staging_lead_id": {"type": "string"},
                                "suggestion_type": {
                                    "type": "string",
                                    "enum": [
                                        "strong_duplicate",
                                        "possible_duplicate",
                                        "merge_contact_method",
                                        "merge_source_evidence",
                                        "restore_from_watch",
                                        "confirm_invalid",
                                        "mark_abandoned",
                                        "needs_manual_review",
                                    ],
                                },
                                "target_lead_id": {"type": ["string", "null"]},
                                "confidence_score": {"type": ["number", "null"]},
                                "reason": {"type": "string"},
                                "evidence_json": {"type": "object"},
                                "recommended_action": {"type": "string"},
                            },
                        },
                    }
                },
            },
        ),
        _payload(
            name="email_reply_runtime_default",
            task_type="EMAIL_REPLY",
            system_prompt=(
                "你是海外车辆采购邮件回复 Agent。只能基于客户上下文和已审核知识生成结构化 JSON，"
                "不得编造事实，不得承诺价格、合同、税务、法律、交付或出口管制事项。"
                "缺失字段输出 Unknown、null 或空数组。不得写入业务 core 表。"
            ),
            user_prompt_template=(
                "客户上下文：{{context}}\n"
                "知识命中：{{knowledge_hits}}\n"
                "任务配置：{{prompt}}\n"
                "选项：{{options}}\n"
                "输出 schema_version=email-reply-v1；audit.writes_core_tables 必须为 false。"
            ),
            output_schema_json={
                "type": "object",
                "additionalProperties": True,
                "required": [
                    "schema_version",
                    "reply_language",
                    "suggested_subject",
                    "suggested_body",
                    "auto_send_allowed",
                    "manual_review_required",
                    "next_action",
                    "audit",
                ],
                "properties": {
                    "schema_version": {"type": "string", "const": "email-reply-v1"},
                    "reply_language": {"type": "string"},
                    "detected_language": {"type": ["string", "null"]},
                    "suggested_subject": {"type": "string"},
                    "suggested_body": {"type": "string"},
                    "knowledge_hits": {"type": "array"},
                    "risk_flags": {"type": "array", "items": {"type": "string"}},
                    "auto_send_allowed": {"type": "boolean"},
                    "manual_review_required": {"type": "boolean"},
                    "next_action": {"type": "string"},
                    "audit": {"type": "object"},
                },
            },
        ),
    ]


def _payload(*, name: str, task_type: str, system_prompt: str, user_prompt_template: str, output_schema_json: dict) -> dict:
    return {
        "name": name,
        "task_type": task_type,
        "provider": PROVIDER,
        "model": MODEL,
        "system_prompt": system_prompt,
        "user_prompt_template": user_prompt_template,
        "output_schema_json": output_schema_json,
        "version": VERSION,
        "status": "active",
        "is_default": True,
        "created_by": CREATED_BY,
        "change_summary": "Agent runtime prompts are seeded into PostgreSQL; runtime must not read local prompt files.",
        "validation_status": "passed",
    }
