from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import PageSnapshotReadStatus, enum_values


class PageSnapshot(Base):
    __tablename__ = "page_snapshots"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    candidate_url_id: Mapped[UUID] = mapped_column(ForeignKey("candidate_urls.id", ondelete="CASCADE"), nullable=False, index=True)
    page_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    text_excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_note: Mapped[str] = mapped_column(Text, nullable=False, default="")
    read_status: Mapped[PageSnapshotReadStatus] = mapped_column(
        Enum(PageSnapshotReadStatus, values_callable=enum_values),
        nullable=False,
        index=True,
    )
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, index=True)
    robots_or_policy_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    candidate_url = relationship("CandidateUrl", back_populates="page_snapshots")
