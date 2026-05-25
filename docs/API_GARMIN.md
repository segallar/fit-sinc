# Garmin Connect API (fit_sinc)

> **Неофициальный доступ** через библиотеку [`garth-ng`](https://pypi.org/project/garth-ng/) (`import garth`).  
> Официальный [Garmin Connect Developer Program](https://developer.garmin.com/gc-developer-program/overview/) **не подходит** для личной загрузки `.fit` — Activity API предназначен для pull данных с устройств партнёров, не для upload от имени пользователя.

**Риск:** Garmin может менять auth flow — следить за [garth-ng releases](https://pypi.org/project/garth-ng/).

---

## Что использует fit_sinc

| Операция | Метод garth-ng |
|----------|----------------|
| Login | `garth.login(email, password)` |
| Сохранение сессии | `garth.save(path)` |
| Восстановление сессии | `garth.resume(path)` |
| Upload FIT | Playwright browser (`/app/import-data`) → fallback HTTP → garth OAuth |
| Refresh token | автоматически в `Client.request()` |

Scope fit_sinc v1: **только upload активности**, без чтения wellness/stats.

---

## Аутентификация

### Login (интерактивно, один раз)

```python
import garth

garth.login("user@example.com", "password")
garth.save("data/garth")
```

**MFA:** если включена двухфакторная аутентификация, `garth.login()` запросит код (или используй `prompt_mfa` callback).

**Файл сессии:** `data/garth/oauth2_token.json`

```json
{
  "access_token": "...",
  "refresh_token": "...",
  "expires_in": 86400,
  "token_type": "Bearer",
  "expires_at": 1779809941.028
}
```

### Resume session

```python
import garth

garth.resume("data/garth")
# garth.client.oauth2_token — активен
```

fit_sinc: [`fit_sinc/garmin/session.py`](../fit_sinc/garmin/session.py)

### CLI fit_sinc

```bash
fit_sinc garmin login          # интерактивный login
fit_sinc garmin status         # проверка сессии
```

**Env (опционально):** `GARMIN_EMAIL`, `GARMIN_PASSWORD` — только для CLI login, не обязательны на сервере если session уже скопирован.

---

## Upload activity (FIT)

### Через garth-ng

```python
import garth
import io

garth.resume("data/garth")

with open("activity.fit", "rb") as f:
    result = garth.upload(f)

# result — dict от Garmin upload-service
```

### HTTP-уровень (внутри garth)

```
POST https://connectapi.garmin.com/upload-service/upload
Authorization: Bearer {oauth2_access_token}
Content-Type: multipart/form-data

file=@activity.fit
```

- User-Agent эмулирует мобильный клиент: `GCM-iOS-5.22.1.4`
- TLS fingerprint: `curl_cffi` с impersonate `chrome120`

**Важно:** передавать FIT **as-is** с Karoo — без модификации.

---

## Connect API (справочно, не используется в v1)

garth-ng умеет вызывать Connect API:

```python
garth.connectapi("/activitylist-service/activities/search/activities", method="GET")
garth.connectapi("/userprofile-service/socialProfile")
```

Base URL: `https://connectapi.garmin.com` (+ domain `.cn` для Китая через `garth.configure(domain="garmin.cn")`).

fit_sinc v1 **не читает** активности из Garmin — только upload.

---

## Обновление токена

`garth.client` автоматически обновляет OAuth2 token при 401 через `refresh_oauth2_token()`.  
Обновлённый token сохраняется если задан `GARTH_HOME` или после явного `garth.save()`.

На сервере fit_sinc загружает session read-only через `garth.resume()` — при Phase 2 добавить `garth.save()` после refresh.

---

## Переменные окружения garth-ng

| Variable | Описание |
|----------|----------|
| `GARTH_HOME` | Авто-resume session из каталога |
| `GARTH_TOKEN` | Base64-serialized token (альтернатива HOME) |

fit_sinc использует явный path: `DATA_DIR/garth/` через `garth.resume()`.

---

## Деплой session на сервер

Session привязана к аккаунту, не к машине — достаточно скопировать каталог:

```bash
scp -r data/garth root@sirocco.romansegalla.online:/opt/fit_sinc/data/
ssh root@sirocco.romansegalla.online \
  'chown -R fit_sinc:fit_sinc /opt/fit_sinc/data/garth'
```

При истечении refresh token — повторить `fit_sinc garmin login` локально и скопировать заново.

---

## Ограничения и риски

| Тема | Детали |
|------|--------|
| ToS | Неофициальный клиент; личное использование на свой риск |
| MFA | Поддерживается, но login только интерактивно |
| Дубликаты | Garmin может создать duplicate activity — dedup по Hammerhead `activityId` в SQLite (Phase 2) |
| Rate limits | Не документированы; при backfill — пауза между upload |
| Поломки | Следить за issues garth-ng при смене Garmin SSO |

**Upload (v0.3.1+):** programmatic HTTP upload blocked by Garmin. fit_sinc uses **headless Chromium (Playwright)**:

1. Cookies `JWT_WEB` + `session` from Chrome DevTools
2. Open `connect.garmin.com/app/import-data`
3. Accept consent → select `.fit` → click «Импорт данных»

На сервере нужен Chromium: `playwright install chromium` (уже выполнен на sirocco).

**Env для systemd:** `PLAYWRIGHT_BROWSERS_PATH`, `HOME` — см. [`deploy/fit-sinc.service`](../deploy/fit-sinc.service).

Web-сессия для upload:

JWT_WEB живёт ~24 ч; `session` cookie — дольше. fit_sinc **автоматически обновляет JWT**:
- фоновая задача в `serve` (каждые 30 мин, env `GARMIN_JWT_REFRESH_INTERVAL_SEC`)
- перед каждым upload
- вручную: `fit_sinc garmin refresh-web`

Обновление: HTTP через `session` cookie → fallback Playwright → fallback `web-login` (если нет MFA).

Если `session` истёк — снова импорт из Chrome DevTools:

```bash
fit_sinc garmin import-web-cookies '{"JWT_WEB":"eyJ...","session":"Fe26..."}'
fit_sinc garmin refresh-web --force
```

---

| Модуль | Назначение |
|--------|----------|
| [`fit_sinc/garmin/session.py`](../fit_sinc/garmin/session.py) | login, resume, status |
| Phase 2 | `garth.upload()` в sync service |

**Зависимость:** `garth-ng>=1.1.0` в [`pyproject.toml`](../pyproject.toml)
