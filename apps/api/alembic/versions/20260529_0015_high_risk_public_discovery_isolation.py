"""Add high risk public discovery isolation fields.

Revision ID: 20260529_0015
Revises: 20260529_0014
Create Date: 2026-05-29
"""
from alembic import op
import sqlalchemy as sa

revision = "20260529_0015"
down_revision = "20260529_0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("collection_tasks", sa.Column("max_sample_size", sa.Integer(), nullable=True))
    op.add_column("candidate_urls", sa.Column("queue_eligible", sa.Boolean(), nullable=False, server_default=sa.text("true")))
    op.create_index("ix_candidate_urls_queue_eligible", "candidate_urls", ["queue_eligible"])


def downgrade() -> None:
    op.drop_index("ix_candidate_urls_queue_eligible", table_name="candidate_urls")
    op.drop_column("candidate_urls", "queue_eligible")
    op.drop_column("collection_tasks", "max_sample_size")
