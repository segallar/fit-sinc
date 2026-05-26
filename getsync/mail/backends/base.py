from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class EmailMessage:
    to: str | list[str]
    subject: str
    html: str | None = None
    text: str | None = None
    from_addr: str = ""
    reply_to: str | None = None
    tags: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class SendResult:
    message_id: str | None
    backend: str


class MailBackend:
    name: str = "base"

    def send(self, message: EmailMessage) -> SendResult:
        raise NotImplementedError
