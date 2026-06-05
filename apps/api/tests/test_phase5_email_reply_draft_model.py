from pathlib import Path

from sqlalchemy import inspect

from app.models.customer import Customer
from app.models.email_message import EmailMessage
from app.models.email_thread import EmailThread
from app.models.enums import EmailReplyDraftStatus


API_ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = API_ROOT / "alembic" / "versions" / "20260605_0031_create_email_reply_drafts.py"


def test_phase5_email_reply_draft_status_enum_defines_review_lifecycle() -> None:
    assert EmailReplyDraftStatus.DRAFTED == "drafted"
    assert EmailReplyDraftStatus.PENDING_REVIEW == "pending_review"
    assert EmailReplyDraftStatus.APPROVED == "approved"
    assert EmailReplyDraftStatus.SENT == "sent"
    assert EmailReplyDraftStatus.REJECTED == "rejected"
    assert EmailReplyDraftStatus.BLOCKED == "blocked"
    assert EmailReplyDraftStatus.FAILED == "failed"


def test_phase5_email_reply_draft_model_separates_ai_suggestion_from_final_content() -> None:
    from app.models import EmailReplyDraft

    columns = inspect(EmailReplyDraft).columns

    for column_name in (
        "id",
        "thread_id",
        "message_id",
        "customer_id",
        "agent_service_run_id",
        "agent_task_run_id",
        "prompt_template_id",
        "prompt_version",
        "model",
        "detected_language",
        "reply_language",
        "language_confidence",
        "ai_suggested_subject",
        "ai_suggested_body",
        "final_subject",
        "final_body",
        "knowledge_hits_json",
        "auto_send_allowed",
        "auto_send_decision_json",
        "manual_review_required",
        "manual_review_reason",
        "status",
        "reviewed_by",
        "reviewed_at",
        "sent_record_id",
        "created_at",
        "updated_at",
    ):
        assert column_name in columns

    assert columns["ai_suggested_subject"].nullable is True
    assert columns["ai_suggested_body"].nullable is False
    assert columns["final_subject"].nullable is True
    assert columns["final_body"].nullable is True
    assert columns["knowledge_hits_json"].nullable is False
    assert columns["auto_send_decision_json"].nullable is False
    assert columns["manual_review_required"].nullable is False

    assert hasattr(Customer, "email_reply_drafts")
    assert hasattr(EmailThread, "reply_drafts")
    assert hasattr(EmailMessage, "reply_drafts")


def test_phase5_email_reply_draft_migration_declares_contracts() -> None:
    assert MIGRATION_PATH.exists()
    migration = MIGRATION_PATH.read_text(encoding="utf-8")

    assert 'revision = "20260605_0031"' in migration
    assert 'down_revision = "20260605_0030"' in migration
    assert '"email_reply_drafts"' in migration
    assert "emailreplydraftstatus" in migration

    for column_name in (
        "thread_id",
        "message_id",
        "customer_id",
        "agent_service_run_id",
        "agent_task_run_id",
        "prompt_template_id",
        "prompt_version",
        "model",
        "ai_suggested_subject",
        "ai_suggested_body",
        "final_subject",
        "final_body",
        "knowledge_hits_json",
        "auto_send_allowed",
        "auto_send_decision_json",
        "manual_review_required",
        "sent_record_id",
    ):
        assert column_name in migration

    for foreign_key in (
        "email_threads.id",
        "email_messages.id",
        "customers.id",
        "agent_task_runs.id",
        "llm_prompt_templates.id",
        "outreach_records.id",
    ):
        assert foreign_key in migration

    assert "drop_table" in migration
