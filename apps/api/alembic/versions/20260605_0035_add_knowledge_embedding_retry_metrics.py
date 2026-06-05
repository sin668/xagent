"""Add knowledge embedding retry metrics.

Revision ID: 20260605_0035
Revises: 20260605_0034
Create Date: 2026-06-05
"""

from alembic import op
import sqlalchemy as sa


revision = "20260605_0035"
down_revision = "20260605_0034"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("knowledge_embeddings", sa.Column("last_error_message", sa.Text(), nullable=True))
    op.add_column(
        "knowledge_embeddings",
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_knowledge_embeddings_retry_count", "knowledge_embeddings", ["retry_count"])


def downgrade() -> None:
    op.drop_index("ix_knowledge_embeddings_retry_count", table_name="knowledge_embeddings")
    op.drop_column("knowledge_embeddings", "retry_count")
    op.drop_column("knowledge_embeddings", "last_error_message")
