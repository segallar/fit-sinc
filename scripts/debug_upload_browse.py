#!/usr/bin/env python3
import json
import re
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

from fit_sinc.garmin.browser_upload import (
    CHROMIUM_ARGS,
    IMPORT_URL,
    USER_AGENT,
    _FIND_FILE_INPUT_JS,
    _cookies_for_playwright,
)

sess = json.loads(Path("data/garmin_web/session.json").read_text())
fit = next(Path("data/fits").glob("*.fit"))
hits: list[str] = []

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True, args=list(CHROMIUM_ARGS))
    context = browser.new_context(user_agent=USER_AGENT, locale="ru-RU")
    context.add_cookies(_cookies_for_playwright(sess["cookies"]))
    page = context.new_page()

    def on_resp(r):
        if "upload" in r.url.lower() or "import" in r.url.lower():
            hits.append(f"{r.request.method} {r.status} {r.url[:160]}")

    page.on("response", on_resp)
    page.goto(IMPORT_URL, wait_until="domcontentloaded")
    page.wait_for_timeout(10000)

    with tempfile.NamedTemporaryFile(suffix=".fit", delete=False) as tmp:
        tmp.write(fit.read_bytes())
        path = tmp.name

    browse = page.get_by_role("button", name=re.compile(r"Обзор|Browse", re.I))
    print("browse buttons", browse.count())
    if browse.count():
        with page.expect_file_chooser(timeout=15000) as fc_info:
            browse.first.click()
        fc_info.value.set_files(path)
    else:
        handle = page.evaluate_handle(_FIND_FILE_INPUT_JS)
        handle.as_element().set_input_files(path)

    page.wait_for_timeout(60000)
    print("upload/import responses:")
    for h in hits:
        print(" ", h)
    browser.close()
