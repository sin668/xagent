import asyncio

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.main import app
from app.models.enums import LLMPromptTaskType, LLMPromptTemplateStatus
from app.models.llm_prompt_template import LLMPromptTemplate


client = TestClient(app)


def cleanup_prompt_draft_records(marker: str) -> None:
    async def run_cleanup() -> None:
        async with AsyncSessionLocal() as async_session:
            def run(sync_session):
                sync_session.query(LLMPromptTemplate).filter(
                    LLMPromptTemplate.name.like(f"{marker}%")
                ).delete(synchronize_session=False)
                sync_session.commit()

            await async_session.run_sync(run)

    asyncio.run(run_cleanup())


@pytest.fixture(autouse=True)
def cleanup_phase5_prompt_draft_api_records():
    marker = "phase5_draft_api_"
    cleanup_prompt_draft_records(marker)
    yield
    cleanup_prompt_draft_records(marker)


def create_active_prompt_template() -> str:
    async def seed() -> str:
        async with AsyncSessionLocal() as async_session:
            def run(sync_session):
                template = LLMPromptTemplate(
                    name="phase5_draft_api_active",
                    task_type=LLMPromptTaskType.EMAIL_REPLY_DRAFT,
                    provider="phase5-draft-api",
                    model="active-edit-guard",
                    system_prompt="active system",
                    user_prompt_template="active user",
                    output_schema_json={"type": "object"},
                    version="active-v1",
                    status=LLMPromptTemplateStatus.ACTIVE,
                    is_default=True,
                    source_file_path="prompts/email-reply-active.md",
                    source_file_hash="active-hash",
                    validation_status="validation_passed",
                )
                sync_session.add(template)
                sync_session.commit()
                return str(template.id)

            return await async_session.run_sync(run)

    return asyncio.run(seed())


def test_phase5_prompt_draft_api_creates_draft_with_admin_role_and_returns_audit_fields() -> None:
    response = client.post(
        "/llm-prompt-templates/drafts",
        json={
            "actor": "运营管理员",
            "actor_role": "admin",
            "name": "phase5_draft_api_create",
            "task_type": "EMAIL_REPLY_DRAFT",
            "provider": "deepseek",
            "model": "deepseek-chat",
            "system_prompt": "system draft",
            "user_prompt_template": "user draft",
            "output_schema_json": {"type": "object"},
            "version": "draft-v1",
            "source_file_path": "prompts/email-reply-draft.md",
            "source_file_hash": "draft-hash",
            "change_summary": "创建草稿",
            "validation_status": "validation_passed",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "draft"
    assert body["is_default"] is False
    assert body["version"] == "draft-v1"
    assert body["source_file_hash"] == "draft-hash"
    assert body["validation_status"] == "validation_passed"
    assert body["change_summary"] == "创建草稿"
    assert body["created_by"] == "运营管理员"


def test_phase5_prompt_draft_api_requires_admin_or_tech_admin_role() -> None:
    response = client.post(
        "/llm-prompt-templates/drafts",
        json={
            "actor": "客服",
            "actor_role": "customer_service",
            "name": "phase5_draft_api_forbidden",
            "task_type": "EMAIL_REPLY_DRAFT",
            "provider": "deepseek",
            "model": "deepseek-chat",
            "system_prompt": "system draft",
            "user_prompt_template": "user draft",
            "output_schema_json": {"type": "object"},
            "version": "draft-v1",
        },
    )

    assert response.status_code == 403


def test_phase5_prompt_draft_api_edits_only_draft_templates() -> None:
    create_response = client.post(
        "/llm-prompt-templates/drafts",
        json={
            "actor": "技术管理员",
            "actor_role": "tech_admin",
            "name": "phase5_draft_api_edit",
            "task_type": "EMAIL_REPLY_DRAFT",
            "provider": "deepseek",
            "model": "deepseek-chat",
            "system_prompt": "system before",
            "user_prompt_template": "user before",
            "output_schema_json": {"type": "object"},
            "version": "draft-v1",
        },
    )
    assert create_response.status_code == 200
    template_id = create_response.json()["id"]

    update_response = client.patch(
        f"/llm-prompt-templates/drafts/{template_id}",
        json={
            "actor": "技术管理员",
            "actor_role": "tech_admin",
            "system_prompt": "system after",
            "change_summary": "编辑草稿",
            "validation_status": "validation_failed",
            "validation_errors_json": {"schema": "缺少 required"},
        },
    )

    assert update_response.status_code == 200
    body = update_response.json()
    assert body["system_prompt"] == "system after"
    assert body["change_summary"] == "编辑草稿"
    assert body["validation_status"] == "validation_failed"
    assert body["validation_errors_json"] == {"schema": "缺少 required"}

    active_id = create_active_prompt_template()
    active_update = client.patch(
        f"/llm-prompt-templates/drafts/{active_id}",
        json={"actor": "技术管理员", "actor_role": "tech_admin", "system_prompt": "do not edit active"},
    )
    assert active_update.status_code == 409


def test_phase5_prompt_draft_detail_returns_source_hash_validation_and_audit_summary() -> None:
    create_response = client.post(
        "/llm-prompt-templates/drafts",
        json={
            "actor": "运营管理员",
            "actor_role": "admin",
            "name": "phase5_draft_api_detail",
            "task_type": "EMAIL_REPLY_DRAFT",
            "provider": "deepseek",
            "model": "deepseek-chat",
            "system_prompt": "system detail",
            "user_prompt_template": "user detail",
            "output_schema_json": {"type": "object"},
            "version": "draft-v1",
            "source_file_hash": "detail-hash",
            "validation_status": "validation_passed",
        },
    )
    template_id = create_response.json()["id"]

    detail = client.get(f"/llm-prompt-templates/drafts/{template_id}")

    assert detail.status_code == 200
    body = detail.json()
    assert body["id"] == template_id
    assert body["status"] == "draft"
    assert body["source_file_hash"] == "detail-hash"
    assert body["validation_status"] == "validation_passed"
    assert body["audit_summary"]["created_by"] == "运营管理员"
    assert "updated_at" in body["audit_summary"]
