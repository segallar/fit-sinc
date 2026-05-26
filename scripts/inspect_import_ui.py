#!/usr/bin/env python3
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

from getsync.garmin.browser_upload import CHROMIUM_ARGS, USER_AGENT, _cookies_for_playwright

sess = json.loads(Path("data/garmin_web/session.json").read_text())

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True, args=list(CHROMIUM_ARGS))
    context = browser.new_context(user_agent=USER_AGENT, locale="ru-RU")
    context.add_cookies(_cookies_for_playwright(sess["cookies"]))
    page = context.new_page()
    for url in (
        "https://connect.garmin.com/app/import-data",
        "https://connect.garmin.com/modern/import-data",
    ):
        page.goto(url, wait_until="networkidle", timeout=90000)
        page.wait_for_timeout(8000)
        count = page.evaluate(
            """() => {
              let n = 0;
              const walk = (root) => {
                root.querySelectorAll('input[type=file]').forEach(() => n++);
                root.querySelectorAll('*').forEach(el => {
                  if (el.shadowRoot) walk(el.shadowRoot);
                });
              };
              walk(document);
              return n;
            }"""
        )
        labels = page.evaluate(
            """() => Array.from(document.querySelectorAll('[aria-label], [title], label, h1, h2, h3, button'))
              .map(el => (el.getAttribute('aria-label') || el.getAttribute('title') || el.textContent || '').trim())
              .filter(Boolean).slice(0, 40)"""
        )
        print("URL", page.url, "file inputs (incl shadow)", count)
        print("labels", labels)
    browser.close()
