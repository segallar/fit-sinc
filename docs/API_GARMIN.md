# Garmin Connect API (GetSync)

> **Неофициальный доступ** через [`garth-ng`](https://pypi.org/project/garth-ng/) (`import garth`).  
> Официальный [Garmin Connect Developer Program](https://developer.garmin.com/gc-developer-program/overview/) **не подходит** для личной загрузки `.fit` — Activity API для pull с устройств партнёров, не upload от имени пользователя.

**Риск:** Garmin может менять auth flow — следить за [garth-ng releases](https://pypi.org/project/garth-ng/).

---

## Что использует GetSync (v1)

| Операция | Реализация |
|----------|------------|
| Login (CLI) | `garth.login` + `garth.save` → `data/users/{id}/garth/` |
| Web-сессия upload | `JWT_WEB` + `session` в `data/users/{id}/garmin_web/session.json` |
| Upload FIT | Playwright `/app/import-data` → HTTP → `garth.upload()` |
| Refresh JWT | HTTP → Playwright → re-login ([`web_refresh.py`](../getsync/garmin/web_refresh.py)) |

Scope v1: **только upload активности**, без чтения wellness/stats.

**Per tenant:** у каждого `user_id` свой `garmin_web/` и `garth/`. Общей сессии на сервер нет ([ARCHITECTURE.md](ARCHITECTURE.md)).

---

## Аутентификация (garth-ng / OAuth)

### Login (интерактивно, CLI)

```python
import garth

garth.login("user@example.com", "password")
garth.save("data/users/default/garth")
```

**MFA:** `garth.login()` запросит код при включённой 2FA.

**Файл сессии:** `data/users/{user_id}/garth/oauth2_token.json`

### Resume session

```python
garth.resume("data/users/default/garth")
```

Код: [`getsync/garmin/session.py`](../getsync/garmin/session.py)

### CLI

```bash
getsync --user <slug> garmin login
getsync --user <slug> garmin status      # upload_ready = web JWT valid
getsync --user <slug> garmin refresh-web
getsync --user <slug> garmin import-web-cookies '{"JWT_WEB":"...","session":"..."}'
```

`GARMIN_EMAIL` / `GARMIN_PASSWORD` в `.env` — только fallback при пустой web-сессии; для нескольких Garmin-аккаунтов **не задавать**.

---

## Web-сессия (основной upload)

Garmin блокирует простой programmatic HTTP upload; GetSync использует cookies из браузерной сессии Connect.

| Cookie | Назначение |
|--------|------------|
| `JWT_WEB` | Bearer для upload API (~24 ч) |
| `session` | Долгоживущая Fe26-session для refresh JWT |

Файл: `data/users/{user_id}/garmin_web/session.json`

**Обновление JWT:**

- фоновый цикл в `getsync serve` (`GARMIN_JWT_REFRESH_INTERVAL_SEC`, default 1800)  
- перед каждым upload (`ensure_web_session`)  
- вручную: `getsync garmin refresh-web` или кнопка в `/app/settings`  

Цепочка: HTTP через `session` → headless Chromium → `web_login` при необходимости.

**Импорт из Chrome DevTools** (если `session` истёк):

```bash
getsync --user <slug> garmin import-web-cookies '{"JWT_WEB":"eyJ...","session":"Fe26..."}'
getsync --user <slug> garmin refresh-web --force
```

---

## Upload activity (FIT)

### Порядок в коде ([`session.py`](../getsync/garmin/session.py))

1. `upload_fit_via_browser` — Playwright, страница import-data  
2. `upload_fit_via_web` — HTTP multipart с `JWT_WEB`  
3. `garth.upload()` — OAuth fallback  

FIT передаётся **без модификации** (байты с Hammerhead).

### HTTP (внутри garth, fallback)

```
POST https://connectapi.garmin.com/upload-service/upload
Authorization: Bearer {oauth2_access_token}
Content-Type: multipart/form-data
```

User-Agent эмулирует мобильный клиент; TLS — `curl_cffi` (impersonate `chrome120`).

---

## Connect API (справочно)

garth-ng умеет `garth.connectapi(...)` для списка активностей и профиля.  
GetSync v1 **не читает** активности из Garmin — только upload. Список в UI строится из Hammerhead + локального SQLite.

---

## OAuth token refresh (garth)

`garth.client` обновляет OAuth2 при 401. На сервере обычно `garth.resume()` без записи; при длительной эксплуатации может понадобиться периодический `garth.save()` после refresh.

---

## Переменные окружения garth-ng

| Variable | Описание |
|----------|----------|
| `GARTH_HOME` | Авто-resume из каталога |
| `GARTH_TOKEN` | Base64 token (альтернатива) |

GetSync задаёт явный path: `UserContext.garth_dir`.

---

## Деплой session на сервер

Сессия привязана к аккаунту — копируется каталог tenant:

```bash
# после локального getsync --user default garmin login
scp -r data/users/default/garth \
  root@sirocco:/opt/getsync/data/users/default/
scp data/users/default/garmin_web/session.json \
  root@sirocco:/opt/getsync/data/users/default/garmin_web/

ssh root@sirocco 'chown -R getsync:getsync /opt/getsync/data'
```

При истечении refresh token — повторить login локально и скопировать снова.

---

## Playwright на сервере

Upload через headless Chromium (`/app/import-data`, consent, file input).

- Установка: `playwright install chromium` (в venv пользователя `getsync`)  
- systemd: `PLAYWRIGHT_BROWSERS_PATH`, `HOME` — [`deploy/getsync.service`](../deploy/getsync.service)

---

## Ограничения и риски

| Тема | Детали |
|------|--------|
| ToS | Неофициальный клиент; личное использование на свой риск |
| MFA | Login интерактивно или cookies из браузера |
| Дубликаты | Дедуп по Hammerhead `activity_id` в SQLite |
| Rate limits | Не документированы; при backfill — умеренная нагрузка |
| Поломки | Следить за issues garth-ng при смене Garmin SSO |

---

## Модули

| Модуль | Назначение |
|--------|------------|
| [`getsync/garmin/session.py`](../getsync/garmin/session.py) | login, status, `upload_fit` orchestration |
| [`getsync/garmin/web_session.py`](../getsync/garmin/web_session.py) | cookies, HTTP upload |
| [`getsync/garmin/web_refresh.py`](../getsync/garmin/web_refresh.py) | JWT refresh |
| [`getsync/garmin/browser_upload.py`](../getsync/garmin/browser_upload.py) | Playwright |

**Зависимость:** `garth-ng>=1.1.0` в [`pyproject.toml`](../pyproject.toml)
