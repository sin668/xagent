from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import JsonType
from app.models.enums import AgentTaskRunStatus, AgentTaskType, enum_values


class AgentTaskRun(Base):
    __tablename__ = "agent_task_runs"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    task_type: Mapped[AgentTaskType] = mapped_column(
        Enum(AgentTaskType, values_callable=enum_values),
        nullable=False,
        index=True,
    )
    status: Mapped[AgentTaskRunStatus] = mapped_column(
        Enum(AgentTaskRunStatus, values_callable=enum_values),
        nullable=False,
        default=AgentTaskRunStatus.PENDING,
        index=True,
    )
    trigger_source: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    input_json: Mapped[dict] = mapped_column(JsonType, nullable=False, default=dict)
    output_summary_json: Mapped[dict | None] = mapped_column(JsonType, nullable=True)
    llm_provider: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    llm_model: Mapped[str | None] = mapped_column(String(120), nullable=True)
    prompt_template_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("llm_prompt_templates.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    prompt_version: Mapped[str | None] = mapped_column(String(40), nullable=True)
    token_usage_json: Mapped[dict | None] = mapped_column(JsonType, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
