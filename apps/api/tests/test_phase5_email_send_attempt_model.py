from pathlib import Path

from sqlalchemy import inspect

from app.models.email_reply_draft import EmailReplyDraft
from app.models.enums import EmailSendAttemptStatus
from app.models.outreach_record import OutreachRecord


API_ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = API_ROOT / "alembic" / "versions" / "20260605_0032_create_email_send_attempts.py"


def test_phase5_email_send_attempt_status_enum_defines_delivery_lifecycle() -> None:
    assert EmailSendAttemptStatus.PENDING == "pending"
    assert EmailSendAttemptStatus.SENDING == "sending"
    assert EmailSendAttemptStatus.SENT == "sent"
    assert EmailSendAttemptStatus.FAILED == "failed"
    assert EmailSendAttemptStatus.RETRY_PENDING == "retry_pending"
    assert EmailSendAttemptStatus.BOUNCED == "bounced"
    assert EmailSendAttemptStatus.BLOCKED == "blocked"


def test_phase5_email_send_attempt_model_records_provider_snapshot_and_failures() -> None:
    from app.models import EmailSendAttempt

    columns = inspect(EmailSendAttempt).columns

    for column_name in (
        "id",
        "reply_draft_id",
        "outreach_record_id",
        "provider",
        "provider_message_id",
        "from_email",
        "to_emails",
        "cc_emails",
        "bcc_emails",
        "subject_snapshot",
        "body_text_snapshot",
        "body_html_snapshot",
        "status",
        "attempt_count",
        "error_code",
        "error_message",
        "bounce_reason",
        "sent_at",
        "created_at",
        "updated_at",
    ):
        assert column_name in columns

    assert columns["provider"].nullable is False
    assert columns["from_email"].nullable is False
    assert columns["to_emails"].nullable is False
    assert columns["subject_snapshot"].nullable is False
    assert columns["body_text_snapshot"].nullable is False
    assert columns["status"].index is True
    assert columns["provider_message_id"].index is True
    assert columns["attempt_count"].nullable is False
    assert columns["error_message"].nullable is True
    assert columns["bounce_reason"].nullable is True

    assert hasattr(EmailReplyDraft, "send_attempts")
    assert hasattr(OutreachRecord, "email_send_attempts")


def test_phase5_email_send_attempt_migration_declares_contracts() -> None:
    assert MIGRATION_PATH.exists()
    migration = MIGRATION_PATH.read_text(encoding="utf-8")

    assert 'revision = "20260605_0032"' in migration
    assert 'down_revision = "20260605_0031"' in migration
    assert '"email_send_attempts"' in migration
    assert "emailsendattemptstatus" in migration

    for column_name in (
        "reply_draft_id",
        "outreach_record_id",
        "provider",
        "provider_message_id",
        "from_email",
        "to_emails",
        "cc_emails",
        "bcc_emails",
        "subject_snapshot",
        "body_text_snapshot",
        "body_html_snapshot",
        "status",
        "attempt_count",
        "error_code",
        "error_message",
        "bounce_reason",
        "sent_at",
    ):
        assert column_name in migration

    assert "email_reply_drafts.id" in migration
    assert "outreach_records.id" in migration
    assert "drop_table" in migration
