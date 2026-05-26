#!/usr/bin/env python3
import base64
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

from getsync.garmin.browser_upload import CHROMIUM_ARGS, USER_AGENT, _cookies_for_playwright

JS = """
async ({ b64, filename }) => {
  const csrf = document.querySelector('meta[name="csrf-token"]')?.content;
  const bytes = Uint8Array.from(atob(b64), (c) => c.charCodeAt(0));
  const form = new FormData();
  form.append("file", new File([bytes], filename, { type: "application/octet-stream" }));
  const headers = {
    NK: "NT",
    Accept: "application/json, text/plain, */*",
    "DI-Backend": "connectapi.garmin.com",
  };
  if (csrf) headers["connect-csrf-token"] = csrf;
  const urls = [
    "/modern/proxy/upload-service/upload/.fit",
    "/modern/upload-service/upload/.fit",
  ];
  const out = [];
  for (const url of urls) {
    try {
      const resp = await fetch(url, {
        method: "POST",
        body: form,
        credentials: "include",
        headers,
      });
      out.push({
        url,
        status: resp.status,
        ct: resp.headers.get("content-type"),
        body: (await resp.text()).slice(0, 200),
      });
    } catch (e) {
      out.push({ url, error: String(e) });
    }
  }
  return out;
}
"""

sess = json.loads(Path("data/garmin_web/session.json").read_text())
fit = next(Path("data/fits").glob("*.fit"))
b64 = base64.b64encode(fit.read_bytes()).decode()

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True, args=list(CHROMIUM_ARGS))
    context = browser.new_context(user_agent=USER_AGENT, locale="ru-RU")
    context.add_cookies(_cookies_for_playwright(sess["cookies"]))
    page = context.new_page()
    page.goto("https://connect.garmin.com/modern/", wait_until="domcontentloaded")
    page.wait_for_timeout(2000)
    print(json.dumps(page.evaluate(JS, {"b64": b64, "filename": fit.name}), indent=2))
    browser.close()
