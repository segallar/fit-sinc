# Connections (источники и приёмники)

> **Создано:** 2026-05-26 · **Обновлено:** 2026-05-26 · **Версия:** 0.7.0  
> Статус: **модель зафиксирована** · в UI список растёт · в БД пока файлы + поля `users` (реестр — фаза **7.1** / **2.7**).

## Идея

У пользователя **много соединений**, не ровно два:

| Роль | Назначение | Примеры |
|------|------------|---------|
| **source** | Откуда читаем активности | Hammerhead, Strava, Wahoo, ручной upload |
| **sink** | Куда доставляем | Garmin Connect, S3, Hammerhead routes |

В каталоге `/app/activities` поле **`source`** совпадает с id источника (`hammerhead`, `garmin`, …).

Сейчас в production:

- **1 источник:** Hammerhead (OAuth + webhook)
- **1 приёмник:** Garmin Connect (web session / garth)
- **Garmin как source (metadata):** список активностей в browse — без локального FIT и wellness; полный pull — roadmap [**3.11**](3.11-GARMIN-PULL.md) · [PLAN.md](PLAN.md)

В Settings показываются **все слоты** (включая planned), чтобы UI не ломался при добавлении провайдера.

## UI — Settings `#connections`

```text
Connections
  Sources
    [Hammerhead]   Source   connected   Connect / Disconnect
    [Strava]       Source   planned     (soon)
    [Wahoo]        Source   planned
  Destinations
    [Garmin]       Destination   not ready   Refresh / Disconnect
  [ Add connection ]  (disabled until 7.1)
```

Компоненты:

- `list_connections()` — [`getsync/web/connections.py`](../getsync/web/connections.py)
- `components/connection_card.html`
- `components/connections/{id}_actions.html` — кнопки для реализованных типов

## Хранение credentials

**Целевая модель (auto-login, много систем):** [CREDENTIALS.md](CREDENTIALS.md) — шифрование per user, `connections/`, задачи **2.16** / **2.7**.

### Сейчас

Per user, **не** в SQLite (пароли Garmin **не** хранятся):

```text
data/users/{user_id}/
  hammerhead_tokens.json      # source: hammerhead
  garmin_web/                 # sink: garmin (web JWT)
  garth/                      # sink: garmin (OAuth fallback)
```

## Целевая модель (фаза 7)

```text
connections (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  provider TEXT NOT NULL,     -- hammerhead | garmin | strava | s3 | …
  role TEXT NOT NULL,           -- source | sink
  label TEXT,                 -- display name
  enabled INTEGER NOT NULL,
  config_json TEXT,             -- non-secret options
  credentials_ref TEXT,       -- path or vault key, not in DB body
  created_at, updated_at
)
```

Правила доставки (`rules`) ссылаются на `connection_id`, а не на захардкоженный `garmin`.

## Связь с activities

| Слой | Связь |
|------|--------|
| `activities.source` | id провайдера-источника |
| Sync HH→Garmin | правило по умолчанию: source=hammerhead → sink=garmin |
| Garmin pull (**3.11**) | source=garmin: FIT + `daily_steps` / `daily_sleep` |
| Будущее | N sources → M sinks по правилам пользователя |

См. [PLAN.md](PLAN.md) фазы **2.7**, **7**, [APP-UI.md](APP-UI.md) §6.3.
