"""Initial MVP data foundation.

Revision ID: 20260528_0001
Revises:
Create Date: 2026-05-28
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260528_0001"
down_revision = None
branch_labels = None
depends_on = None


customer_type = sa.Enum(
    "local_dealer_secondary_dealer",
    "personal_buyer",
    "kol_auto_blogger",
    "unknown",
    "non_target",
    name="customertype",
)
customer_grade = sa.Enum("A", "B", "C", "Invalid", "Watch", name="customergrade")
customer_status = sa.Enum(
    "new",
    "needs_enrichment",
    "pending_review",
    "ready_for_customer_service",
    "customer_service_following",
    "ready_for_sales",
    "sales_following",
    "invalid",
    "watch",
    "do_not_contact",
    name="customerstatus",
)
contact_method_type = sa.Enum(
    "email",
    "phone",
    "whatsapp",
    "telegram",
    "vkontakte",
    "odnoklassniki",
    "tiktok",
    "max",
    "website",
    "website_form",
    "other",
    name="contactmethodtype",
)
source_platform = sa.Enum(
    "official_website",
    "public_directory",
    "search_engine",
    "google_maps",
    "yandex_maps",
    "youtube",
    "drom",
    "other",
    name="sourceplatform",
)
channel_risk_level = sa.Enum("Low", "Medium", "High", "Forbidden", name="channelrisklevel")
outreach_status = sa.Enum("draft", "ready_for_manual_send", "sent", "replied", "rejected", "closed", name="outreachstatus")
ai_task_type = sa.Enum("lead_extraction", "lead_grading", "outreach_draft", "inventory_matching", "risk_block", name="aitasktype")
compliance_review_status = sa.Enum("pending", "approved", "rejected", "not_required", name="compliancereviewstatus")
sync_status = sa.Enum("success", "partial", "failed", name="syncstatus")
script_review_status = sa.Enum(
    "draft",
    "business_review",
    "compliance_review",
    "approved_for_external_use",
    "disabled",
    name="scriptreviewstatus",
)


def upgrade() -> None:
    op.create_table(
        "customers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("external_id", sa.String(length=120), nullable=True, unique=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("normalized_name", sa.String(length=255), nullable=True),
        sa.Column("country", sa.String(length=80), nullable=False),
        sa.Column("city", sa.String(length=120), nullable=True),
        sa.Column("customer_type", customer_type, nullable=False),
        sa.Column("grade", customer_grade, nullable=False),
        sa.Column("status", customer_status, nullable=False),
        sa.Column("owner", sa.String(length=120), nullable=True),
        sa.Column("do_not_contact", sa.Boolean(), nullable=False),
        sa.Column("do_not_contact_reason", sa.Text(), nullable=True),
        sa.Column("do_not_contact_marked_by", sa.String(length=120), nullable=True),
        sa.Column("do_not_contact_marked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ai_recommended_grade", customer_grade, nullable=True),
        sa.Column("ai_recommendation_reason", sa.Text(), nullable=True),
        sa.Column("missing_fields", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_customers_external_id", "customers", ["external_id"])
    op.create_index("ix_customers_name", "customers", ["name"])
    op.create_index("ix_customers_normalized_name", "customers", ["normalized_name"])
    op.create_index("ix_customers_country", "customers", ["country"])
    op.create_index("ix_customers_city", "customers", ["city"])
    op.create_index("ix_customers_grade", "customers", ["grade"])
    op.create_index("ix_customers_status", "customers", ["status"])
    op.create_index("ix_customers_owner", "customers", ["owner"])
    op.create_index("ix_customers_do_not_contact", "customers", ["do_not_contact"])

    op.create_table(
        "lead_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("external_id", sa.String(length=120), nullable=True, unique=True),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("customers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("platform", source_platform, nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("source_title", sa.String(length=255), nullable=True),
        sa.Column("evidence_note", sa.Text(), nullable=False),
        sa.Column("evidence_excerpt", sa.Text(), nullable=True),
        sa.Column("channel_risk_level", channel_risk_level, nullable=False),
        sa.Column("collected_keyword", sa.String(length=255), nullable=True),
        sa.Column("collected_by", sa.String(length=120), nullable=True),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_lead_sources_external_id", "lead_sources", ["external_id"])
    op.create_index("ix_lead_sources_customer_id", "lead_sources", ["customer_id"])
    op.create_index("ix_lead_sources_platform", "lead_sources", ["platform"])
    op.create_index("ix_lead_sources_channel_risk_level", "lead_sources", ["channel_risk_level"])

    op.create_table(
        "contact_methods",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("customers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("method_type", contact_method_type, nullable=False),
        sa.Column("value", sa.String(length=255), nullable=False),
        sa.Column("label", sa.String(length=120), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("evidence_note", sa.Text(), nullable=True),
        sa.Column("is_primary", sa.Boolean(), nullable=False),
        sa.Column("is_verified", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_contact_methods_customer_id", "contact_methods", ["customer_id"])
    op.create_index("ix_contact_methods_method_type", "contact_methods", ["method_type"])
    op.create_index("ix_contact_methods_value", "contact_methods", ["value"])

    op.create_table(
        "outreach_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("external_id", sa.String(length=120), nullable=True, unique=True),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("customers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("channel", contact_method_type, nullable=False),
        sa.Column("status", outreach_status, nullable=False),
        sa.Column("script_version", sa.String(length=80), nullable=True),
        sa.Column("sent_by", sa.String(length=120), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("response_summary", sa.Text(), nullable=True),
        sa.Column("next_action", sa.String(length=120), nullable=True),
        sa.Column("triggers_do_not_contact", sa.Boolean(), nullable=False),
        sa.Column("do_not_contact_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_outreach_records_external_id", "outreach_records", ["external_id"])
    op.create_index("ix_outreach_records_customer_id", "outreach_records", ["customer_id"])

    op.create_table(
        "inventory_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("external_id", sa.String(length=120), nullable=True, unique=True),
        sa.Column("brand", sa.String(length=120), nullable=False),
        sa.Column("model", sa.String(length=120), nullable=False),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("mileage_km", sa.Integer(), nullable=True),
        sa.Column("vehicle_type", sa.String(length=80), nullable=True),
        sa.Column("condition_summary", sa.Text(), nullable=True),
        sa.Column("quoted_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("currency", sa.String(length=8), nullable=False),
        sa.Column("quote_status", sa.String(length=80), nullable=False),
        sa.Column("export_ready", sa.Boolean(), nullable=False),
        sa.Column("source_ref", sa.String(length=120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_inventory_items_external_id", "inventory_items", ["external_id"])
    op.create_index("ix_inventory_items_brand", "inventory_items", ["brand"])
    op.create_index("ix_inventory_items_model", "inventory_items", ["model"])

    op.create_table(
        "channel_risk_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("external_id", sa.String(length=120), nullable=True, unique=True),
        sa.Column("channel_name", sa.String(length=120), nullable=False, unique=True),
        sa.Column("channel_type", sa.String(length=120), nullable=False),
        sa.Column("risk_level", channel_risk_level, nullable=False),
        sa.Column("collection_allowed", sa.Boolean(), nullable=False),
        sa.Column("ai_processing_allowed", sa.Boolean(), nullable=False),
        sa.Column("allowed_actions", sa.Text(), nullable=False),
        sa.Column("forbidden_actions", sa.Text(), nullable=False),
        sa.Column("policy_source_url", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("last_reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_channel_risk_rules_external_id", "channel_risk_rules", ["external_id"])
    op.create_index("ix_channel_risk_rules_channel_name", "channel_risk_rules", ["channel_name"])
    op.create_index("ix_channel_risk_rules_risk_level", "channel_risk_rules", ["risk_level"])

    op.create_table(
        "ai_audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("customers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("task_type", ai_task_type, nullable=False),
        sa.Column("model_name", sa.String(length=120), nullable=False),
        sa.Column("prompt_version", sa.String(length=120), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("input_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("output_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("risk_blocked", sa.Boolean(), nullable=False),
        sa.Column("risk_block_reason", sa.Text(), nullable=True),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_ai_audit_logs_customer_id", "ai_audit_logs", ["customer_id"])
    op.create_index("ix_ai_audit_logs_task_type", "ai_audit_logs", ["task_type"])

    op.create_table(
        "compliance_reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("customers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("review_type", sa.String(length=120), nullable=False),
        sa.Column("status", compliance_review_status, nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("reviewer", sa.String(length=120), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_compliance_reviews_customer_id", "compliance_reviews", ["customer_id"])
    op.create_index("ix_compliance_reviews_status", "compliance_reviews", ["status"])

    op.create_table(
        "sync_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source_name", sa.String(length=120), nullable=False),
        sa.Column("object_name", sa.String(length=120), nullable=False),
        sa.Column("status", sync_status, nullable=False),
        sa.Column("success_count", sa.Integer(), nullable=False),
        sa.Column("failure_count", sa.Integer(), nullable=False),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "script_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("external_id", sa.String(length=120), nullable=True, unique=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("script_type", sa.String(length=120), nullable=False),
        sa.Column("applicable_grades", sa.Text(), nullable=False),
        sa.Column("applicable_channels", sa.Text(), nullable=False),
        sa.Column("chinese_internal_text", sa.Text(), nullable=False),
        sa.Column("russian_customer_text", sa.Text(), nullable=False),
        sa.Column("forbidden_promises", sa.Text(), nullable=False),
        sa.Column("review_status", script_review_status, nullable=False),
        sa.Column("reviewer", sa.String(length=120), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.String(length=80), nullable=False),
        sa.Column("opt_out_path", sa.Text(), nullable=False),
        sa.Column("risk_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_script_templates_external_id", "script_templates", ["external_id"])
    op.create_index("ix_script_templates_name", "script_templates", ["name"])
    op.create_index("ix_script_templates_review_status", "script_templates", ["review_status"])


def downgrade() -> None:
    op.drop_index("ix_script_templates_review_status", table_name="script_templates")
    op.drop_index("ix_script_templates_name", table_name="script_templates")
    op.drop_index("ix_script_templates_external_id", table_name="script_templates")
    op.drop_table("script_templates")
    op.drop_table("sync_logs")
    op.drop_index("ix_compliance_reviews_status", table_name="compliance_reviews")
    op.drop_index("ix_compliance_reviews_customer_id", table_name="compliance_reviews")
    op.drop_table("compliance_reviews")
    op.drop_index("ix_ai_audit_logs_task_type", table_name="ai_audit_logs")
    op.drop_index("ix_ai_audit_logs_customer_id", table_name="ai_audit_logs")
    op.drop_table("ai_audit_logs")
    op.drop_index("ix_channel_risk_rules_risk_level", table_name="channel_risk_rules")
    op.drop_index("ix_channel_risk_rules_channel_name", table_name="channel_risk_rules")
    op.drop_index("ix_channel_risk_rules_external_id", table_name="channel_risk_rules")
    op.drop_table("channel_risk_rules")
    op.drop_index("ix_inventory_items_model", table_name="inventory_items")
    op.drop_index("ix_inventory_items_brand", table_name="inventory_items")
    op.drop_index("ix_inventory_items_external_id", table_name="inventory_items")
    op.drop_table("inventory_items")
    op.drop_index("ix_outreach_records_customer_id", table_name="outreach_records")
    op.drop_index("ix_outreach_records_external_id", table_name="outreach_records")
    op.drop_table("outreach_records")
    op.drop_index("ix_contact_methods_value", table_name="contact_methods")
    op.drop_index("ix_contact_methods_method_type", table_name="contact_methods")
    op.drop_index("ix_contact_methods_customer_id", table_name="contact_methods")
    op.drop_table("contact_methods")
    op.drop_index("ix_lead_sources_channel_risk_level", table_name="lead_sources")
    op.drop_index("ix_lead_sources_platform", table_name="lead_sources")
    op.drop_index("ix_lead_sources_customer_id", table_name="lead_sources")
    op.drop_index("ix_lead_sources_external_id", table_name="lead_sources")
    op.drop_table("lead_sources")
    op.drop_index("ix_customers_do_not_contact", table_name="customers")
    op.drop_index("ix_customers_owner", table_name="customers")
    op.drop_index("ix_customers_status", table_name="customers")
    op.drop_index("ix_customers_grade", table_name="customers")
    op.drop_index("ix_customers_city", table_name="customers")
    op.drop_index("ix_customers_country", table_name="customers")
    op.drop_index("ix_customers_normalized_name", table_name="customers")
    op.drop_index("ix_customers_name", table_name="customers")
    op.drop_index("ix_customers_external_id", table_name="customers")
    op.drop_table("customers")
    for enum in [
        sync_status,
        script_review_status,
        compliance_review_status,
        ai_task_type,
        outreach_status,
        channel_risk_level,
        source_platform,
        contact_method_type,
        customer_status,
        customer_grade,
        customer_type,
    ]:
        enum.drop(op.get_bind(), checkfirst=True)
