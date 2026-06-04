from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import JsonType
from app.models.enums import AITaskType, enum_values


class AIAuditLog(Base):
    __tablename__ = "ai_audit_logs"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    customer_id: Mapped[UUID | None] = mapped_column(ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True)
    task_type: Mapped[AITaskType] = mapped_column(Enum(AITaskType, values_callable=enum_values), nullable=False, index=True)
    model_name: Mapped[str] = mapped_column(String(120), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(120), nullable=False)
    channel_name: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_urls: Mapped[list] = mapped_column(JsonType, nullable=False, default=list)
    input_payload: Mapped[dict | None] = mapped_column(JsonType, nullable=True)
    output_payload: Mapped[dict | None] = mapped_column(JsonType, nullable=True)
    output_json: Mapped[dict | None] = mapped_column(JsonType, nullable=True)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost_amount: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    cost_currency: Mapped[str | None] = mapped_column(String(12), nullable=True)
    risk_blocked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    risk_block_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    customer = relationship("Customer", back_populates="ai_audit_logs")
