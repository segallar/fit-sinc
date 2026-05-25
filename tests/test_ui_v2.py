"""UI v2 scaffold — без сети."""

import unittest

from fastapi.testclient import TestClient


class TestUiV2(unittest.TestCase):
    def test_render_template(self) -> None:
        from fit_sinc.web.templating import render_template

        html = render_template(
            "fragments/status_panel.html",
            jwt_ttl="2h",
            activity_count=3,
        )
        self.assertIn("Garmin JWT TTL", html)
        self.assertIn("2h", html)

    def test_ui_preview_routes(self) -> None:
        from fit_sinc.web.app import app

        client = TestClient(app)
        r = client.get("/ui-preview")
        self.assertEqual(r.status_code, 200)
        self.assertIn("UI v2 preview", r.text)
        self.assertIn("/static/app.css", r.text)

        frag = client.get("/ui-preview/fragment/status")
        self.assertEqual(frag.status_code, 200)
        self.assertIn("Garmin JWT TTL", frag.text)


if __name__ == "__main__":
    unittest.main()
