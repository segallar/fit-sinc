#!/usr/bin/env python3
import httpx
import re

index = httpx.get(
    "https://connect.garmin.com/web-react/static/js/index__bundle__5.25.0.30.js",
    timeout=60,
).text
scripts = set(re.findall(r"/web-react/static/js/[^\"']+", index))
print("scripts", len(scripts))
for path in sorted(scripts):
    url = "https://connect.garmin.com" + path
    try:
        text = httpx.get(url, timeout=60).text
    except Exception as exc:
        print("fail", path, exc)
        continue
    for needle in ("detailedImportResult", "upload-service", "import-data", "ImportData"):
        if needle in text:
            print("HIT", needle, path)
            for m in re.findall(r".{0,40}upload.{0,60}", text, flags=re.I)[:5]:
                print(" ", m[:100])
