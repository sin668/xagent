import asyncio

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.main import app
from app.models.enums import LLMPromptTaskType, LLMPromptTemplateStatus
from app.models.llm_prompt_template import LLMPromptTemplate


client = TestClient(app)


def cleanup_prompt_publish_records(marker: str = "phase5_publish_api_") -> None:
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
def cleanup_phase5_prompt_publish_api_records():
    cleanup_prompt_publish_records()
    yield
    cleanup_prompt_publish_records()


def create_draft(name: str, *, version: str = "draft-v1", validation_status: str = "validation_passed") -> str:
    response = client.post(
        "/llm-prompt-templates/drafts",
        json={
            "actor": "技术管理员",
            "actor_role": "tech_admin",
            "name": name,
            "task_type": "EMAIL_REPLY_DRAFT",
            "provider": "deepseek",
            "model": "deepseek-chat",
            "system_prompt": "EMAIL_REPLY 必须保留风险边界，不自动发送，不编造，必须人工复核。",
            "user_prompt_template": "客户来信：{{customer_email}}",
            "output_schema_json": {"type": "object", "required": ["reply_body"]},
            "version": version,
            "validation_status": validation_status,
        },
    )
    assert response.status_code == 200
    return response.json()["id"]


def create_active_default(name: str, *, version: str = "active-v1") -> str:
    async def seed() -> str:
        async with AsyncSessionLocal() as async_session:
            def run(sync_session):
                template = LLMPromptTemplate(
                    name=name,
                    task_type=LLMPromptTaskType.EMAIL_REPLY_DRAFT,
                    provider="deepseek",
                    model="deepseek-chat",
                    system_prompt="active system",
                    user_prompt_template="active user",
                    output_schema_json={"type": "object"},
                    version=version,
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


def active_default_count() -> int:
    async def count_rows() -> int:
        async with AsyncSessionLocal() as async_session:
            def run(sync_session):
                return sync_session.scalar(
                    select(LLMPromptTemplate)
                    .where(LLMPromptTemplate.task_type == LLMPromptTaskType.EMAIL_REPLY_DRAFT)
                    .where(LLMPromptTemplate.provider == "deepseek")
                    .where(LLMPromptTemplate.model == "deepseek-chat")
                    .where(LLMPromptTemplate.status == LLMPromptTemplateStatus.ACTIVE)
                    .where(LLMPromptTemplate.is_default.is_(True))
                    .limit(1)
                )

            first = await async_session.run_sync(run)
            if first is None:
                return 0
            def count(sync_session):
                return len(
                    sync_session.scalars(
                        select(LLMPromptTemplate)
                        .where(LLMPromptTemplate.task_type == LLMPromptTaskType.EMAIL_REPLY_DRAFT)
                        .where(LLMPromptTemplate.provider == "deepseek")
                        .where(LLMPromptTemplate.model == "deepseek-chat")
                        .where(LLMPromptTemplate.status == LLMPromptTemplateStatus.ACTIVE)
                        .where(LLMPromptTemplate.is_default.is_(True))
                    ).all()
                )
            return await async_session.run_sync(count)

    return asyncio.run(count_rows())


def test_phase5_prompt_publish_api_publishes_validated_draft_as_active_default_and_writes_audit() -> None:
    old_active_id = create_active_default("phase5_publish_api_old_active")
    draft_id = create_draft("phase5_publish_api_new_draft", version="new-v1")

    response = client.post(
        f"/llm-prompt-templates/drafts/{draft_id}/publish",
        json={"actor": "技术管理员", "actor_role": "tech_admin", "change_summary": "发布新版本"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == draft_id
    assert body["status"] == "active"
    assert body["is_default"] is True
    assert body["published_by"] == "技术管理员"
    assert body["published_at"] is not None
    assert body["change_summary"] == "发布新版本"
    assert active_default_count() == 1

    old_detail = client.get(f"/llm-prompt-templates/{old_active_id}").json()
    assert old_detail["status"] == "paused"
    assert old_detail["is_default"] is False


def test_phase5_prompt_publish_api_rejects_unvalidated_draft() -> None:
    draft_id = create_draft("phase5_publish_api_invalid_draft", validation_status="validation_failed")

    response = client.post(
        f"/llm-prompt-templates/drafts/{draft_id}/publish",
        json={"actor": "技术管理员", "actor_role": "tech_admin", "change_summary": "尝试发布"},
    )

    assert response.status_code == 409
    detail = client.get(f"/llm-prompt-templates/drafts/{draft_id}").json()
    assert detail["status"] == "draft"


def test_phase5_prompt_default_switch_api_allows_one_default_active_per_task_provider_model() -> None:
    first_id = create_active_default("phase5_publish_api_default_first", version="active-v1")
    second_id = create_draft("phase5_publish_api_default_second", version="active-v2")
    publish = client.post(
        f"/llm-prompt-templates/drafts/{second_id}/publish",
        json={"actor": "技术管理员", "actor_role": "tech_admin", "change_summary": "发布第二版"},
    )
    assert publish.status_code == 200

    response = client.post(
        f"/llm-prompt-templates/{first_id}/set-default",
        json={"actor": "技术管理员", "actor_role": "tech_admin", "change_summary": "切回第一版"},
    )

    assert response.status_code == 200
    assert response.json()["id"] == first_id
    assert response.json()["status"] == "active"
    assert response.json()["is_default"] is True
    assert active_default_count() == 1
    second_detail = client.get(f"/llm-prompt-templates/{second_id}").json()
    assert second_detail["is_default"] is False


def test_phase5_prompt_rollback_api_creates_auditable_draft_from_active_history() -> None:
    old_active_id = create_active_default("phase5_publish_api_rollback_old", version="active-v1")
    new_draft_id = create_draft("phase5_publish_api_rollback_new", version="active-v2")
    publish = client.post(
        f"/llm-prompt-templates/drafts/{new_draft_id}/publish",
        json={"actor": "技术管理员", "actor_role": "tech_admin", "change_summary": "发布第二版"},
    )
    assert publish.status_code == 200

    response = client.post(
        f"/llm-prompt-templates/{new_draft_id}/rollback",
        json={"actor": "技术管理员", "actor_role": "tech_admin", "rollback_to_template_id": old_active_id, "change_summary": "回滚到第一版"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "draft"
    assert body["is_default"] is False
    assert body["rollback_from_template_id"] == new_draft_id
    assert body["parent_template_id"] == old_active_id
    assert body["change_summary"] == "回滚到第一版"

    old_detail = client.get(f"/llm-prompt-templates/{old_active_id}").json()
    new_detail = client.get(f"/llm-prompt-templates/{new_draft_id}").json()
    assert old_detail["id"] == old_active_id
    assert new_detail["id"] == new_draft_id
