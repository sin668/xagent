from collections.abc import AsyncIterator
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models.enums import LLMPromptTaskType, LLMPromptTemplateStatus
from app.schemas.llm_prompt_template import LLMPromptTemplateListResponse, LLMPromptTemplateResponse
from app.services.llm_prompt_templates import LLMPromptTemplateService


router = APIRouter(prefix="/llm-prompt-templates", tags=["llm-prompt-templates"])


async def get_async_session() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session


def serialize_template(template) -> LLMPromptTemplateResponse:
    return LLMPromptTemplateResponse.model_validate(template)


@router.get("", response_model=LLMPromptTemplateListResponse)
async def list_llm_prompt_templates(
    task_type: LLMPromptTaskType | None = Query(default=None),
    status: LLMPromptTemplateStatus | None = Query(default=None),
    is_default: bool | None = Query(default=None),
    async_session: AsyncSession = Depends(get_async_session),
) -> LLMPromptTemplateListResponse:
    def run(sync_session):
        service = LLMPromptTemplateService(sync_session)
        items = [
            serialize_template(template)
            for template in service.list_templates(task_type=task_type, status=status, is_default=is_default)
        ]
        return LLMPromptTemplateListResponse(items=items, total=len(items))

    return await async_session.run_sync(run)


@router.get("/{template_id:uuid}", response_model=LLMPromptTemplateResponse)
async def get_llm_prompt_template(
    template_id: UUID,
    async_session: AsyncSession = Depends(get_async_session),
) -> LLMPromptTemplateResponse:
    def run(sync_session):
        template = LLMPromptTemplateService(sync_session).get_template(template_id)
        if template is None:
            raise HTTPException(status_code=404, detail="Prompt template 不存在")
        return serialize_template(template)

    return await async_session.run_sync(run)
