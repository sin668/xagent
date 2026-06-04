"""Create raw collection tasks and candidate URLs.

Revision ID: 20260529_0010
Revises: 20260529_0009
Create Date: 2026-05-29
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260529_0010"
down_revision = "20260529_0009"
branch_labels = None
depends_on = None


source_usage_type = postgresql.ENUM(
    "automatic_collection",
    "public_discovery_only",
    "manual_sample",
    "policy_research",
    name="sourceusagetype",
    create_type=False,
)
collection_task_status = postgresql.ENUM(
    "pending",
    "running",
    "completed",
    "failed",
    "blocked",
    name="collectiontaskstatus",
    create_type=False,
)
candidate_url_status = postgresql.ENUM(
    "new",
    "staged",
    "duplicate",
    "blocked",
    "failed",
    name="candidateurlstatus",
    create_type=False,
)
channel_risk_level = postgresql.ENUM("Low", "Medium", "High", "Forbidden", name="channelrisklevel", create_type=False)
source_platform = postgresql.ENUM(
    "official_website",
    "public_directory",
    "search_engine",
    "google_maps",
    "yandex_maps",
    "youtube",
    "drom",
    "other",
    name="sourceplatform",
    create_type=False,
)


def upgrade() -> None:
    source_usage_type.create(op.get_bind(), checkfirst=True)
    collection_task_status.create(op.get_bind(), checkfirst=True)
    candidate_url_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "collection_tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("plan_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("task_type", sa.String(length=80), nullable=False),
        sa.Column("channel_name", sa.String(length=120), nullable=False),
        sa.Column("risk_level", channel_risk_level, nullable=False),
        sa.Column("source_usage_type", source_usage_type, nullable=False),
        sa.Column("allowed_actions", sa.Text(), nullable=False),
        sa.Column("forbidden_actions", sa.Text(), nullable=False),
        sa.Column("status", collection_task_status, nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_collection_tasks_plan_id", "collection_tasks", ["plan_id"])
    op.create_index("ix_collection_tasks_task_type", "collection_tasks", ["task_type"])
    op.create_index("ix_collection_tasks_channel_name", "collection_tasks", ["channel_name"])
    op.create_index("ix_collection_tasks_risk_level", "collection_tasks", ["risk_level"])
    op.create_index("ix_collection_tasks_source_usage_type", "collection_tasks", ["source_usage_type"])
    op.create_index("ix_collection_tasks_status", "collection_tasks", ["status"])

    op.create_table(
        "candidate_urls",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("collection_tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("url_hash", sa.String(length=64), nullable=False),
        sa.Column("source_platform", source_platform, nullable=False),
        sa.Column("source_risk_level", channel_risk_level, nullable=False),
        sa.Column("source_usage_type", source_usage_type, nullable=False),
        sa.Column("requires_secondary_verification", sa.Boolean(), nullable=False),
        sa.Column("discovery_reason", sa.Text(), nullable=False),
        sa.Column("status", candidate_url_status, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("url_hash", name="uq_candidate_urls_url_hash"),
    )
    op.create_index("ix_candidate_urls_task_id", "candidate_urls", ["task_id"])
    op.create_index("ix_candidate_urls_url_hash", "candidate_urls", ["url_hash"])
    op.create_index("ix_candidate_urls_source_platform", "candidate_urls", ["source_platform"])
    op.create_index("ix_candidate_urls_source_risk_level", "candidate_urls", ["source_risk_level"])
    op.create_index("ix_candidate_urls_source_usage_type", "candidate_urls", ["source_usage_type"])
    op.create_index("ix_candidate_urls_requires_secondary_verification", "candidate_urls", ["requires_secondary_verification"])
    op.create_index("ix_candidate_urls_status", "candidate_urls", ["status"])

    op.execute("COMMENT ON TABLE collection_tasks IS 'raw 层采集任务，记录渠道、风险等级、允许动作和禁止动作'")
    op.execute("COMMENT ON TABLE candidate_urls IS 'raw 层候选 URL，按 url_hash 幂等，必须关联 collection_tasks'")


def downgrade() -> None:
    op.drop_index("ix_candidate_urls_status", table_name="candidate_urls")
    op.drop_index("ix_candidate_urls_requires_secondary_verification", table_name="candidate_urls")
    op.drop_index("ix_candidate_urls_source_usage_type", table_name="candidate_urls")
    op.drop_index("ix_candidate_urls_source_risk_level", table_name="candidate_urls")
    op.drop_index("ix_candidate_urls_source_platform", table_name="candidate_urls")
    op.drop_index("ix_candidate_urls_url_hash", table_name="candidate_urls")
    op.drop_index("ix_candidate_urls_task_id", table_name="candidate_urls")
    op.drop_table("candidate_urls")

    op.drop_index("ix_collection_tasks_status", table_name="collection_tasks")
    op.drop_index("ix_collection_tasks_source_usage_type", table_name="collection_tasks")
    op.drop_index("ix_collection_tasks_risk_level", table_name="collection_tasks")
    op.drop_index("ix_collection_tasks_channel_name", table_name="collection_tasks")
    op.drop_index("ix_collection_tasks_task_type", table_name="collection_tasks")
    op.drop_index("ix_collection_tasks_plan_id", table_name="collection_tasks")
    op.drop_table("collection_tasks")

    candidate_url_status.drop(op.get_bind(), checkfirst=True)
    collection_task_status.drop(op.get_bind(), checkfirst=True)
    source_usage_type.drop(op.get_bind(), checkfirst=True)
