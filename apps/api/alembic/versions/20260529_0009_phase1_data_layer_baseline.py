"""Create phase 1 data layer baseline.

Revision ID: 20260529_0009
Revises: 20260528_0008
Create Date: 2026-05-29
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.exc import SQLAlchemyError

revision = "20260529_0009"
down_revision = "20260528_0008"
branch_labels = None
depends_on = None


DATA_LAYERS = [
    {
        "layer_name": "raw",
        "layer_order": 10,
        "purpose": "保存采集任务、候选 URL、公开页面摘要和来源证据，不直接交付客服或销售。",
        "allowed_tables": "collection_tasks,candidate_urls,page_snapshots",
        "entry_gate": "允许 Low/Medium 受控自动发现；High 仅 public_discovery_only；Forbidden 不入库。",
    },
    {
        "layer_name": "staging",
        "layer_order": 20,
        "purpose": "保存 AI 抽取后的候选线索、联系方式和来源快照，等待人工复核。",
        "allowed_tables": "staging_leads,staging_contacts,staging_sources",
        "entry_gate": "必须有关联 source_url 和 evidence_note；缺失字段保留 Unknown/null/[]。",
    },
    {
        "layer_name": "core",
        "layer_order": 30,
        "purpose": "保存已通过人工复核的正式客户、联系方式、来源、触达和合规复核记录。",
        "allowed_tables": "customers,contact_methods,lead_sources,outreach_records,compliance_reviews",
        "entry_gate": "无来源、无证据、Invalid/Watch、勿扰、High 未二次复核不得进入待触达。",
    },
    {
        "layer_name": "audit",
        "layer_order": 40,
        "purpose": "保存 AI、Agent、人工操作、规则阻断和风险事件日志。",
        "allowed_tables": "ai_audit_logs,agent_run_logs,review_logs,risk_events",
        "entry_gate": "所有 AI 输出必须写入输入引用、输出 JSON、模型、prompt 版本、来源和校验结果。",
    },
    {
        "layer_name": "knowledge",
        "layer_order": 50,
        "purpose": "保存渠道 SOP、FAQ、触达模板、关键词、车辆知识、合规规则和失败案例。",
        "allowed_tables": "knowledge_collections,knowledge_items,knowledge_embeddings,rule_configs",
        "entry_gate": "只有 approved 知识可进入生产 RAG；deprecated 知识不得被检索给 Agent。",
    },
]

TABLE_LAYER_MAP = [
    ("collection_tasks", "raw", "planned", "P1-E1-S2", "采集任务由后续 Story 创建。"),
    ("candidate_urls", "raw", "planned", "P1-E1-S2", "候选 URL 由后续 Story 创建。"),
    ("page_snapshots", "raw", "planned", "P1-E1-S3", "公开页面快照由后续 Story 创建。"),
    ("staging_leads", "staging", "planned", "P1-E1-S4", "AI 抽取候选线索由后续 Story 创建。"),
    ("staging_contacts", "staging", "planned", "P1-E1-S4", "staging 联系方式可随 staging_leads 或独立表实现。"),
    ("staging_sources", "staging", "planned", "P1-E1-S4", "staging 来源证据可随 staging_leads 或独立表实现。"),
    ("customers", "core", "existing", "MVP baseline", "正式客户主体，已有表，不在本迁移中修改。"),
    ("contact_methods", "core", "existing", "MVP baseline", "正式联系方式，已有表，不在本迁移中修改。"),
    ("lead_sources", "core", "existing", "MVP baseline", "正式来源证据，已有表，不在本迁移中修改。"),
    ("outreach_records", "core", "existing", "MVP baseline", "人工触达记录，已有表，不在本迁移中修改。"),
    ("compliance_reviews", "core", "existing", "MVP baseline", "C 级合规复核记录，已有表，不在本迁移中修改。"),
    ("ai_audit_logs", "audit", "existing", "MVP baseline", "AI 审计日志，已有表，后续 Story 扩展字段。"),
    ("agent_run_logs", "audit", "planned", "P1-E1-S5", "Agent 运行日志由后续 Story 创建。"),
    ("review_logs", "audit", "planned", "P1-E1-S5", "人工复核日志由后续 Story 创建。"),
    ("risk_events", "audit", "planned", "P1-E1-S5", "风险事件由后续 Story 创建。"),
    ("knowledge_collections", "knowledge", "planned", "P1-E5-S1", "知识集合由知识库 Story 创建。"),
    ("knowledge_items", "knowledge", "planned", "P1-E5-S1", "知识条目由知识库 Story 创建。"),
    ("knowledge_embeddings", "knowledge", "planned", "P1-E5-S1", "向量表由知识库 Story 创建。"),
    ("rule_configs", "knowledge", "planned", "P1-E5-S1", "结构化规则配置由知识库 Story 创建。"),
]


def ensure_pgvector_extension() -> None:
    try:
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    except SQLAlchemyError as exc:
        raise RuntimeError(
            "pgvector extension is required for phase 1 knowledge embeddings. "
            "Install pgvector on the PostgreSQL server, then run "
            "'CREATE EXTENSION IF NOT EXISTS vector;' in the target database before retrying."
        ) from exc


def upgrade() -> None:
    ensure_pgvector_extension()

    op.create_table(
        "phase1_data_layers",
        sa.Column("layer_name", sa.String(length=40), primary_key=True),
        sa.Column("layer_order", sa.Integer(), nullable=False, unique=True),
        sa.Column("purpose", sa.Text(), nullable=False),
        sa.Column("allowed_tables", sa.Text(), nullable=False),
        sa.Column("entry_gate", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_phase1_data_layers_layer_order", "phase1_data_layers", ["layer_order"])

    op.create_table(
        "phase1_data_layer_table_map",
        sa.Column("table_name", sa.String(length=120), primary_key=True),
        sa.Column(
            "layer_name",
            sa.String(length=40),
            sa.ForeignKey("phase1_data_layers.layer_name", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("table_role", sa.String(length=40), nullable=False),
        sa.Column("planned_story", sa.String(length=80), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_phase1_data_layer_table_map_layer", "phase1_data_layer_table_map", ["layer_name"])
    op.create_index("ix_phase1_data_layer_table_map_role", "phase1_data_layer_table_map", ["table_role"])

    data_layers_table = sa.table(
        "phase1_data_layers",
        sa.column("layer_name", sa.String),
        sa.column("layer_order", sa.Integer),
        sa.column("purpose", sa.Text),
        sa.column("allowed_tables", sa.Text),
        sa.column("entry_gate", sa.Text),
    )
    table_map_table = sa.table(
        "phase1_data_layer_table_map",
        sa.column("table_name", sa.String),
        sa.column("layer_name", sa.String),
        sa.column("table_role", sa.String),
        sa.column("planned_story", sa.String),
        sa.column("notes", sa.Text),
    )

    op.bulk_insert(data_layers_table, DATA_LAYERS)
    op.bulk_insert(
        table_map_table,
        [
            {
                "table_name": table_name,
                "layer_name": layer_name,
                "table_role": table_role,
                "planned_story": planned_story,
                "notes": notes,
            }
            for table_name, layer_name, table_role, planned_story, notes in TABLE_LAYER_MAP
        ],
    )

    op.execute("COMMENT ON TABLE phase1_data_layers IS '第一阶段 raw/staging/core/audit/knowledge 数据层基线登记表'")
    op.execute("COMMENT ON TABLE phase1_data_layer_table_map IS '第一阶段业务表到数据层的映射和后续 Story 落点'")


def downgrade() -> None:
    op.drop_index("ix_phase1_data_layer_table_map_role", table_name="phase1_data_layer_table_map")
    op.drop_index("ix_phase1_data_layer_table_map_layer", table_name="phase1_data_layer_table_map")
    op.drop_table("phase1_data_layer_table_map")
    op.drop_index("ix_phase1_data_layers_layer_order", table_name="phase1_data_layers")
    op.drop_table("phase1_data_layers")
