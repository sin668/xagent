import asyncio

import pytest
from fastapi.testclient import TestClient

from app.db.session import AsyncSessionLocal
from app.main import app
from app.models.llm_prompt_template import LLMPromptTemplate


client = TestClient(app)


def cleanup_prompt_validation_records(marker: str = "phase5_validation_api_") -> None:
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
def cleanup_phase5_prompt_validation_api_records():
    cleanup_prompt_validation_records()
    yield
    cleanup_prompt_validation_records()


def create_draft(payload: dict) -> str:
    response = client.post(
        "/llm-prompt-templates/drafts",
        json={
            "actor": "技术管理员",
            "actor_role": "tech_admin",
            "name": payload.get("name", "phase5_validation_api_draft"),
            "task_type": payload.get("task_type", "EMAIL_REPLY_DRAFT"),
            "provider": "deepseek",
            "model": "deepseek-chat",
            "system_prompt": payload.get("system_prompt", "必须遵守风险边界，不自动发送，不编造。"),
            "user_prompt_template": payload.get("user_prompt_template", "客户来信：{{customer_email}}\n客户资料：{{customer_profile}}"),
            "output_schema_json": payload.get("output_schema_json", {"type": "object", "required": ["reply_body"]}),
            "version": "draft-v1",
            "validation_status": "validation_failed",
        },
    )
    assert response.status_code == 200
    return response.json()["id"]


def test_phase5_prompt_validation_preview_passes_valid_email_reply_prompt_and_updates_draft_status() -> None:
    template_id = create_draft(
        {
            "name": "phase5_validation_api_pass",
            "system_prompt": "EMAIL_REPLY 必须保留风险边界，不自动发送，不编造，必须人工复核。",
            "user_prompt_template": "客户来信：{{customer_email}}\n客户资料：{{customer_profile}}\n知识库：{{knowledge_context}}",
            "output_schema_json": {"type": "object", "required": ["reply_subject", "reply_body"]},
        }
    )

    response = client.post(
        f"/llm-prompt-templates/drafts/{template_id}/validation-preview",
        json={
            "actor": "技术管理员",
            "actor_role": "tech_admin",
            "sample_variables": {
                "customer_email": "客户询问车辆价格",
                "customer_profile": "俄罗斯车商",
                "knowledge_context": "付款和报价必须人工确认",
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["validation_status"] == "validation_passed"
    assert body["passed"] is True
    assert body["errors"] == {}
    assert "客户询问车辆价格" in body["rendered_user_prompt"]

    detail = client.get(f"/llm-prompt-templates/drafts/{template_id}").json()
    assert detail["validation_status"] == "validation_passed"
    assert detail["validation_errors_json"] is None


def test_phase5_prompt_validation_preview_fails_missing_required_variables_without_publish() -> None:
    template_id = create_draft(
        {
            "name": "phase5_validation_api_missing_variable",
            "user_prompt_template": "客户来信：{{customer_email}}\n客户资料：{{customer_profile}}",
        }
    )

    response = client.post(
        f"/llm-prompt-templates/drafts/{template_id}/validation-preview",
        json={
            "actor": "技术管理员",
            "actor_role": "tech_admin",
            "sample_variables": {"customer_email": "客户询问车辆价格"},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["passed"] is False
    assert body["validation_status"] == "validation_failed"
    assert body["errors"]["missing_variables"] == ["customer_profile"]
    assert body["would_publish"] is False

    detail = client.get(f"/llm-prompt-templates/drafts/{template_id}").json()
    assert detail["status"] == "draft"
    assert detail["validation_status"] == "validation_failed"


def test_phase5_prompt_validation_preview_requires_email_reply_risk_boundaries() -> None:
    template_id = create_draft(
        {
            "name": "phase5_validation_api_missing_risk",
            "system_prompt": "请生成礼貌邮件。",
            "user_prompt_template": "客户来信：{{customer_email}}",
        }
    )

    response = client.post(
        f"/llm-prompt-templates/drafts/{template_id}/validation-preview",
        json={
            "actor": "技术管理员",
            "actor_role": "tech_admin",
            "sample_variables": {"customer_email": "客户询问车辆价格"},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["passed"] is False
    assert "risk_boundaries" in body["errors"]
    assert "不自动发送" in body["errors"]["risk_boundaries"]
    assert "不编造" in body["errors"]["risk_boundaries"]


def test_phase5_prompt_validation_preview_requires_admin_or_tech_admin() -> None:
    template_id = create_draft({"name": "phase5_validation_api_forbidden"})

    response = client.post(
        f"/llm-prompt-templates/drafts/{template_id}/validation-preview",
        json={"actor": "客服", "actor_role": "customer_service", "sample_variables": {}},
    )

    assert response.status_code == 403
