from __future__ import annotations

import logging

from getsync.mail.backends.base import EmailMessage, MailBackend, SendResult

logger = logging.getLogger(__name__)


class NullMailer(MailBackend):
    name = "null"

    def send(self, message: EmailMessage) -> SendResult:
        recipients = message.to if isinstance(message.to, list) else [message.to]
        logger.info(
            "mail skipped (null backend) to=%s subject=%r from=%s",
            recipients,
            message.subject,
            message.from_addr,
        )
        return SendResult(message_id=None, backend=self.name)
