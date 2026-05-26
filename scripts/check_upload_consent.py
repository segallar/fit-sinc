#!/usr/bin/env python3
import json
from pathlib import Path

import httpx

from getsync.garmin.web_session import web_resume

cookies = web_resume() or {}
client = httpx.Client(
    cookies=cookies,
    headers={
        "User-Agent": "Mozilla/5.0 Chrome/131",
        "Accept": "application/json",
        "NK": "NT",
        "Origin": "https://connect.garmin.com",
        "Referer": "https://connect.garmin.com/app/import-data",
    },
    timeout=30,
)
for url in [
    "https://connect.garmin.com/gc-api/gdprconsent-service/feature/UPLOAD",
    "https://connect.garmin.com/consentTextServices/consentText?consentTypeId=DI_CONNECT_UPLOAD&locale=ru-RU",
]:
    r = client.get(url)
    print("GET", url.split(".com")[1][:60])
    print(r.status_code, r.text[:500])
    print()

# try accept consent
r = client.post(
    "https://connect.garmin.com/gc-api/gdprconsent-service/consent/UPLOAD",
    json={"consentTypeId": "DI_CONNECT_UPLOAD", "accepted": True},
)
print("POST consent", r.status_code, r.text[:300])
