from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import LLMPromptTaskType, LLMPromptTemplateStatus


class LLMPromptTemplateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    task_type: LLMPromptTaskType
    provider: str = Field(min_length=1, max_length=80)
    model: str = Field(min_length=1, max_length=120)
    system_prompt: str = Field(min_length=1)
    user_prompt_template: str = Field(min_length=1)
    output_schema_json: dict
    version: str = Field(min_length=1, max_length=40)
    status: LLMPromptTemplateStatus = LLMPromptTemplateStatus.DRAFT
    is_default: bool = False
    created_by: str | None = Field(default=None, max_length=120)


class LLMPromptTemplateUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    provider: str | None = Field(default=None, min_length=1, max_length=80)
    model: str | None = Field(default=None, min_length=1, max_length=120)
    system_prompt: str | None = Field(default=None, min_length=1)
    user_prompt_template: str | None = Field(default=None, min_length=1)
    output_schema_json: dict | None = None
    version: str | None = Field(default=None, min_length=1, max_length=40)
    status: LLMPromptTemplateStatus | None = None
    is_default: bool | None = None


class LLMPromptTemplateResponse(BaseModel):
    id: UUID
    name: str
    task_type: LLMPromptTaskType
    provider: str
    model: str
    system_prompt: str
    user_prompt_template: str
    output_schema_json: dict
    version: str
    status: LLMPromptTemplateStatus
    is_default: bool
    created_by: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LLMPromptTemplateListResponse(BaseModel):
    items: list[LLMPromptTemplateResponse]
    total: int
