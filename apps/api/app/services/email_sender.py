from __future__ import annotations

import smtplib
from dataclasses import dataclass, field
from email.message import EmailMessage
from uuid import uuid4

from app.settings import Settings, settings


class EmailSenderError(RuntimeError):
    pass


class EmailSenderConfigurationError(EmailSenderError):
    pass


class EmailSenderDeliveryError(EmailSenderError):
    pass


@dataclass(frozen=True, slots=True)
class EmailMessagePayload:
    from_email: str
    to_emails: list[str]
    subject: str
    body_text: str
    cc_emails: list[str] = field(default_factory=list)
    bcc_emails: list[str] = field(default_factory=list)
    body_html: str | None = None
    metadata: dict | None = None


@dataclass(frozen=True, slots=True)
class EmailSendResult:
    provider: str
    status: str
    provider_message_id: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    raw_response: dict | None = None


class EmailProviderAdapter:
    provider: str

    def send(self, message: EmailMessagePayload) -> EmailSendResult:
        raise NotImplementedError


class FakeEmailProvider(EmailProviderAdapter):
    provider = "fake"

    def send(self, message: EmailMessagePayload) -> EmailSendResult:
        EmailSender.validate_message(message)
        return EmailSendResult(
            provider=self.provider,
            status="sent",
            provider_message_id=f"fake-{uuid4()}",
            raw_response={"recipient_count": len(message.to_emails)},
        )


class SMTPEmailProvider(EmailProviderAdapter):
    provider = "smtp"

    def __init__(
        self,
        *,
        host: str,
        port: int,
        username: str | None,
        password: str | None,
        use_tls: bool,
        timeout_seconds: int,
        smtp_factory=None,
    ) -> None:
        if not host:
            raise EmailSenderConfigurationError("SMTP provider requires SMTP_HOST.")
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.use_tls = use_tls
        self.timeout_seconds = timeout_seconds
        self.smtp_factory = smtp_factory or smtplib.SMTP

    def send(self, message: EmailMessagePayload) -> EmailSendResult:
        EmailSender.validate_message(message)
        email_message = self._build_message(message)
        try:
            with self.smtp_factory(self.host, self.port, timeout=self.timeout_seconds) as smtp:
                if self.use_tls:
                    smtp.starttls()
                if self.username:
                    smtp.login(self.username, self.password or "")
                smtp.send_message(email_message)
        except Exception as exc:
            raise EmailSenderDeliveryError(str(exc)) from exc
        return EmailSendResult(
            provider=self.provider,
            status="sent",
            provider_message_id=f"smtp-{uuid4()}",
            raw_response={"recipient_count": len(message.to_emails)},
        )

    @staticmethod
    def _build_message(payload: EmailMessagePayload) -> EmailMessage:
        message = EmailMessage()
        message["From"] = payload.from_email
        message["To"] = ", ".join(payload.to_emails)
        if payload.cc_emails:
            message["Cc"] = ", ".join(payload.cc_emails)
        if payload.bcc_emails:
            message["Bcc"] = ", ".join(payload.bcc_emails)
        message["Subject"] = payload.subject
        message.set_content(payload.body_text)
        if payload.body_html:
            message.add_alternative(payload.body_html, subtype="html")
        return message


class ExtensionEmailProvider(EmailProviderAdapter):
    def __init__(self, provider: str, *, configured: bool) -> None:
        self.provider = provider
        self.configured = configured

    def send(self, message: EmailMessagePayload) -> EmailSendResult:
        EmailSender.validate_message(message)
        if not self.configured:
            raise EmailSenderConfigurationError(f"{self.provider} provider is selected but required credentials are missing.")
        raise EmailSenderConfigurationError(f"{self.provider} provider adapter is not enabled in phase 5 small-run.")


class EmailSender:
    SUPPORTED_PROVIDERS = {"fake", "smtp", "sendgrid", "mailgun", "enterprise_mail"}

    def __init__(self, adapter: EmailProviderAdapter) -> None:
        self.adapter = adapter

    @classmethod
    def from_settings(cls, config: Settings = settings, *, smtp_factory=None) -> "EmailSender":
        provider = str(config.email_sender_provider or "fake").strip().lower()
        if provider not in cls.SUPPORTED_PROVIDERS:
            raise EmailSenderConfigurationError(f"Unsupported email sender provider: {provider}")
        if provider == "fake":
            return cls(FakeEmailProvider())
        if provider == "smtp":
            return cls(
                SMTPEmailProvider(
                    host=config.smtp_host or "",
                    port=config.smtp_port,
                    username=config.smtp_username,
                    password=config.smtp_password.get_secret_value() if config.smtp_password else None,
                    use_tls=config.smtp_use_tls,
                    timeout_seconds=config.smtp_timeout_seconds,
                    smtp_factory=smtp_factory,
                )
            )
        if provider == "sendgrid":
            return cls(ExtensionEmailProvider(provider, configured=bool(config.sendgrid_api_key)))
        if provider == "mailgun":
            return cls(ExtensionEmailProvider(provider, configured=bool(config.mailgun_api_key and config.mailgun_domain)))
        return cls(ExtensionEmailProvider(provider, configured=bool(config.enterprise_mail_api_key and config.enterprise_mail_base_url)))

    def send(self, message: EmailMessagePayload) -> EmailSendResult:
        return self.adapter.send(message)

    @staticmethod
    def validate_message(message: EmailMessagePayload) -> None:
        if not message.from_email.strip():
            raise EmailSenderConfigurationError("Email sender requires from_email.")
        if not message.to_emails:
            raise EmailSenderConfigurationError("Email sender requires at least one recipient.")
        if not message.subject.strip():
            raise EmailSenderConfigurationError("Email sender requires subject.")
        if not message.body_text.strip() and not (message.body_html or "").strip():
            raise EmailSenderConfigurationError("Email sender requires body content.")
