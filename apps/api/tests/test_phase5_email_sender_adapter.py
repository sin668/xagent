import pytest

from app.services.email_sender import EmailMessagePayload, EmailSendResult, EmailSender, EmailSenderConfigurationError
from app.settings import Settings


def build_settings(**overrides) -> Settings:
    values = {
        "_env_file": None,
        "EMAIL_SENDER_PROVIDER": "fake",
        "EMAIL_SENDER_FROM_EMAIL": "sales@example.com",
        "SMTP_HOST": "smtp.example.com",
        "SMTP_PORT": "587",
        "SMTP_USERNAME": "smtp-user",
        "SMTP_PASSWORD": "smtp-pass",
        "SMTP_USE_TLS": "true",
        **overrides,
    }
    return Settings(**values)


def make_message() -> EmailMessagePayload:
    return EmailMessagePayload(
        from_email="sales@example.com",
        to_emails=["dealer@example.ru"],
        cc_emails=["manager@example.com"],
        bcc_emails=[],
        subject="Vehicle procurement follow-up",
        body_text="Hello, thanks for your message.",
        body_html="<p>Hello, thanks for your message.</p>",
        metadata={"draft_id": "draft-1"},
    )


def test_email_sender_fake_provider_returns_deterministic_result() -> None:
    sender = EmailSender.from_settings(build_settings(EMAIL_SENDER_PROVIDER="fake"))

    result = sender.send(make_message())

    assert isinstance(result, EmailSendResult)
    assert result.provider == "fake"
    assert result.status == "sent"
    assert result.provider_message_id.startswith("fake-")
    assert result.error_code is None
    assert result.error_message is None


def test_email_sender_rejects_unknown_provider_without_sending() -> None:
    with pytest.raises(EmailSenderConfigurationError) as exc_info:
        EmailSender.from_settings(build_settings(EMAIL_SENDER_PROVIDER="unknown"))

    assert "unknown" in str(exc_info.value)


def test_email_sender_uses_smtp_provider_with_injected_factory() -> None:
    sent_messages: list[dict] = []

    class FakeSMTP:
        def __init__(self, host: str, port: int, timeout: int) -> None:
            self.host = host
            self.port = port
            self.timeout = timeout
            self.started_tls = False
            self.logged_in = None

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback) -> None:
            return None

        def starttls(self) -> None:
            self.started_tls = True

        def login(self, username: str, password: str) -> None:
            self.logged_in = (username, password)

        def send_message(self, message) -> None:
            sent_messages.append(
                {
                    "host": self.host,
                    "port": self.port,
                    "timeout": self.timeout,
                    "started_tls": self.started_tls,
                    "logged_in": self.logged_in,
                    "from": message["From"],
                    "to": message["To"],
                    "cc": message["Cc"],
                    "subject": message["Subject"],
                    "body": message.get_body(preferencelist=("plain",)).get_content(),
                }
            )

    sender = EmailSender.from_settings(
        build_settings(EMAIL_SENDER_PROVIDER="smtp"),
        smtp_factory=FakeSMTP,
    )

    result = sender.send(make_message())

    assert result.provider == "smtp"
    assert result.status == "sent"
    assert result.provider_message_id.startswith("smtp-")
    assert sent_messages == [
        {
            "host": "smtp.example.com",
            "port": 587,
            "timeout": 30,
            "started_tls": True,
            "logged_in": ("smtp-user", "smtp-pass"),
            "from": "sales@example.com",
            "to": "dealer@example.ru",
            "cc": "manager@example.com",
            "subject": "Vehicle procurement follow-up",
            "body": "Hello, thanks for your message.\n",
        }
    ]


def test_email_sender_settings_support_provider_aliases() -> None:
    settings = build_settings(
        EMAIL_SENDER_PROVIDER="sendgrid",
        SENDGRID_API_KEY="sg-key",
        MAILGUN_API_KEY="mg-key",
        MAILGUN_DOMAIN="mg.example.com",
    )

    assert settings.email_sender_provider == "sendgrid"
    assert settings.email_sender_from_email == "sales@example.com"
    assert settings.sendgrid_api_key.get_secret_value() == "sg-key"
    assert settings.mailgun_api_key.get_secret_value() == "mg-key"
    assert settings.mailgun_domain == "mg.example.com"
