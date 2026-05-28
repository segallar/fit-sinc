"""Mail module (2.1e) — no network in default tests."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from getsync.mail import MailConfigurationError, MailSendError, get_mailer, send_email
from getsync.mail.backends.base import EmailMessage
from getsync.mail.backends.resend import ResendMailer
from helpers import isolated_env


class TestNullMailer(unittest.TestCase):
    def test_send_email_no_network(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp), MAIL_FROM="GetSync <test@example.com>"):
                result = send_email(
                    to="user@test.local",
                    subject="Test",
                    html="<p>Hi</p>",
                )
                self.assertIsNone(result.message_id)
                self.assertEqual(result.backend, "null")


class TestResendMailer(unittest.TestCase):
    def test_missing_api_key_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp), MAIL_BACKEND="resend", RESEND_API_KEY=""):
                with self.assertRaises(MailConfigurationError):
                    get_mailer()

    def test_resend_success(self) -> None:
        mailer = ResendMailer("re_test_key")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "msg_123"}

        with patch("getsync.mail.backends.resend.httpx.post", return_value=mock_response) as post:
            result = mailer.send(
                EmailMessage(
                    from_addr="onboarding@resend.dev",
                    to="roman@segalla.ru",
                    subject="Hello World",
                    html="<p>Congrats</p>",
                )
            )

        self.assertEqual(result.message_id, "msg_123")
        self.assertEqual(result.backend, "resend")
        post.assert_called_once()
        call_kwargs = post.call_args.kwargs
        self.assertEqual(call_kwargs["json"]["to"], ["roman@segalla.ru"])
        self.assertEqual(call_kwargs["headers"]["Authorization"], "Bearer re_test_key")

    def test_resend_api_error(self) -> None:
        mailer = ResendMailer("re_test_key")
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.reason_phrase = "Forbidden"
        mock_response.text = '{"message":"Invalid API key"}'

        with patch("getsync.mail.backends.resend.httpx.post", return_value=mock_response):
            with self.assertRaises(MailSendError):
                mailer.send(
                    EmailMessage(
                        from_addr="onboarding@resend.dev",
                        to="user@test.local",
                        subject="Hi",
                        html="<p>x</p>",
                    )
                )
