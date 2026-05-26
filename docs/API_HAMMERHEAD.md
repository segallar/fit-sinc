# Hammerhead API (GetSync)

> **Официальный API** Hammerhead Karoo. OpenAPI: https://api.hammerhead.io/v1/docs/openapi.yml  
> Developer Portal: https://www.hammerhead.io/pages/developer-platform  
> Регистрация client: https://support.hammerhead.io/hc/en-us/articles/43558376710683-Creating-a-Developer-Account

GetSync использует scope **`activity:read`** — чтение активностей, скачивание FIT и webhook-уведомления.

---

## Базовые URL

| Сервис | Base URL |
|--------|----------|
| OAuth | `https://api.hammerhead.io/v1/auth` |
| REST API | `https://api.hammerhead.io/v1/api` |

---

## OAuth 2.0

### 1. Authorize (браузер пользователя)

```
GET https://api.hammerhead.io/v1/auth/oauth/authorize
  ?response_type=code
  &client_id={CLIENT_ID}
  &redirect_uri={REDIRECT_URI}
  &scope=activity:read
  &state={RANDOM_STATE}
```

**Redirect URI (CLI, локально):** `http://127.0.0.1:8765/callback`  
**Redirect URI (кабинет, production):** `https://app.getsync.me/app/settings/hammerhead/callback`  
(задаётся `HAMMERHEAD_WEB_REDIRECT_URI` или совпадает с путём в [`settings_routes.py`](../getsync/web/settings_routes.py))

**Успех:** `{redirect_uri}?code={code}&state={state}`  
**Отказ:** `{redirect_uri}?error=access_denied&state={state}`

### 2. Token exchange

```
POST https://api.hammerhead.io/v1/auth/oauth/token
Content-Type: application/x-www-form-urlencoded

client_id=...
client_secret=...
grant_type=authorization_code
code=...
redirect_uri=...   # must match authorize request
```

**Ответ 200:**

```json
{
  "token_type": "Bearer",
  "access_token": "...",
  "refresh_token": "...",
  "expires_in": 52000,
  "user_id": "192184"
}
```

Поле `user_id` сохраняется в `users.hammerhead_user_id` для маршрутизации webhook.

### 3. Refresh token

```
POST https://api.hammerhead.io/v1/auth/oauth/token
Content-Type: application/x-www-form-urlencoded

client_id=...
client_secret=...
grant_type=refresh_token
refresh_token=...
```

### 4. Deauthorize

```
POST https://api.hammerhead.io/v1/auth/oauth/deauthorize

client_id=...
client_secret=...
token={access_token}
```

### Scopes

| Scope | Описание |
|-------|----------|
| `activity:read` | Чтение активностей + webhook (**используем**) |
| `route:read` | Чтение маршрутов |
| `route:write` | Загрузка маршрутов |
| `workout:write` | Загрузка workouts |

---

## Activities API

Все запросы с заголовком:

```
Authorization: Bearer {access_token}
```

### Список активностей

```
GET /activities?page=1&perPage=10&startDate=2025-01-01
```

| Параметр | Тип | Описание |
|----------|-----|----------|
| `page` | int | Страница (default 1) |
| `perPage` | int | 1–100 (default 10) |
| `startDate` | date | Фильтр `YYYY-MM-DD` |

**Ответ 200:**

```json
{
  "totalItems": 34,
  "totalPages": 4,
  "perPage": 10,
  "currentPage": 1,
  "data": [
    {
      "id": "192184.activity.06112a72-5f09-401f-a9a0-ef38d64e10e3",
      "name": "Morning Ride",
      "createdAt": "2026-05-24T08:17:22.485Z",
      "duration": 76765,
      "distance": 123.45
    }
  ]
}
```

### Детали активности

```
GET /activities/{activityId}
```

Дополнительные поля: `activityType` (RIDE, GRAVEL, …), `description`, `polyline`, `updatedAt`.

### Скачивание FIT

```
GET /activities/{activityId}/file
```

**Ответ 200:** бинарный FIT (`application/vnd.ant.fit`).

При 404/409/425 GetSync повторяет запрос с задержками 5 / 15 / 30 с ([`sync/service.py`](../getsync/sync/service.py)).

---

## Webhook (входящий в GetSync)

Hammerhead **POST** на URL из Developer Portal:

```
https://app.getsync.me/webhooks/hammerhead
```

(legacy до cutover: `https://fit.romansegalla.online/webhooks/hammerhead`)

### Тело запроса

```json
{
  "activityId": "192184.activity.06112a72-5f09-401f-a9a0-ef38d64e10e3",
  "userId": "192184"
}
```

### Подпись

| Header | Значение |
|--------|----------|
| `X-Hmac-Signature` | HMAC-SHA256(raw body, webhook_secret) |

GetSync проверяет hex- и base64-представление digest ([`oauth.py`](../getsync/hammerhead/oauth.py)). Без валидной подписи → **403**.

### Ответ GetSync

```json
{"status": "accepted"}
```

Синхронизация выполняется в `BackgroundTasks` после ответа.

Hammerhead **не гарантирует** доставку — idempotency на стороне GetSync (`activities` + `is_synced`).

### Маршрутизация tenant

`payload.userId` → `Store.get_user_by_hammerhead_id()` → `user_id`.  
Если не найден — tenant `default` ([`resolve_user_for_webhook`](../getsync/sync/service.py)).

---

## Developer Portal — что указать

| Поле | Production (целевое) |
|------|----------------------|
| Redirect URL (CLI) | `http://127.0.0.1:8765/callback` |
| Redirect URL (UI) | `https://app.getsync.me/app/settings/hammerhead/callback` |
| Webhook URL | `https://app.getsync.me/webhooks/hammerhead` |
| Webhook secret | → `HAMMERHEAD_WEBHOOK_SECRET` в `.env` |

---

## Реализация в коде

| Модуль | Назначение |
|--------|------------|
| [`getsync/hammerhead/oauth.py`](../getsync/hammerhead/oauth.py) | OAuth, refresh, HMAC verify |
| [`getsync/hammerhead/client.py`](../getsync/hammerhead/client.py) | API client, download FIT |
| [`getsync/cli.py`](../getsync/cli.py) | `getsync hammerhead auth\|status` |
| [`getsync/web/settings_routes.py`](../getsync/web/settings_routes.py) | OAuth из кабинета |

**Хранение tokens (per tenant):** `data/users/{user_id}/hammerhead_tokens.json`

**CLI:**

```bash
getsync hammerhead auth       # OAuth flow (CLI redirect)
getsync hammerhead auth-url   # только URL
getsync hammerhead status     # JSON статус
getsync --user <slug> hammerhead auth
```

См. также [ARCHITECTURE.md](ARCHITECTURE.md), [CI-CD.md](CI-CD.md) (webhook smoke).
