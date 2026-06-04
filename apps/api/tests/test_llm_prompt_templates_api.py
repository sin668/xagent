import asyncio

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.main import app
from app.models.enums import LLMPromptTaskType
from app.models.llm_prompt_template import LLMPromptTemplate
from app.services.default_prompt_seed import SourceDiscoveryDefaultPromptSeed


client = TestClient(app)


async def seed_source_discovery_prompt() -> str:
    async with AsyncSessionLocal() as async_session:
        def seed(sync_session):
            template = SourceDiscoveryDefaultPromptSeed.seed(
                sync_session,
                provider="deepseek",
                model="deepseek-chat",
            )
            sync_session.flush()
            return str(template.id)

        template_id = await async_session.run_sync(seed)
        await async_session.commit()
        return template_id


@pytest.fixture()
def seeded_source_discovery_prompt() -> str:
    return asyncio.run(seed_source_discovery_prompt())


def test_list_llm_prompt_templates_supports_filters(seeded_source_discovery_prompt: str) -> None:
    response = client.get(
        "/llm-prompt-templates",
        params={"task_type": "SOURCE_DISCOVERY", "status": "active", "is_default": "true"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= 1
    assert len(body["items"]) >= 1
    assert all(item["task_type"] == "SOURCE_DISCOVERY" for item in body["items"])
    assert all(item["status"] == "active" for item in body["items"])
    assert all(item["is_default"] is True for item in body["items"])
    assert any(item["id"] == seeded_source_discovery_prompt for item in body["items"])


def test_get_llm_prompt_template_detail_returns_schema_and_prompt_without_api_key(
    seeded_source_discovery_prompt: str,
) -> None:
    response = client.get(f"/llm-prompt-templates/{seeded_source_discovery_prompt}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == seeded_source_discovery_prompt
    assert body["name"] == "source_discovery_default"
    assert body["task_type"] == "SOURCE_DISCOVERY"
    assert body["version"] == "v1.0"
    assert body["output_schema_json"]["properties"]["candidates"]["type"] == "array"
    assert "不抽取客户" in body["system_prompt"]
    assert "api_key" not in body
    assert "secret" not in str(body).lower()


def test_get_llm_prompt_template_detail_returns_404_for_unknown_id() -> None:
    response = client.get("/llm-prompt-templates/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404


def test_prompt_template_api_is_read_only_for_phase_two() -> None:
    openapi = client.get("/openapi.json").json()
    path_methods = openapi["paths"]["/llm-prompt-templates"].keys()
    detail_path_methods = openapi["paths"]["/llm-prompt-templates/{template_id}"].keys()

    assert set(path_methods) == {"get"}
    assert set(detail_path_methods) == {"get"}


def test_prompt_template_filters_exclude_non_matching_task_type() -> None:
    asyncio.run(seed_source_discovery_prompt())

    response = client.get("/llm-prompt-templates", params={"task_type": "LEAD_EXTRACTION"})

    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["total"] == 0
