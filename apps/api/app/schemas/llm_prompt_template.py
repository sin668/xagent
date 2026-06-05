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
    source_file_path: str | None = Field(default=None, max_length=500)
    source_file_hash: str | None = Field(default=None, max_length=128)
    migration_batch_id: str | None = Field(default=None, max_length=120)
    parent_template_id: UUID | None = None
    published_by: str | None = Field(default=None, max_length=120)
    published_at: datetime | None = None
    change_summary: str | None = None
    rollback_from_template_id: UUID | None = None
    validation_status: str | None = Field(default=None, max_length=40)
    validation_errors_json: dict | None = None


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
    source_file_path: str | None = Field(default=None, max_length=500)
    source_file_hash: str | None = Field(default=None, max_length=128)
    migration_batch_id: str | None = Field(default=None, max_length=120)
    parent_template_id: UUID | None = None
    published_by: str | None = Field(default=None, max_length=120)
    published_at: datetime | None = None
    change_summary: str | None = None
    rollback_from_template_id: UUID | None = None
    validation_status: str | None = Field(default=None, max_length=40)
    validation_errors_json: dict | None = None


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
    source_file_path: str | None
    source_file_hash: str | None
    migration_batch_id: str | None
    parent_template_id: UUID | None
    published_by: str | None
    published_at: datetime | None
    change_summary: str | None
    rollback_from_template_id: UUID | None
    validation_status: str | None
    validation_errors_json: dict | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LLMPromptTemplateListResponse(BaseModel):
    items: list[LLMPromptTemplateResponse]
    total: int
