# Product Vision и стратегия GetSync

> **Создано:** 2026-05-27 · **Обновлено:** 2026-05-28 · **Версия:** 0.7.0  
> **Product model:** [ACTIVITY-HUB.md](ACTIVITY-HUB.md) · **Tactical:** [PLAN.md](PLAN.md) · **Domain v0:** [DOMAIN-MODEL.md](DOMAIN-MODEL.md) · **Runtime:** [ARCHITECTURE.md](ARCHITECTURE.md)

Стратегический документ: *куда* и *зачем* развивается GetSync. Конкретные задачи, оценки и статусы — только в [PLAN.md](PLAN.md).

---

## 1. Что такое GetSync

GetSync — **personal activity hub**: единый каталог тренировок и слой доставки в любые подключённые системы по правилам пользователя.

Платформа для хранения, нормализации, синхронизации и анализа спортивных данных — с **GetSync как source of truth**, а не с одной парой экосистем.

**Проблема, с которой начался проект:**

- тренировки распределены между устройствами и облаками;
- экосистемы плохо синхронизируются;
- дубли, потери, lock-in;
- пользователь не владеет полной историей.

**Product model (normative):** [ACTIVITY-HUB.md](ACTIVITY-HUB.md)

```text
Sources (N)  →  catalog + storage  →  Sinks (M)
                 workspace (UI)
                 rules (N → M)
```

**Positioning (одна строка):**

> GetSync — personal athlete data layer: собирает, нормализует и маршрутизирует спортивные данные между устройствами и облаками. Вы владеете копией истории; внешние платформы — providers/sinks, не canonical store.

