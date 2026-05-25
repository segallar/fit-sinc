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
posts: list[str] = []

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True, args=list(CHROMIUM_ARGS))
    context = browser.new_context(user_agent=USER_AGENT, locale="ru-RU")
    context.add_cookies(_cookies_for_playwright(sess["cookies"]))
    page = context.new_page()

    def on_resp(r):
        u = r.url.lower()
        if r.request.method == "POST" or "upload" in u:
            posts.append(f"{r.request.method} {r.status} {r.url[:130]}")

    page.on("response", on_resp)
    page.goto(IMPORT_URL, wait_until="domcontentloaded")
    page.wait_for_timeout(10000)

    # consent / accept buttons
    for pat in [
        r"Принимаю|Accept|Соглас|I agree|Continue|Продолж",
        r"Обзор|Browse",
    ]:
        loc = page.get_by_role("button", name=re.compile(pat, re.I))
        print(pat, "buttons", loc.count())
        if loc.count():
            for i in range(min(loc.count(), 3)):
                print(" ", i, loc.nth(i).inner_text()[:60])

    # try click accept/consent if present
    accept = page.get_by_role("button", name=re.compile(r"Принимаю|Accept|Соглас|Continue|Продолж", re.I))
    if accept.count():
        accept.first.click()
        page.wait_for_timeout(2000)

    checkbox = page.locator('input[type="checkbox"]')
    print("checkboxes", checkbox.count())
    if checkbox.count():
        checkbox.first.check(force=True)
        page.wait_for_timeout(1000)

    with tempfile.NamedTemporaryFile(suffix=".fit", delete=False) as tmp:
        tmp.write(fit.read_bytes())
        path = tmp.name

    handle = page.evaluate_handle(_FIND_FILE_INPUT_JS)
    handle.as_element().set_input_files(path)
    page.wait_for_timeout(2000)

    # click submit/import if appears
    submit = page.get_by_role("button", name=re.compile(r"Импорт|Import|Upload|Загруз", re.I))
    print("submit buttons", submit.count())
    if submit.count():
        submit.first.click()

    page.wait_for_timeout(30000)
    print("--- responses ---")
    for p in posts:
        print(p)
    print("body tail:", page.inner_text("body")[-400:])
    browser.close()
