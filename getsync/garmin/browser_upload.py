"""Garmin Connect FIT upload via headless Chromium (Playwright).

Flow: /app/import-data → accept consent → shadow file input → «Import data» button.
"""

from __future__ import annotations

import json
import logging
import re
import tempfile
from pathlib import Path
from typing import Any

from getsync.users.context import UserContext, as_context
from getsync.garmin.web_session import web_resume

logger = logging.getLogger("getsync.garmin.browser")

IMPORT_URL = "https://connect.garmin.com/app/import-data"
REFRESH_URL = "https://connect.garmin.com/modern/"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)
CHROMIUM_ARGS = (
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--disable-gpu",
    "--disable-software-rasterizer",
)
IMPORT_BTN = re.compile(r"^(Import data|Импорт данных)$", re.I)
CONSENT_BTN = re.compile(r"Accept|Принимаю|I agree|Continue|Продолж", re.I)

_FIND_FILE_INPUT_JS = """
() => {
  const walk = (root) => {
    const direct = root.querySelector('input[type="file"]');
    if (direct) return direct;
    for (const el of root.querySelectorAll('*')) {
      if (el.shadowRoot) {
        const found = walk(el.shadowRoot);
        if (found) return found;
      }
    }
    return null;
  };
  return walk(document);
}
"""


