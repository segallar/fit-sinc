# Domain Model (v0)

> **Создано:** 2026-05-27 · **Обновлено:** 2026-05-27 · **Версия:** 0.7.0 · **2.17** UUID tenant id — [PLAN.md](PLAN.md#217--tenant-id-uuid)  
> **Стратегия:** [VISION.md](VISION.md) · **Tactical:** [PLAN.md](PLAN.md) · **SQLite сегодня:** [DATABASE.md](DATABASE.md) · **FIT:** [STORAGE.md](STORAGE.md)

Черновик **canonical domain model** для GetSync. Описывает целевые сущности и mapping на текущую реализацию. Не дублирует полную SQL-схему — см. [DATABASE.md](DATABASE.md).

---

## Принципы v0

| Принцип | Реализация |
| ------- | ---------- |
| **Canonical ID** | `(user_id, source, activity_id)` для activities |
| **Raw + normalized** | FIT/raw на диске (`storage_key`); метаданные в SQLite |
| **Source of truth** | GetSync; провайдеры — ingest/export |
| **Per-tenant** | Все сущности scoped by `user_id` |
| **Evolution** | Новые поля/таблицы без big-bang; миграции в `Store` |

---

## Сущности

### Athlete / User

Учётная запись tenant. Таблица `users`.

| Поле (concept) | Сейчас | Примечание |
| -------------- | ------ | ---------- |
| id | `users.id` | PK; сейчас часто = `slug` (`default`); **roadmap:** UUID (**2.17**) |
| slug | `users.slug` | UNIQUE, human-readable; не меняется после создания |
| email, profile | ✅ | |
| timezone, locale | ✅ | |
| hammerhead_user_id | ✅ | webhook routing |
| is_admin, disabled | ✅ | |

**Roadmap:** `email_verified` — **2.1e** / **2.6**.

---

### Activity

Нормализованная тренировка из любого source.

| Поле (concept) | Сейчас | Примечание |
| -------------- | ------ | ---------- |
| user_id | ✅ | |
| source | ✅ | `hammerhead`, `garmin`, … |
| activity_id | ✅ | id у провайдера |
| sync_status | ✅ | pipeline HH→Garmin |
| storage_key | ✅ | путь FIT в [STORAGE.md](STORAGE.md) |
| activity_type, timestamps | ✅ | browse/calendar |
| garmin_result | ✅ | upload outcome |

**Artifact:** `{storage_key}` → `.fit` under `data/users/{id}/activities/{source}/`.

**Roadmap:** `raw_payload_ref`, conflict flags — H2; duplicate detection rules — **3.1**.

---

### Connection (Source Integration)

Привязка tenant к провайдеру (source или sink).

| Поле (concept) | Сейчас | Примечание |
| -------------- | ------ | ---------- |
| user_id + provider + role | файлы + UI registry | [CONNECTIONS.md](CONNECTIONS.md) |
| enabled, config | partial | |
| credentials | **2.16** ✅ encrypted | `connections/garmin/` |

**Roadmap:** таблица `connections` — **2.7**; Hammerhead в vault — **2.7.1**.

---

### Sync Event

Запись журнала pipeline (webhook, download, upload, error).

| Поле | Сейчас |
| ---- | ------ |
| user_id, activity_id, event_type, message, created_at | `sync_events` ✅ |

Admin UI: `/app/admin/sync-log`.

---

### Session Refresh Event

Журнал обновления Garmin JWT.

| Поле | Сейчас |
| ---- | ------ |
| user_id, trigger, event_type, … | `session_refresh_events` ✅ |

Admin UI: `/app/admin/log`.

---

### Sync Rule

Правило маршрутизации: source → sink(s) с фильтрами.

| Статус | Сейчас |
| ------ | ------ |
| Implicit | `hammerhead` → `garmin` (hardcoded) |

**Roadmap:** таблица + UI — **3.1** (после **2.7** и второго source / manual upload **2.9**).

Пример (target):

```text
rule: default_cycling
  when: source=hammerhead AND activity_type=cycling
  then: sink=garmin
```

---

### Wellness Event / WellnessDay

Дневные метрики: steps, sleep, body.

| Статус | Сейчас |
| ------ | ------ |
| 📋 | — |

**Roadmap:** `daily_steps`, `daily_sleep` — **3.11.3**; UI widget — **3.11.4**.

---

### Route / Planned Workout / Device

| Сущность | H1 | H2+ |
| -------- | -- | --- |
| **Route** | — | courses **3.2**, Komoot integration |
| **Planned Workout** | — | workspace H2 |
| **Device** | — | optional metadata H3 |

Не моделировать в v0 — только зафиксировать как future entities в [VISION.md](VISION.md).

---

## Диаграмма (v0)

```mermaid
erDiagram
    User ||--o{ Activity : owns
    User ||--o{ Connection : has
    User ||--o{ SyncEvent : generates
    User ||--o{ SyncRule : defines
    Activity }o--|| Connection : "source"
    SyncRule }o--o{ Connection : "source and sinks"

    User {
        text id PK
        text email
    }
    Activity {
        text user_id PK
        text source PK
        text activity_id PK
        text storage_key
    }
    Connection {
        text provider
        text role
    }
    SyncRule {
        text id PK
        json filter
    }
```

`Connection` и `SyncRule` — **design**; в SQLite появятся в **2.7** / **3.1**.

---

## Horizons: что вводить когда

| Entity | H1 (сейчас) | H2 | H3 |
| ------ | ----------- | -- | -- |
| Activity (extend) | ✅ + refine | conflict, raw ref | |
| Connection | **2.7** | multi-provider | |
| SyncRule | design | **3.1** impl | |
| WellnessDay | **3.11.3** | | |
| Route, PlannedWorkout | — | spike | |
| Device | — | — | optional |

---

## Следующие шаги (H1)

1. Review этого документа vs код — без немедленных миграций
2. **2.7** — `connections` table + migrate file-based HH/Garmin refs
3. **3.11.1** spike — влияет на Activity + storage для `source=garmin`
4. Contract sketch для provider adapter (**3.9.2**) — отдельный файл или секция в MODULES (после **3.9.0**)

См. [PLAN.md](PLAN.md) · [VISION.md §11](VISION.md#11-план-по-трём-горизонтам).
