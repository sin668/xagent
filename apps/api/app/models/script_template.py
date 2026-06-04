from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import ScriptReviewStatus, enum_values


class ScriptTemplate(Base):
    __tablename__ = "script_templates"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    external_id: Mapped[str | None] = mapped_column(String(120), nullable=True, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    script_type: Mapped[str] = mapped_column(String(120), nullable=False)
    applicable_grades: Mapped[str] = mapped_column(Text, nullable=False)
    applicable_channels: Mapped[str] = mapped_column(Text, nullable=False)
    chinese_internal_text: Mapped[str] = mapped_column(Text, nullable=False)
    russian_customer_text: Mapped[str] = mapped_column(Text, nullable=False)
    forbidden_promises: Mapped[str] = mapped_column(Text, nullable=False)
    review_status: Mapped[ScriptReviewStatus] = mapped_column(
        Enum(ScriptReviewStatus, values_callable=enum_values),
        nullable=False,
        default=ScriptReviewStatus.DRAFT,
        index=True,
    )
    reviewer: Mapped[str | None] = mapped_column(String(120), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    version: Mapped[str] = mapped_column(String(80), nullable=False)
    opt_out_path: Mapped[str] = mapped_column(Text, nullable=False)
    risk_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

