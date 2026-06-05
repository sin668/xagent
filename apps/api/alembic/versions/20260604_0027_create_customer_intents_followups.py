"""Create customer intents and followups.

Revision ID: 20260604_0027
Revises: 20260604_0026
Create Date: 2026-06-04
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260604_0027"
down_revision = "20260604_0026"
branch_labels = None
depends_on = None


customer_vehicle_intent_source_type = postgresql.ENUM(
    "manual_customer_reply",
    "manual_business_note",
    "ai_enrichment_accepted",
    "imported",
    "unknown",
    name="customervehicleintentsourcetype",
    create_type=False,
)
customer_vehicle_intent_status = postgresql.ENUM(
    "active",
    "pending_confirmation",
    "fulfilled",
    "archived",
    name="customervehicleintentstatus",
    create_type=False,
)
customer_followup_team = postgresql.ENUM(
    "customer_service",
    "sales",
    "export",
    "compliance",
    "operations",
    name="customerfollowupteam",
    create_type=False,
)
customer_followup_type = postgresql.ENUM(
    "manual_call",
    "manual_message",
    "email",
    "customer_reply",
    "internal_note",
    "compliance_review",
    name="customerfollowuptype",
    create_type=False,
)


def upgrade() -> None:
    customer_vehicle_intent_source_type.create(op.get_bind(), checkfirst=True)
    customer_vehicle_intent_status.create(op.get_bind(), checkfirst=True)
    customer_followup_team.create(op.get_bind(), checkfirst=True)
    customer_followup_type.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "customer_vehicle_intents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("brand", sa.String(length=120), nullable=True),
        sa.Column("model", sa.String(length=120), nullable=True),
        sa.Column("year_range", sa.String(length=80), nullable=True),
        sa.Column("vehicle_age", sa.String(length=80), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=True),
        sa.Column("budget_range", sa.String(length=120), nullable=True),
        sa.Column("purchase_frequency", sa.String(length=120), nullable=True),
        sa.Column("delivery_country", sa.String(length=80), nullable=True),
        sa.Column("delivery_city", sa.String(length=120), nullable=True),
        sa.Column("concerns", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("source_type", customer_vehicle_intent_source_type, nullable=False),
        sa.Column("source_note", sa.Text(), nullable=True),
        sa.Column("status", customer_vehicle_intent_status, nullable=False),
        sa.Column("created_by", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_customer_vehicle_intents_customer_id", "customer_vehicle_intents", ["customer_id"])
    op.create_index("ix_customer_vehicle_intents_brand", "customer_vehicle_intents", ["brand"])
    op.create_index("ix_customer_vehicle_intents_model", "customer_vehicle_intents", ["model"])
    op.create_index("ix_customer_vehicle_intents_delivery_country", "customer_vehicle_intents", ["delivery_country"])
    op.create_index("ix_customer_vehicle_intents_delivery_city", "customer_vehicle_intents", ["delivery_city"])
    op.create_index("ix_customer_vehicle_intents_source_type", "customer_vehicle_intents", ["source_type"])
    op.create_index("ix_customer_vehicle_intents_status", "customer_vehicle_intents", ["status"])
    op.create_index("ix_customer_vehicle_intents_created_by", "customer_vehicle_intents", ["created_by"])

    op.create_table(
        "customer_followups",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_id", sa.String(length=120), nullable=False),
        sa.Column("team", customer_followup_team, nullable=False),
        sa.Column("followup_type", customer_followup_type, nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("customer_feedback", sa.Text(), nullable=True),
        sa.Column("next_action", sa.Text(), nullable=True),
        sa.Column("next_followup_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("triggered_dnc", sa.Boolean(), nullable=False),
        sa.Column("triggered_compliance_review", sa.Boolean(), nullable=False),
        sa.Column("created_by", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_customer_followups_customer_id", "customer_followups", ["customer_id"])
    op.create_index("ix_customer_followups_owner_id", "customer_followups", ["owner_id"])
    op.create_index("ix_customer_followups_team", "customer_followups", ["team"])
    op.create_index("ix_customer_followups_followup_type", "customer_followups", ["followup_type"])
    op.create_index("ix_customer_followups_next_followup_at", "customer_followups", ["next_followup_at"])
    op.create_index("ix_customer_followups_triggered_dnc", "customer_followups", ["triggered_dnc"])
    op.create_index(
        "ix_customer_followups_triggered_compliance_review",
        "customer_followups",
        ["triggered_compliance_review"],
    )
    op.create_index("ix_customer_followups_created_by", "customer_followups", ["created_by"])


def downgrade() -> None:
    op.drop_index("ix_customer_followups_created_by", table_name="customer_followups")
    op.drop_index("ix_customer_followups_triggered_compliance_review", table_name="customer_followups")
    op.drop_index("ix_customer_followups_triggered_dnc", table_name="customer_followups")
    op.drop_index("ix_customer_followups_next_followup_at", table_name="customer_followups")
    op.drop_index("ix_customer_followups_followup_type", table_name="customer_followups")
    op.drop_index("ix_customer_followups_team", table_name="customer_followups")
    op.drop_index("ix_customer_followups_owner_id", table_name="customer_followups")
    op.drop_index("ix_customer_followups_customer_id", table_name="customer_followups")
    op.drop_table("customer_followups")
    op.drop_index("ix_customer_vehicle_intents_created_by", table_name="customer_vehicle_intents")
    op.drop_index("ix_customer_vehicle_intents_status", table_name="customer_vehicle_intents")
    op.drop_index("ix_customer_vehicle_intents_source_type", table_name="customer_vehicle_intents")
    op.drop_index("ix_customer_vehicle_intents_delivery_city", table_name="customer_vehicle_intents")
    op.drop_index("ix_customer_vehicle_intents_delivery_country", table_name="customer_vehicle_intents")
    op.drop_index("ix_customer_vehicle_intents_model", table_name="customer_vehicle_intents")
    op.drop_index("ix_customer_vehicle_intents_brand", table_name="customer_vehicle_intents")
    op.drop_index("ix_customer_vehicle_intents_customer_id", table_name="customer_vehicle_intents")
    op.drop_table("customer_vehicle_intents")
    customer_followup_type.drop(op.get_bind(), checkfirst=True)
    customer_followup_team.drop(op.get_bind(), checkfirst=True)
    customer_vehicle_intent_status.drop(op.get_bind(), checkfirst=True)
    customer_vehicle_intent_source_type.drop(op.get_bind(), checkfirst=True)
