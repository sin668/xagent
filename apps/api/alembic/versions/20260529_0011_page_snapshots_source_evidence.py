"""Create page snapshots and source evidence records.

Revision ID: 20260529_0011
Revises: 20260529_0010
Create Date: 2026-05-29
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260529_0011"
down_revision = "20260529_0010"
branch_labels = None
depends_on = None


page_snapshot_read_status = postgresql.ENUM(
    "success",
    "blocked",
    "failed",
    "needs_manual_review",
    name="pagesnapshotreadstatus",
    create_type=False,
)


def upgrade() -> None:
    page_snapshot_read_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "page_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("candidate_url_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("candidate_urls.id", ondelete="CASCADE"), nullable=False),
        sa.Column("page_title", sa.String(length=255), nullable=True),
        sa.Column("text_excerpt", sa.Text(), nullable=True),
        sa.Column("evidence_note", sa.Text(), nullable=False, server_default=""),
        sa.Column("read_status", page_snapshot_read_status, nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("robots_or_policy_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_page_snapshots_candidate_url_id", "page_snapshots", ["candidate_url_id"])
    op.create_index("ix_page_snapshots_read_status", "page_snapshots", ["read_status"])
    op.create_index("ix_page_snapshots_captured_at", "page_snapshots", ["captured_at"])
    op.execute(
        "COMMENT ON TABLE page_snapshots IS 'raw 层公开页面读取快照，仅保存摘要、证据摘录和读取状态，不保存完整网页镜像'"
    )


def downgrade() -> None:
    op.drop_index("ix_page_snapshots_captured_at", table_name="page_snapshots")
    op.drop_index("ix_page_snapshots_read_status", table_name="page_snapshots")
    op.drop_index("ix_page_snapshots_candidate_url_id", table_name="page_snapshots")
    op.drop_table("page_snapshots")
    page_snapshot_read_status.drop(op.get_bind(), checkfirst=True)
