from pathlib import Path

from sqlalchemy import inspect

from app.models.customer import Customer
from app.models.enums import EmailMessageDirection, EmailMessageSourceType, EmailMessageStatus, EmailThreadStatus


API_ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = API_ROOT / "alembic" / "versions" / "20260605_0030_create_email_threads_messages.py"


def test_phase5_email_enums_define_thread_message_import_contracts() -> None:
    assert EmailThreadStatus.OPEN == "open"
    assert EmailThreadStatus.WAITING_REPLY == "waiting_reply"
    assert EmailThreadStatus.REPLIED == "replied"
    assert EmailThreadStatus.ARCHIVED == "archived"
    assert EmailThreadStatus.BLOCKED == "blocked"

    assert EmailMessageDirection.INBOUND == "inbound"
    assert EmailMessageDirection.OUTBOUND == "outbound"

    assert EmailMessageStatus.RECEIVED == "received"
    assert EmailMessageStatus.PENDING_REPLY == "pending_reply"
    assert EmailMessageStatus.DRAFTED == "drafted"
    assert EmailMessageStatus.SENT == "sent"
    assert EmailMessageStatus.FAILED == "failed"
    assert EmailMessageStatus.ARCHIVED == "archived"

    assert EmailMessageSourceType.MANUAL == "manual"
    assert EmailMessageSourceType.API_IMPORT == "api_import"
    assert EmailMessageSourceType.MAILBOX_SYNC == "mailbox_sync"


def test_phase5_email_models_are_registered_and_related_to_customer() -> None:
    from app.models import EmailMessage, EmailThread

    thread_columns = inspect(EmailThread).columns
    message_columns = inspect(EmailMessage).columns

    for column_name in (
        "id",
        "customer_id",
        "subject",
        "status",
        "channel_account",
        "last_message_at",
        "created_at",
        "updated_at",
    ):
        assert column_name in thread_columns

    for column_name in (
        "id",
        "thread_id",
        "customer_id",
        "direction",
        "from_email",
        "to_emails",
        "cc_emails",
        "subject",
        "body_text",
        "body_html",
        "language",
        "status",
        "source_type",
        "external_message_id",
        "created_at",
        "updated_at",
    ):
        assert column_name in message_columns

    assert hasattr(Customer, "email_threads")
    assert hasattr(Customer, "email_messages")


def test_phase5_email_threads_messages_migration_declares_contracts() -> None:
    assert MIGRATION_PATH.exists()
    migration = MIGRATION_PATH.read_text(encoding="utf-8")

    assert 'revision = "20260605_0030"' in migration
    assert 'down_revision = "20260605_0029"' in migration
    assert '"email_threads"' in migration
    assert '"email_messages"' in migration

    for enum_name in (
        "emailthreadstatus",
        "emailmessagedirection",
        "emailmessagestatus",
        "emailmessagesourcetype",
    ):
        assert enum_name in migration

    for column_name in (
        "customer_id",
        "thread_id",
        "direction",
        "source_type",
        "external_message_id",
        "last_message_at",
    ):
        assert column_name in migration

    assert "customers.id" in migration
    assert "ondelete=\"SET NULL\"" in migration
    assert "drop_table" in migration
