from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import LLMPromptTaskType, LLMPromptTemplateStatus, enum_values


class LLMPromptTemplate(Base):
    __tablename__ = "llm_prompt_templates"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    task_type: Mapped[LLMPromptTaskType] = mapped_column(
        Enum(LLMPromptTaskType, values_callable=enum_values),
        nullable=False,
        index=True,
    )
    provider: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    model: Mapped[str] = mapped_column(String(120), nullable=False)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    user_prompt_template: Mapped[str] = mapped_column(Text, nullable=False)
    output_schema_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    version: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[LLMPromptTemplateStatus] = mapped_column(
        Enum(LLMPromptTemplateStatus, values_callable=enum_values),
        nullable=False,
        default=LLMPromptTemplateStatus.DRAFT,
        index=True,
    )
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    created_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    source_file_path: Mapped[str | None] = mapped_column(String(500), nullable=True, index=True)
    source_file_hash: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    migration_batch_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    parent_template_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("llm_prompt_templates.id", ondelete="SET NULL"),
        nullable=True,
    )
    published_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    change_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    rollback_from_template_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("llm_prompt_templates.id", ondelete="SET NULL"),
        nullable=True,
    )
    validation_status: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    validation_errors_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
