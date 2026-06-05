import asyncio

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.main import app
from app.models.enums import LLMPromptTaskType, LLMPromptTemplateStatus
from app.models.llm_prompt_template import LLMPromptTemplate
from app.models.review_log import ReviewLog


client = TestClient(app)


def cleanup_prompt_governance_records(marker: str = "phase5_governance_api_") -> None:
    async def run_cleanup() -> None:
        async with AsyncSessionLocal() as async_session:
            def run(sync_session):
                template_ids = [
                    str(template_id)
                    for template_id in sync_session.scalars(
                        select(LLMPromptTemplate.id).where(LLMPromptTemplate.name.like(f"{marker}%"))
                    ).all()
                ]
                if template_ids:
                    sync_session.query(ReviewLog).filter(ReviewLog.task_id.in_(template_ids)).delete(
                        synchronize_session=False
                    )
                sync_session.query(ReviewLog).filter(ReviewLog.input_ref.like(f"{marker}%")).delete(
                    synchronize_session=False
                )
                sync_session.query(LLMPromptTemplate).filter(
                    LLMPromptTemplate.name.like(f"{marker}%")
                ).delete(synchronize_session=False)
                sync_session.commit()

            await async_session.run_sync(run)

    asyncio.run(run_cleanup())


@pytest.fixture(autouse=True)
def cleanup_phase5_prompt_governance_api_records():
    cleanup_prompt_governance_records()
    yield
    cleanup_prompt_governance_records()


def create_draft(name: str, *, provider: str = "phase5-governance", model: str = "permission-audit") -> str:
    response = client.post(
        "/llm-prompt-templates/drafts",
        json={
            "actor": "技术管理员",
            "actor_role": "tech_admin",
            "name": name,
            "task_type": "EMAIL_REPLY_DRAFT",
            "provider": provider,
            "model": model,
            "system_prompt": "EMAIL_REPLY 必须不自动发送，不编造，人工复核。",
            "user_prompt_template": "客户来信：{{customer_email}}",
            "output_schema_json": {"type": "object", "required": ["reply_body"]},
            "version": "draft-v1",
            "validation_status": "validation_passed",
        },
    )
    assert response.status_code == 200
    return response.json()["id"]


def create_active_default(name: str, *, provider: str = "phase5-governance", model: str = "permission-audit") -> str:
    async def seed() -> str:
        async with AsyncSessionLocal() as async_session:
            def run(sync_session):
                template = LLMPromptTemplate(
                    name=name,
                    task_type=LLMPromptTaskType.EMAIL_REPLY_DRAFT,
                    provider=provider,
                    model=model,
                    system_prompt="active system",
                    user_prompt_template="active user",
                    output_schema_json={"type": "object"},
                    version="active-v1",
                    status=LLMPromptTemplateStatus.ACTIVE,
                    is_default=True,
                    created_by="seed",
                    validation_status="validation_passed",
                )
                sync_session.add(template)
                sync_session.commit()
                return str(template.id)

            return await async_session.run_sync(run)

    return asyncio.run(seed())


def test_phase5_prompt_governance_blocks_operator_and_sales_manager_from_editing_or_publishing() -> None:
    draft_id = create_draft("phase5_governance_api_role_block")

    operator_edit = client.patch(
        f"/llm-prompt-templates/drafts/{draft_id}",
        json={"actor": "运营", "actor_role": "operator", "system_prompt": "operator edit"},
    )
    sales_publish = client.post(
        f"/llm-prompt-templates/drafts/{draft_id}/publish",
        json={"actor": "销售主管", "actor_role": "sales_manager", "change_summary": "尝试发布"},
    )

    assert operator_edit.status_code == 403
    assert sales_publish.status_code == 403


def test_phase5_prompt_governance_allows_only_tech_admin_to_edit_output_schema() -> None:
    draft_id = create_draft("phase5_governance_api_schema_guard")

    admin_schema_edit = client.patch(
        f"/llm-prompt-templates/drafts/{draft_id}",
        json={
            "actor": "运营管理员",
            "actor_role": "admin",
            "output_schema_json": {"type": "object", "required": ["reply_body", "subject"]},
        },
    )
    tech_schema_edit = client.patch(
        f"/llm-prompt-templates/drafts/{draft_id}",
        json={
            "actor": "技术管理员",
            "actor_role": "tech_admin",
            "output_schema_json": {"type": "object", "required": ["reply_body", "subject"]},
            "change_summary": "技术管理员调整 schema",
        },
    )

    assert admin_schema_edit.status_code == 403
    assert tech_schema_edit.status_code == 200
    assert tech_schema_edit.json()["output_schema_json"]["required"] == ["reply_body", "subject"]


def test_phase5_prompt_governance_writes_audit_logs_for_publish_default_switch_and_rollback() -> None:
    old_id = create_active_default("phase5_governance_api_audit_old")
    draft_id = create_draft("phase5_governance_api_audit_new")
    publish = client.post(
        f"/llm-prompt-templates/drafts/{draft_id}/publish",
        json={"actor": "技术管理员", "actor_role": "tech_admin", "change_summary": "发布新版本"},
    )
    set_default = client.post(
        f"/llm-prompt-templates/{old_id}/set-default",
        json={"actor": "技术管理员", "actor_role": "tech_admin", "change_summary": "切回旧版本"},
    )
    rollback = client.post(
        f"/llm-prompt-templates/{old_id}/rollback",
        json={
            "actor": "技术管理员",
            "actor_role": "tech_admin",
            "rollback_to_template_id": draft_id,
            "change_summary": "基于新版本生成回滚草稿",
        },
    )

    assert publish.status_code == 200
    assert set_default.status_code == 200
    assert rollback.status_code == 200

    old_audit = client.get(f"/llm-prompt-templates/{old_id}/audit-logs")
    new_audit = client.get(f"/llm-prompt-templates/{draft_id}/audit-logs")

    assert old_audit.status_code == 200
    assert new_audit.status_code == 200
    old_actions = {item["action"] for item in old_audit.json()["items"]}
    new_actions = {item["action"] for item in new_audit.json()["items"]}
    assert "prompt_set_default" in old_actions
    assert "prompt_rollback" in old_actions
    assert "prompt_publish" in new_actions
    assert all(item["reviewer"] == "技术管理员" for item in old_audit.json()["items"] + new_audit.json()["items"])