**Bootstrap-сценарий в production (v0.7):** Hammerhead Karoo → GetSync catalog → Garmin Connect — один implicit rule, не определение продукта. См. [ACTIVITY-HUB.md §6](ACTIVITY-HUB.md#6-bootstrap-recipe-не-product-definition).

---

## 2. Основная проблема рынка

Современный спортсмен использует велокомпьютеры, часы, весы, recovery devices, route planners, training calendars, social platforms — Garmin, Hammerhead, Whoop, Withings, Strava, Komoot, Final Surge, TrainingPeaks и др.

Каждая система:

- хранит только часть данных;
- имеет собственную модель;
- плохо взаимодействует с другими;
- ограничивает экспорт;
- создаёт ecosystem lock-in.

**Главная идея GetSync:**

> История спортсмена не должна зависеть от конкретного устройства, платформы или экосистемы.

---

## 3. Product Vision

### Кратко

GetSync — это:

- **activity hub** — unified catalog + delivery по правилам;
- слой нормализации (`NormalizedActivity`);
- orchestration platform (ingress / egress);
- open ecosystem для интеграций и аналитики (долгосрочно).

### Долгосрочная цель

- unified athlete history в одном hub;
- centralized sports data layer (canonical store у пользователя);
- open platform для AI и внешних приложений.

### Что важно

GetSync — **не** upload utility «из A в B», не календарь одного провайдера и не social network. Это инфраструктурная платформа поверх fragmented sports ecosystem. Сценарий Karoo→Garmin — **первый рецепт**, не границы продукта.

---

## 4. Основные принципы

### 4.1 Platform-first

Главная ценность — в данных, синхронизации, нормализации и orchestration, а не в «красивом UI ради роста».

**Уточнение для v0.7:** UI в краткосрочном горизонте — **operational interface** (activities, settings, connections, sync logs), без feature expansion. Задачи **2.10** / **2.12** в [PLAN.md](PLAN.md) — не detour, а минимум для ops без CLI.

### 4.2 Web-first

Web — основной интерфейс; backend — центр системы. Mobile позже: companion / viewer / notifications.

### 4.3 Modular-first architecture

Независимые модули: отдельная разработка, тесты, минимум зависимостей. См. **3.9** в PLAN.

### 4.4 Integrations are plugins

Garmin, Hammerhead, Strava, Withings — provider modules. Core domain не зависит от конкретного провайдера. См. [CONNECTIONS.md](CONNECTIONS.md), [CREDENTIALS.md](CREDENTIALS.md).

### 4.5 Source of truth

GetSync — canonical storage layer. Внешние платформы — providers/sinks.

---

## 5. Основные области продукта

| Область | Содержание | PLAN / docs |
| ------- | ---------- | ----------- |
| **Activity Hub** | Catalog, ingress/egress, source of truth | [ACTIVITY-HUB.md](ACTIVITY-HUB.md), **3.9.3** ✅ |
| **Data Model** | Activity, Connection, SyncRule, Wellness, … | [DOMAIN-MODEL.md](DOMAIN-MODEL.md), [DATABASE.md](DATABASE.md) |
| **Athlete Workspace** | Календарь, activities, filters, delivery status | `workspace/`, **2.3** ✅, **2.10** |
| **Delivery Engine** | rules, retries, dedup, provider adapters | `sync/`, `providers/`, **3.9.3b**, **3.1** |
| **Rule Engine** | routing, filters, priorities | **3.1**, **3.9.5** |
| **Visualization** | maps, charts, compare | **3.10** |
| **Open API** | public API, OAuth apps | **3.12** |
| **Social & Clubs** | sharing, clubs (не core) | **4.2** |

Детали data model — §5.1 в [DOMAIN-MODEL.md](DOMAIN-MODEL.md).

---

## 6. Рыночные наблюдения

| Сегмент | Сильные стороны | Слабость для GetSync |
| ------- | --------------- | -------------------- |
| Device ecosystems (Garmin, HH, Wahoo) | Свои устройства | Плохой cross-platform data layer |
| Training (TP, Final Surge, intervals.icu) | Планирование | Fragmented data ownership |
| Routes (Komoot) | Route UX | Слабая athlete data model |
| Social (Strava) | Community | Ограниченный utility и export |

**Вывод:** рынок fragmented; нет unified athlete platform + open sync infrastructure — white space для GetSync.

---

## 7. Open Source и коммерция

**Сейчас:** не усложнять licensing; сохранить ownership; проектировать modular architecture.

**Потенциально:** open-source core + commercial hosted platform (SaaS, premium analytics, AI, clubs).

**Осторожно:** adapters с grey-area API (Garmin web, Hammerhead) — возможно closed/plugins с disclaimer, не «open everything day one».

---

## 8. Архитектурные требования

- **Modularity** — replaceable, testable subsystems
- **Boundaries** — Domain · Integrations · Sync · Storage · API · Visualization
- **Event-driven** (перспектива) — sync events, queues, workers (**3.8**)
- **Storage abstraction** — local ✅, S3 (**3.3**)
- **Tenant isolation** — per-user storage, credentials, rules ✅

---

## 9. Что уже реализовано

См. также [PLAN.md § Что реализовано](PLAN.md#что-реализовано-сейчас-код--prod).

- production deployment (`app.getsync.me`);
- **activity hub core:** `catalog` + `workspace` (**3.9.3** ✅);
- provider integrations: Hammerhead (source), Garmin (sink + catalog ingest);
- bootstrap delivery: HH webhook → FIT → Garmin;
- admin tools, sync logs;
- multi-user architecture, tenant isolation;
- encrypted credentials (**2.16**);
- `StorageBackend` local;
- mail infra (`getsync/mail`, Resend).

**Стадия:** working infrastructure platform, не prototype.

---

## 10. Текущие приоритеты (согласовано с PLAN)

| Приоритет | Фокус | PLAN |
| --------- | ----- | ---- |
| P0 | Ops UI: sidebar, Garmin login в Settings | **2.10**, **2.12**, **2.13** |
| **P0 platform** | Modularity: rules, contracts, boundaries | **3.9.*** — [MODULES.md](MODULES.md) |
| P1 | Domain foundation + второй source | **3.11.1–3.11.2** (после **3.9.3**) |
| P1 | Trust для публичного register | **2.6** / **2.1e** |
| P2 | Rule engine product (UI, БД) | **3.1** (после **2.7** + multi-source) |
| Не сейчас | Social, mobile app, AI, public API GA | **3.12**, **4.x** |

---

## 11. План по трём горизонтам

### Горизонт 1 — Сейчас

**Цель:** hub foundation + modularity.

- Зафиксировать [ACTIVITY-HUB.md](ACTIVITY-HUB.md), [DOMAIN-MODEL.md](DOMAIN-MODEL.md), [MODULES.md](MODULES.md)
- **catalog + workspace** ✅; provider registry + adapters (**3.9.3b**, Strava reference)
- Reliability delivery, dedup, tenant isolation
- UI — minimum ops surface (**2.10**, **2.12**)
- Garmin pull (**3.11**) — Garmin как **source** в hub

### Горизонт 2 — Следующая версия продукта

**Цель:** full activity hub — multi-source, multi-sink.

- Unified workspace: calendar, activity viewer, routes
- Rule engine product (**3.1**), Strava и др. по priority matrix
- Wellness (**3.11.3–3.11.4**), visualization (**3.10**)
- API foundation (**3.12**), постепенный open-source core

### Горизонт 3 — Далекая перспектива

**Цель:** open athlete data platform.

- Open Athlete Graph (normalized history)
- AI & analysis layer (**4.1**)
- Developer ecosystem, marketplace
- Clubs & teams (**4.2**)
- Hosted commercial platform

---

## 12. Non-goals (12 месяцев)

- Native mobile app
- Strava-level social network
- Integrations marketplace «все провайдеры сразу»
- AI assistant как headline feature до stable data layer
- Docker/K8s migration ради миграции (ops по необходимости)

---

## 13. Mapping vision → PLAN

| Vision | PLAN ID | Горизонт |
| ------ | ------- | -------- |
| **Activity hub model** | [ACTIVITY-HUB.md](ACTIVITY-HUB.md) | H1 |
| Domain model v0 | [DOMAIN-MODEL.md](DOMAIN-MODEL.md) | H1 |
| Catalog + workspace | **3.9.3** ✅ | H1 |
| Provider adapters (HH, Garmin, Strava) | **3.9.3b** | H1 |
| Connections в БД | **2.7** | H1 |
| Garmin login UI | **2.12** | H1 / v0.7 |
| Modularity | **3.9.*** — [MODULES.md](MODULES.md) | H1 |
| Source/Sink contracts | **3.9.2** (closes **2.8**) | H1 |
| Garmin as hub source | **3.11.*** | H1 |
| Rule engine product | **3.1** | H2 |
| Full hub (N→M) | **3.5** | H2 |
| Public API | **3.12** | H2 |
| Visualization | **3.10** | H2 |
| OAuth login | **3.4** | H2 |
| AI layer | **4.1** | H3 |
| Clubs / teams | **4.2** | H3 |

---

## 14. Главный вывод

GetSync — **activity hub**: canonical catalog тренировок и rule-driven delivery между fragmented ecosystems. Не «синхронизатор Karoo с Garmin», а платформа, где Karoo→Garmin — первый supported recipe.

**Фокус сейчас:** hub foundation (`catalog`, `workspace`, `providers`), modularity, reliable delivery — при bounded ops UI в v0.7.

Тактические задачи: [PLAN.md](PLAN.md) · модель: [ACTIVITY-HUB.md](ACTIVITY-HUB.md).
