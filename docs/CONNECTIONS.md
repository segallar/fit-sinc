# Connections (источники и приёмники)

> **Создано:** 2026-05-26 · **Обновлено:** 2026-05-28 · **Версия:** 0.7.0  
> **Product model:** [ACTIVITY-HUB.md](ACTIVITY-HUB.md) · Статус: **модель зафиксирована** · реестр connections — **2.7**

## Идея

GetSync — **activity hub**: у пользователя **много connections** (sources и sinks), не одна пара экосистем.

| Роль | Назначение | Примеры |
|------|------------|---------|
| **source** | Ingress → catalog | Hammerhead, Garmin pull, Strava, Wahoo, manual FIT |
| **sink** | Egress из catalog/FIT | Garmin Connect, Strava, S3, archive |

В каталоге `/app/activities` поле **`source`** = id провайдера-источника в hub (`hammerhead`, `garmin`, `strava`, …).

### Bootstrap vs hub (production v0.7)

| | Роль в hub |
|---|------------|
| **Hammerhead** | source (webhook + refresh) |
| **Garmin Connect** | sink (upload) + source metadata (refresh); full pull — **3.11** |
| **Strava** | source + sink — **3.9.3c** ([API_STRAVA.md](API_STRAVA.md)) |
| **Implicit rule** | `hammerhead → garmin` до **3.1** — см. [ACTIVITY-HUB.md](ACTIVITY-HUB.md) |

В Settings показываются **все слоты** (включая planned), чтобы UI не ломался при добавлении провайдера.

## UI — Settings `#connections`

```text
Connections
  Sources
    [Hammerhead]   Source   connected   Connect / Disconnect
    [Strava]       Source + Destination   connected / not connected   Connect / Disconnect
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
| Sync HH→Garmin | **bootstrap implicit rule** (до **3.1**); target: arbitrary N→M |
| Garmin pull (**3.11**) | Garmin как **source** в hub: FIT + wellness |
| Strava (**3.9.3c**) | source + sink — [API_STRAVA.md](API_STRAVA.md) |
| Будущее | N sources → M sinks по правилам пользователя |

См. [PLAN.md](PLAN.md) фазы **2.7**, **7**, [APP-UI.md](APP-UI.md) §6.3.
