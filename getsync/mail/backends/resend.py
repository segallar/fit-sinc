from __future__ import annotations

import httpx

from getsync.mail.backends.base import EmailMessage, MailBackend, SendResult


class MailSendError(RuntimeError):
    pass


class ResendMailer(MailBackend):
    name = "resend"
    _api_url = "https://api.resend.com/emails"

    def __init__(self, api_key: str) -> None:
        key = api_key.strip()
        if not key:
            raise ValueError("Resend API key is required")
        self._api_key = key

    def send(self, message: EmailMessage) -> SendResult:
        if not message.from_addr:
            raise MailSendError("from_addr is required for Resend")

        recipients = message.to if isinstance(message.to, list) else [message.to]
        payload: dict[str, object] = {
            "from": message.from_addr,
            "to": recipients,
            "subject": message.subject,
        }
        if message.html:
            payload["html"] = message.html
        if message.text:
            payload["text"] = message.text
        if message.reply_to:
            payload["reply_to"] = message.reply_to
        if message.tags:
            payload["tags"] = [{"name": tag} for tag in message.tags]

        try:
            response = httpx.post(
                self._api_url,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=30.0,
            )
        except httpx.HTTPError as exc:
            raise MailSendError(f"Resend request failed: {exc}") from exc

        if response.status_code >= 400:
            detail = response.text.strip() or response.reason_phrase
            raise MailSendError(f"Resend API error {response.status_code}: {detail}")

        data = response.json()
        message_id = data.get("id")
        if not isinstance(message_id, str):
            raise MailSendError(f"Unexpected Resend response: {data!r}")

        return SendResult(message_id=message_id, backend=self.name)
