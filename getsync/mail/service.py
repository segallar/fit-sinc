from __future__ import annotations

from getsync.config import Settings, get_settings
from getsync.mail.backends.base import EmailMessage, MailBackend, SendResult
from getsync.mail.backends.console import ConsoleMailer
from getsync.mail.backends.null import NullMailer
from getsync.mail.backends.resend import ResendMailer


class MailConfigurationError(RuntimeError):
    pass


def get_mailer(settings: Settings | None = None) -> MailBackend:
    cfg = settings or get_settings()
    backend = cfg.mail_backend.strip().lower() or "null"

    if backend == "null":
        return NullMailer()
    if backend == "console":
        return ConsoleMailer()
    if backend == "resend":
        if not cfg.resend_api_key.strip():
            raise MailConfigurationError(
                "RESEND_API_KEY is required when MAIL_BACKEND=resend"
            )
        return ResendMailer(cfg.resend_api_key)

    raise MailConfigurationError(f"Unknown MAIL_BACKEND: {backend!r}")


def send_email(
    to: str | list[str],
    subject: str,
    *,
    html: str | None = None,
    text: str | None = None,
    from_addr: str | None = None,
    reply_to: str | None = None,
    tags: list[str] | None = None,
    settings: Settings | None = None,
) -> SendResult:
    cfg = settings or get_settings()
    sender = from_addr or cfg.mail_from
    if not sender.strip():
        raise MailConfigurationError("MAIL_FROM is required to send email")

    message = EmailMessage(
        to=to,
        subject=subject,
        html=html,
        text=text,
        from_addr=sender,
        reply_to=reply_to or cfg.mail_reply_to or None,
        tags=tags or [],
    )
    return get_mailer(cfg).send(message)
