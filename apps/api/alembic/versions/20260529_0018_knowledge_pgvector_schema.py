"""Create knowledge pgvector schema.

Revision ID: 20260529_0018
Revises: 20260529_0017
Create Date: 2026-05-29
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260529_0018"
down_revision = "20260529_0017"
branch_labels = None
depends_on = None


class Vector(sa.types.UserDefinedType):
    def get_col_spec(self, **kw) -> str:
        return "vector(1536)"


knowledge_item_status = postgresql.ENUM("draft", "active", "deprecated", "disabled", name="knowledgeitemstatus", create_type=False)
knowledge_review_status = postgresql.ENUM("pending", "approved", "rejected", name="knowledgereviewstatus", create_type=False)
knowledge_embedding_status = postgresql.ENUM("pending", "ready", "failed", name="knowledgeembeddingstatus", create_type=False)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    knowledge_item_status.create(op.get_bind(), checkfirst=True)
    knowledge_review_status.create(op.get_bind(), checkfirst=True)
    knowledge_embedding_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "knowledge_collections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=160), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", knowledge_item_status, nullable=False, server_default="draft"),
        sa.Column("review_status", knowledge_review_status, nullable=False, server_default="pending"),
        sa.Column("version", sa.String(length=80), nullable=False, server_default="v1"),
        sa.Column("source_ref", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_knowledge_collections_name", "knowledge_collections", ["name"])
    op.create_index("ix_knowledge_collections_status", "knowledge_collections", ["status"])
    op.create_index("ix_knowledge_collections_review_status", "knowledge_collections", ["review_status"])

    op.create_table(
        "knowledge_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("collection_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("knowledge_collections.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("language", sa.String(length=20), nullable=False, server_default="zh"),
        sa.Column("country", sa.String(length=80), nullable=True),
        sa.Column("applicable_channels", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("status", knowledge_item_status, nullable=False, server_default="draft"),
        sa.Column("review_status", knowledge_review_status, nullable=False, server_default="pending"),
        sa.Column("source_ref", sa.Text(), nullable=True),
        sa.Column("version", sa.String(length=80), nullable=False, server_default="v1"),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_knowledge_items_collection_id", "knowledge_items", ["collection_id"])
    op.create_index("ix_knowledge_items_title", "knowledge_items", ["title"])
    op.create_index("ix_knowledge_items_language", "knowledge_items", ["language"])
    op.create_index("ix_knowledge_items_country", "knowledge_items", ["country"])
    op.create_index("ix_knowledge_items_status", "knowledge_items", ["status"])
    op.create_index("ix_knowledge_items_review_status", "knowledge_items", ["review_status"])
    op.create_index("ix_knowledge_items_version", "knowledge_items", ["version"])

    op.create_table(
        "knowledge_embeddings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("knowledge_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("embedding_model", sa.String(length=120), nullable=False),
        sa.Column("embedding", Vector(), nullable=True),
        sa.Column("embedding_dimensions", sa.Integer(), nullable=False, server_default="1536"),
        sa.Column("embedding_status", knowledge_embedding_status, nullable=False, server_default="pending"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_knowledge_embeddings_item_id", "knowledge_embeddings", ["item_id"])
    op.create_index("ix_knowledge_embeddings_embedding_model", "knowledge_embeddings", ["embedding_model"])
    op.create_index("ix_knowledge_embeddings_embedding_status", "knowledge_embeddings", ["embedding_status"])


def downgrade() -> None:
    op.drop_index("ix_knowledge_embeddings_embedding_status", table_name="knowledge_embeddings")
    op.drop_index("ix_knowledge_embeddings_embedding_model", table_name="knowledge_embeddings")
    op.drop_index("ix_knowledge_embeddings_item_id", table_name="knowledge_embeddings")
    op.drop_table("knowledge_embeddings")

    op.drop_index("ix_knowledge_items_version", table_name="knowledge_items")
    op.drop_index("ix_knowledge_items_review_status", table_name="knowledge_items")
    op.drop_index("ix_knowledge_items_status", table_name="knowledge_items")
    op.drop_index("ix_knowledge_items_country", table_name="knowledge_items")
    op.drop_index("ix_knowledge_items_language", table_name="knowledge_items")
    op.drop_index("ix_knowledge_items_title", table_name="knowledge_items")
    op.drop_index("ix_knowledge_items_collection_id", table_name="knowledge_items")
    op.drop_table("knowledge_items")

    op.drop_index("ix_knowledge_collections_review_status", table_name="knowledge_collections")
    op.drop_index("ix_knowledge_collections_status", table_name="knowledge_collections")
    op.drop_index("ix_knowledge_collections_name", table_name="knowledge_collections")
    op.drop_table("knowledge_collections")

    knowledge_embedding_status.drop(op.get_bind(), checkfirst=True)
    knowledge_review_status.drop(op.get_bind(), checkfirst=True)
    knowledge_item_status.drop(op.get_bind(), checkfirst=True)

