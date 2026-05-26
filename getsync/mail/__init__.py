from getsync.mail.backends.base import EmailMessage, SendResult
from getsync.mail.backends.resend import MailSendError
from getsync.mail.service import MailConfigurationError, get_mailer, send_email

__all__ = [
    "EmailMessage",
    "MailConfigurationError",
    "MailSendError",
    "SendResult",
    "get_mailer",
    "send_email",
]