def _cookies_for_playwright(cookies: dict[str, str]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for name, value in cookies.items():
        if not value:
            continue
        for domain in (".garmin.com", "connect.garmin.com"):
            key = (name, domain)
            if key in seen:
                continue
            seen.add(key)
            items.append(
                {
                    "name": name,
                    "value": value,
                    "domain": domain,
                    "path": "/",
                    "secure": True,
                    "sameSite": "Lax",
                }
            )
    return items


def _is_upload_response(url: str, method: str, status: int) -> bool:
    if method.upper() != "POST" or status not in (200, 201, 409):
        return False
    lower = url.lower()
    return "upload-service" in lower or (
        "upload" in lower and "gdpr" not in lower and "sentry" not in lower
    )


def _parse_upload_payload(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise RuntimeError(f"Unexpected Garmin upload response: {payload!r}")

    result = payload.get("detailedImportResult", payload)
    if not isinstance(result, dict):
        raise RuntimeError(f"Unexpected Garmin upload result: {result!r}")

    successes = result.get("successes") or []
    if successes:
        return {"status": "uploaded", "detailedImportResult": result, "method": "browser"}

    failures = result.get("failures") or []
    if failures:
        messages = failures[0].get("messages") or []
        if messages and messages[0].get("code") == 202:
            return {
                "status": "duplicate",
                "detailedImportResult": result,
                "activity_id": failures[0].get("internalId"),
                "method": "browser",
            }
        msg = messages[0].get("content") if messages else str(failures[0])
        raise RuntimeError(f"Garmin upload rejected: {msg}")

    return {"status": "uploaded", "detailedImportResult": result, "method": "browser"}


def _parse_upload_response_body(body: str) -> dict[str, Any]:
    try:
        return _parse_upload_payload(json.loads(body))
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Garmin browser upload returned non-JSON: {body[:200]}"
        ) from exc


def _wait_for_file_input(page: Any, timeout_ms: int = 60_000) -> Any:
    for _ in range(timeout_ms // 500):
        handle = page.evaluate_handle(_FIND_FILE_INPUT_JS)
        element = handle.as_element()
        if element is not None:
            return element
        page.wait_for_timeout(500)
    raise RuntimeError("Garmin import page: file input not found (shadow DOM timeout)")


def _accept_consent_if_needed(page: Any) -> None:
    consent = page.get_by_role("button", name=CONSENT_BTN)
    if consent.count() > 0:
        consent.first.click()
        page.wait_for_timeout(1500)


def refresh_cookies_via_browser(existing: dict[str, str]) -> dict[str, str] | None:
    """Refresh JWT_WEB in headless Chromium using the `session` cookie."""
    import asyncio
    import concurrent.futures

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return _refresh_cookies_via_browser_sync(existing)

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(_refresh_cookies_via_browser_sync, existing)
        return future.result(timeout=120)


def _refresh_cookies_via_browser_sync(existing: dict[str, str]) -> dict[str, str] | None:
    from getsync.garmin.web_session import _has_session_cookie, _jwt_valid

    session = existing.get("session") or existing.get("SESSION")
    if not _has_session_cookie(existing):
        return None

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.warning("Playwright unavailable — skip browser JWT refresh")
        return None

    seed = {"session": session} if session else existing
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, args=list(CHROMIUM_ARGS))
        try:
            context = browser.new_context(
                user_agent=USER_AGENT,
                locale="ru-RU",
                viewport={"width": 1280, "height": 900},
            )
            context.add_cookies(_cookies_for_playwright(seed))
            page = context.new_page()
            page.goto(REFRESH_URL, wait_until="domcontentloaded", timeout=60_000)
            if "sign-in" in page.url.lower() or "signin" in page.url.lower():
                return None
            page.wait_for_timeout(5000)
            refreshed = {
                c["name"]: c["value"]
                for c in context.cookies()
                if "garmin.com" in c.get("domain", "")
            }
        finally:
            browser.close()

    merged = {**existing, **refreshed}
    if not _jwt_valid(merged.get("JWT_WEB")):
        return None
    return merged


def upload_fit_via_browser(
    fit_bytes: bytes,
    filename: str,
    ctx: UserContext | None = None,
) -> dict[str, Any]:
    """Upload FIT via Garmin Connect import-data UI in headless Chromium."""
    import asyncio
    import concurrent.futures

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return _upload_fit_via_browser_sync(fit_bytes, filename, ctx)

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(
            _upload_fit_via_browser_sync, fit_bytes, filename, ctx
        )
        return future.result(timeout=180)


def _upload_fit_via_browser_sync(
    fit_bytes: bytes,
    filename: str,
    ctx: UserContext | None = None,
) -> dict[str, Any]:
    try:
        from playwright.sync_api import TimeoutError as PlaywrightTimeout
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError(
            "Playwright not installed — run: pip install playwright && playwright install chromium"
        ) from exc

    user_ctx = as_context(ctx)
    cookies = web_resume(user_ctx)
    if not cookies:
        raise RuntimeError(
            "Garmin web session not available — run: getsync garmin import-web-cookies"
        )

    safe_name = filename if filename.endswith(".fit") else f"{filename}.fit"
    tmp_path: Path | None = None
    captured: list[tuple[int, str, str]] = []

    try:
        with tempfile.NamedTemporaryFile(suffix=".fit", delete=False) as tmp:
            tmp.write(fit_bytes)
            tmp_path = Path(tmp.name)

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True, args=list(CHROMIUM_ARGS))
            try:
                context = browser.new_context(
                    user_agent=USER_AGENT,
                    locale="ru-RU",
                    viewport={"width": 1280, "height": 900},
                )
                context.add_cookies(_cookies_for_playwright(cookies))
                page = context.new_page()

                def on_response(response: Any) -> None:
                    req = response.request
                    if not _is_upload_response(
                        response.url, req.method, response.status
                    ):
                        return
                    try:
                        body = response.text()
                    except Exception:
                        body = ""
                    captured.append((response.status, response.url, body))

                page.on("response", on_response)
                page.goto(IMPORT_URL, wait_until="domcontentloaded", timeout=60_000)

                if "sign-in" in page.url.lower() or "signin" in page.url.lower():
                    raise RuntimeError(
                        "Garmin browser session expired — re-import cookies from Chrome"
                    )

                page.wait_for_timeout(8000)
                _accept_consent_if_needed(page)

                file_input = _wait_for_file_input(page)
                file_input.set_input_files(str(tmp_path))
                page.wait_for_timeout(1000)

                import_btn = page.get_by_role("button", name=IMPORT_BTN)
                if import_btn.count() == 0:
                    raise RuntimeError("Garmin import page: «Import data» button not found")
                import_btn.first.click()

                for _ in range(120):
                    for _status, url, body in captured:
                        if body.lstrip().startswith("{"):
                            logger.info(
                                "Garmin browser upload OK (%s via %s)",
                                safe_name,
                                url,
                            )
                            return _parse_upload_response_body(body)
                    page.wait_for_timeout(1000)

                if captured:
                    status, url, body = captured[-1]
                    raise RuntimeError(
                        f"Garmin upload response not JSON ({status} {url}): {body[:200]}"
                    )
                raise RuntimeError(
                    "Garmin browser upload timed out — no upload response in 120s"
                )
            finally:
                browser.close()
    except PlaywrightTimeout as exc:
        raise RuntimeError(f"Garmin browser upload timeout: {exc}") from exc
    finally:
        if tmp_path and tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
