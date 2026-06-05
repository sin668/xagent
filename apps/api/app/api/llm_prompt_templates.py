from collections.abc import AsyncIterator
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models.enums import LLMPromptTaskType, LLMPromptTemplateStatus
from app.schemas.llm_prompt_template import (
    LLMPromptTemplateDraftCreate,
    LLMPromptTemplateDraftDetailResponse,
    LLMPromptTemplateDraftUpdate,
    LLMPromptTemplateListResponse,
    LLMPromptTemplateResponse,
)
from app.services.llm_prompt_templates import LLMPromptTemplateService


router = APIRouter(prefix="/llm-prompt-templates", tags=["llm-prompt-templates"])


async def get_async_session() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session


def serialize_template(template) -> LLMPromptTemplateResponse:
    return LLMPromptTemplateResponse.model_validate(template)


def serialize_draft_detail(template) -> LLMPromptTemplateDraftDetailResponse:
    response = LLMPromptTemplateDraftDetailResponse.model_validate(template)
    response.audit_summary = {
        "created_by": template.created_by,
        "published_by": template.published_by,
        "published_at": template.published_at.isoformat() if template.published_at else None,
        "created_at": template.created_at.isoformat(),
        "updated_at": template.updated_at.isoformat(),
        "source_file_path": template.source_file_path,
        "source_file_hash": template.source_file_hash,
        "migration_batch_id": template.migration_batch_id,
        "validation_status": template.validation_status,
    }
    return response


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


@router.post("/drafts", response_model=LLMPromptTemplateDraftDetailResponse)
async def create_llm_prompt_template_draft(
    request: LLMPromptTemplateDraftCreate,
    async_session: AsyncSession = Depends(get_async_session),
) -> LLMPromptTemplateDraftDetailResponse:
    def run(sync_session):
        service = LLMPromptTemplateService(sync_session)
        payload = request.model_dump(exclude={"actor", "actor_role"})
        try:
            template = service.create_draft(actor=request.actor, actor_role=request.actor_role, payload=payload)
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        sync_session.commit()
        return serialize_draft_detail(template)

    return await async_session.run_sync(run)


@router.get("/drafts/{template_id:uuid}", response_model=LLMPromptTemplateDraftDetailResponse)
async def get_llm_prompt_template_draft(
    template_id: UUID,
    async_session: AsyncSession = Depends(get_async_session),
) -> LLMPromptTemplateDraftDetailResponse:
    def run(sync_session):
        template = LLMPromptTemplateService(sync_session).get_template(template_id)
        if template is None:
            raise HTTPException(status_code=404, detail="Prompt template 不存在")
        if template.status != LLMPromptTemplateStatus.DRAFT:
            raise HTTPException(status_code=409, detail="该 Prompt template 不是 draft 状态")
        return serialize_draft_detail(template)

    return await async_session.run_sync(run)


@router.patch("/drafts/{template_id:uuid}", response_model=LLMPromptTemplateDraftDetailResponse)
async def update_llm_prompt_template_draft(
    template_id: UUID,
    request: LLMPromptTemplateDraftUpdate,
    async_session: AsyncSession = Depends(get_async_session),
) -> LLMPromptTemplateDraftDetailResponse:
    def run(sync_session):
        service = LLMPromptTemplateService(sync_session)
        payload = request.model_dump(exclude_unset=True)
        try:
            template = service.update_draft(template_id, actor_role=request.actor_role, payload=payload)
        except PermissionError as exc:
            raise HTTPException(status_code=409 if "draft" in str(exc) else 403, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        sync_session.commit()
        return serialize_draft_detail(template)

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
