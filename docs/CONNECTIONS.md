# Connections (источники и приёмники)

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

## Хранение credentials (сейчас)

Per user, **не** в SQLite:

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
| Будущее | N sources → M sinks по правилам пользователя |

См. [PLAN.md](PLAN.md) фазы **2.7**, **7**, [APP-UI.md](APP-UI.md) §6.3.
