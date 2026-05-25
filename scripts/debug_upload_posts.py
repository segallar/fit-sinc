#!/usr/bin/env python3
import json
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

posts: list[str] = []

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True, args=list(CHROMIUM_ARGS))
    context = browser.new_context(user_agent=USER_AGENT, locale="ru-RU")
    context.add_cookies(_cookies_for_playwright(sess["cookies"]))
    page = context.new_page()

    def on_resp(r):
        if r.request.method == "POST":
            posts.append(f"{r.status} {r.url[:140]}")

    page.on("response", on_resp)
    page.goto(IMPORT_URL, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(8000)
    handle = page.evaluate_handle(_FIND_FILE_INPUT_JS)
    el = handle.as_element()
    print("file input found", el is not None)
    with tempfile.NamedTemporaryFile(suffix=".fit", delete=False) as tmp:
        tmp.write(fit.read_bytes())
        path = tmp.name
    el.set_input_files(path)
    page.wait_for_timeout(30000)
    print("POST responses:")
    for p in posts:
        print(" ", p)
    print("page text snippet:", page.inner_text("body")[:400])
    browser.close()
