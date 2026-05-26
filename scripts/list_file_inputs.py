#!/usr/bin/env python3
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

from getsync.garmin.browser_upload import (
    CHROMIUM_ARGS,
    IMPORT_URL,
    USER_AGENT,
    _cookies_for_playwright,
)

JS = """
() => {
  const out = [];
  const walk = (root, depth) => {
    root.querySelectorAll('input[type="file"]').forEach((el) => {
      out.push({
        accept: el.accept,
        id: el.id,
        name: el.name,
        hidden: el.hidden,
        display: getComputedStyle(el).display,
        parentText: (el.closest('section,div,form')?.innerText || '').slice(0, 120),
      });
    });
    root.querySelectorAll('*').forEach((el) => {
      if (el.shadowRoot) walk(el.shadowRoot, depth + 1);
    });
  };
  walk(document, 0);
  return out;
}
"""

sess = json.loads(Path("data/garmin_web/session.json").read_text())
with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True, args=list(CHROMIUM_ARGS))
    context = browser.new_context(user_agent=USER_AGENT, locale="ru-RU")
    context.add_cookies(_cookies_for_playwright(sess["cookies"]))
    page = context.new_page()
    page.goto(IMPORT_URL, wait_until="domcontentloaded")
    page.wait_for_timeout(10000)
    print(json.dumps(page.evaluate(JS), indent=2, ensure_ascii=False))
    browser.close()
