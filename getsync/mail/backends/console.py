from __future__ import annotations

import sys

from getsync.mail.backends.base import EmailMessage, MailBackend, SendResult


class ConsoleMailer(MailBackend):
    name = "console"

    def send(self, message: EmailMessage) -> SendResult:
        recipients = message.to if isinstance(message.to, list) else [message.to]
        print(
            f"[mail:console] from={message.from_addr!r} to={recipients!r} "
            f"subject={message.subject!r}",
            file=sys.stderr,
        )
        if message.text:
            print(message.text, file=sys.stderr)
        elif message.html:
            print(message.html, file=sys.stderr)
        return SendResult(message_id="console", backend=self.name)
