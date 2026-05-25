# Hammerhead API (fit_sinc)

> **Официальный API** Hammerhead Karoo. OpenAPI: https://api.hammerhead.io/v1/docs/openapi.yml  
> Developer Portal: https://www.hammerhead.io/pages/developer-platform  
> Регистрация client: https://support.hammerhead.io/hc/en-us/articles/43558376710683-Creating-a-Developer-Account

fit_sinc использует scope **`activity:read`** — чтение активностей, скачивание FIT и webhook-уведомления.

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

**Redirect URI fit_sinc (локально):** `http://127.0.0.1:8765/callback`

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
| `activity:read` | Чтение активностей + webhook (используем) |
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

---

## Webhook (входящий в fit_sinc)

Hammerhead **POST** на URL из Developer Portal:

```
https://fit.romansegalla.online/webhooks/hammerhead
```

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

fit_sinc проверяет hex- и base64-представление digest. Без валидной подписи → **403**.

### Ответ fit_sinc

```json
{"status": "accepted"}
```

Hammerhead **игнорирует ошибки** webhook — idempotency на стороне fit_sinc обязательна (Phase 2).

---

## Developer Portal — что указать

| Поле | Значение fit_sinc |
|------|-------------------|
| Redirect URL | `http://127.0.0.1:8765/callback` |
| Webhook URL | `https://fit.romansegalla.online/webhooks/hammerhead` |
| Webhook secret | → `HAMMERHEAD_WEBHOOK_SECRET` в `.env` |

---

## Реализация в fit_sinc

| Модуль | Назначение |
|--------|------------|
| [`fit_sinc/hammerhead/oauth.py`](../fit_sinc/hammerhead/oauth.py) | OAuth, refresh, HMAC verify |
| [`fit_sinc/hammerhead/client.py`](../fit_sinc/hammerhead/client.py) | API client, download FIT |
| [`fit_sinc/cli.py`](../fit_sinc/cli.py) | `fit_sinc hammerhead auth|status` |

**Хранение tokens:** `data/hammerhead_tokens.json`

**CLI:**

```bash
fit_sinc hammerhead auth       # OAuth flow
fit_sinc hammerhead auth-url   # только URL
fit_sinc hammerhead status     # JSON статус
```
