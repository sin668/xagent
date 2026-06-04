"""Add lead inventory matches.

Revision ID: 20260528_0005
Revises: 20260528_0004
Create Date: 2026-05-28
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260528_0005"
down_revision = "20260528_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "lead_inventory_matches",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("customers.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "inventory_item_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("inventory_items.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("recommendation_reason", sa.Text(), nullable=False),
        sa.Column("risk_tips", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("decision", sa.String(length=40), nullable=True),
        sa.Column("decision_owner", sa.String(length=120), nullable=True),
        sa.Column("decision_note", sa.Text(), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_lead_inventory_matches_customer_id", "lead_inventory_matches", ["customer_id"])
    op.create_index("ix_lead_inventory_matches_inventory_item_id", "lead_inventory_matches", ["inventory_item_id"])


def downgrade() -> None:
    op.drop_index("ix_lead_inventory_matches_inventory_item_id", table_name="lead_inventory_matches")
    op.drop_index("ix_lead_inventory_matches_customer_id", table_name="lead_inventory_matches")
    op.drop_table("lead_inventory_matches")
