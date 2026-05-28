# Activity Hub — product model

> **Создано:** 2026-05-28 · **Обновлено:** 2026-05-28 · **Версия:** 0.7.0  
> **Стратегия:** [VISION.md](VISION.md) · **Runtime:** [ARCHITECTURE.md](ARCHITECTURE.md) · **Domain:** [DOMAIN-MODEL.md](DOMAIN-MODEL.md) · **Modules:** [MODULES.md](MODULES.md)

Normative описание **activity hub** — центральной product model GetSync. Тактические задачи — [PLAN.md](PLAN.md).

---

## 1. Что такое activity hub

**GetSync** — personal **activity hub**: единый каталог тренировок tenant'а и слой доставки в внешние системы **по правилам**.

```text
  Sources (N)              GetSync Hub                    Sinks (M)
  ───────────              ─────────────                  ─────────
  Hammerhead    ──►       catalog (SQLite + FIT)    ──►   Garmin Connect
  Garmin pull   ──►       workspace (list/calendar) ──►   Strava
  Strava        ──►       rules (N → M)             ──►   S3 / archive
  manual FIT    ──►       delivery orchestrator     ──►   …
  Wahoo …       ──►
```

**Source of truth** — каталог GetSync (`catalog`), не Hammerhead, не Garmin, не Strava.

Внешние платформы — **providers**: adapters для **ingress** (данные в hub) и **egress** (доставка из hub).

---

## 2. Positioning

> GetSync — personal athlete data layer: собирает, нормализует и маршрутизирует спортивные данные между устройствами и облаками. Вы владеете копией истории; внешние платформы — providers/sinks, не canonical store.

GetSync — **не**:

- утилита «Karoo → Garmin» (это один bootstrap-сценарий, см. §6);
- social network или training planner;
- замена календарю одного провайдера.

GetSync — **да**:

- unified activity catalog per tenant;
- normalization layer (`NormalizedActivity`);
- delivery hub с declarative rules (**3.1**).

---

## 3. Три потока данных

### 3.1 Ingress (source → catalog)

| Trigger | Пример | Куда |
| ------- | ------ | ---- |
| Webhook (push) | Hammerhead `activityId` | ingest metadata + optional FIT |
| Pull on-demand | Refresh в UI, CLI backfill | `catalog.refresh_from_providers` |
| Pull scheduled | Фоновый job (**3.8**) | то же |
| Manual file | FIT/GPX upload (**2.9**) | `catalog` + `storage` |

После ingress UI читает **только catalog** ([`workspace`](../../getsync/workspace/) — list/calendar).

### 3.2 Egress (catalog → sink)

| Шаг | Модуль | Смысл |
| --- | ------ | ----- |
| Rule match | `rules` (**3.1**) | `when source=X then sink=Y` |
| Artifact fetch | `providers` source | FIT с диска или download |
| Deliver | `providers` sink | upload FIT / API push |
| State | `catalog` | delivery status per activity/sink |

Сегодня egress **зашит** как HH download → Garmin upload (`sync/service.py`) — transitional.

### 3.3 Presentation (catalog → user)

| Компонент | Роль |
| --------- | ---- |
| `workspace` | filters, pagination, calendar — read-only snapshot |
| `web` | delivery layer, Settings, Connections |

---

## 4. Модули hub

| Модуль | Hub role |
| ------ | -------- |
| **catalog** | Owner `activities` table + ingest; canonical metadata |
| **workspace** | Presentation; не знает providers |
| **providers** | Source/sink adapters; `registry.get_source` / `get_sink` |
| **sync** | Delivery orchestrator (переименование в `delivery` — опционально H2) |
| **rules** | N sources → M sinks (**3.9.5** infra, **3.1** product) |
| **storage** | FIT bytes; keys в catalog |
| **events** | In-process signals (**3.9.4**); не путать с SQLite audit |

См. [MODULES.md](MODULES.md) import matrix.

---

## 5. Providers: роли и механизмы

Один provider id может быть **source**, **sink** или оба (Garmin, Strava).

| Механизм | Направление | Примеры |
| -------- | ----------- | ------- |
| Webhook | ingress trigger | Hammerhead |
| Pull (REST/OAuth) | ingress | Strava, Garmin list, HH refresh |
| Push upload (API) | egress | Strava `/uploads`, Garmin web/garth |
| Browser fallback | egress / session | Garmin JWT refresh, upload |
| Manual file | ingress | FIT drag-and-drop (**2.9**) |

**Не activity-sink:** Hammerhead `route:write` — маршруты на Karoo, отдельный domain (routes), не FIT activities.

---

## 6. Bootstrap recipe (не product definition)

**Первый production-сценарий** (v0.6–v0.7), не архитектурный центр:

```text
Hammerhead webhook → download FIT → catalog → upload Garmin Connect
```

Implicit rule (до **3.1**):

```text
when: source=hammerhead AND event=activity.received
then: deliver to garmin
```

Этот сценарий остаётся supported и documented в [ARCHITECTURE.md](ARCHITECTURE.md#bootstrap-recipe-hammerhead--garmin) · [API_HAMMERHEAD.md](API_HAMMERHEAD.md). Новые интеграции добавляются **без смены hub-модели**.

---

## 7. Transitional vs target (код)

| Область | Сейчас (transitional) | Target (hub) |
| ------- | --------------------- | ------------ |
| Ingest | `registry` + `scan_source` (HH, Garmin) ✅ | + Strava OAuth (**3.9.3c**) |
| Delivery | `get_source` / `get_sink` (bootstrap HH→Garmin) ✅ | rule-driven `deliver(activity, sink)` |
| UI Sync button | HH-row → Garmin | Deliver по правилам |

Refactor без big-bang: **3.9** providers → **3.9.5** rules infra → **3.1** rules product.

---

## 8. Roadmap alignment

| Vision | PLAN | Содержание |
| ------ | ---- | ---------- |
| Hub catalog | **3.9.3** ✅ | `catalog` + `workspace` |
| Provider adapters | **3.9.3b** ✅ | HH, Garmin, Strava stub; **3.9.3c** → live OAuth |
| Rules infra | **3.9.5** | default rule → explicit |
| Multi-source UI | **3.5** | full hub (Strava, archive, …) |
| Garmin as source | **3.11** | pull FIT + wellness into catalog |

---

## 9. Связанные документы

| Документ | Тема |
| -------- | ---- |
| [VISION.md](VISION.md) | Product vision, горизонты |
| [DOMAIN-MODEL.md](DOMAIN-MODEL.md) | Activity, Connection, SyncRule |
| [CONNECTIONS.md](CONNECTIONS.md) | Sources / destinations в Settings |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Runtime, tenants, bootstrap recipe |
