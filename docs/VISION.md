# Product Vision и стратегия GetSync

> **Создано:** 2026-05-27 · **Обновлено:** 2026-05-27 · **Версия:** 0.7.0  
> **Тактический roadmap:** [PLAN.md](PLAN.md) · **Domain v0:** [DOMAIN-MODEL.md](DOMAIN-MODEL.md) · **Архитектура:** [ARCHITECTURE.md](ARCHITECTURE.md)

Стратегический документ: *куда* и *зачем* развивается GetSync. Конкретные задачи, оценки и статусы — только в [PLAN.md](PLAN.md).

---

## 1. Что такое GetSync

GetSync — платформа для хранения, нормализации, синхронизации и анализа спортивных данных.

Изначально проект появился как решение конкретной проблемы:

- тренировки и спортивные данные распределены между множеством устройств и сервисов;
- экосистемы плохо синхронизируются между собой;
- возникают дубли;
- данные теряются;
- пользователь не владеет своей полной спортивной историей.

**Текущий production workflow:**

Hammerhead Karoo → Hammerhead Cloud → GetSync → Garmin Connect.

**Долгосрочная цель:**

GetSync — **unified athlete data platform**: единый слой данных спортсмена между устройствами, сервисами и аналитическими системами.

**Positioning (одна строка):**

> GetSync — personal athlete data layer: собирает, нормализует и маршрутизирует спортивные данные между устройствами и облаками. Вы владеете копией истории; внешние платформы — providers/sinks, не source of truth.

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

- единое хранилище спортивных данных;
- слой нормализации данных;
- sync/orchestration platform;
- open ecosystem для интеграций и аналитики (долгосрочно).

### Долгосрочная цель

- unified athlete history;
- centralized sports data layer;
- open platform для AI и внешних приложений.

### Что важно

GetSync — **не** просто календарь, social network или upload utility. Это инфраструктурная платформа поверх fragmented sports ecosystem.

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
| **Data Model** | Activity, Connection, SyncRule, Wellness, … | [DOMAIN-MODEL.md](DOMAIN-MODEL.md), [DATABASE.md](DATABASE.md) |
| **Athlete Workspace** | Календарь, activities, filters, sync status | **2.3** ✅, **2.10** |
| **Sync Engine** | import/export, retries, dedup | `sync/service.py`, webhook |
| **Rule Engine** | routing, filters, priorities | **3.1** |
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
- Hammerhead OAuth + webhook pipeline;
- Garmin upload + browse;
- activity storage + unified catalog + calendar;
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
| P1 | Domain foundation + второй source | [DOMAIN-MODEL.md](DOMAIN-MODEL.md), **2.7**, **3.11.1–3.11.2** |
| P1 | Trust для публичного register | **2.6** / **2.1e** |
| P2 | Rule engine design → impl | **3.1** (после 2+ sources) |
| Не сейчас | Social, mobile app, AI, public API GA | **3.12**, **4.x** |

---

## 11. План по трём горизонтам

### Горизонт 1 — Сейчас

**Цель:** стабилизировать архитектуру и ядро платформы.

- Зафиксировать [DOMAIN-MODEL.md](DOMAIN-MODEL.md) v0, module boundaries (**3.9** design)
- Reliability sync, dedup, tenant isolation
- UI — minimum ops surface (**2.10**, **2.12**)
- Garmin pull spike + pipeline (**3.11**)
- Open-source — не публиковать всё сразу; сильное ядро

### Горизонт 2 — Следующая версия продукта

**Цель:** athlete workspace + multi-source hub.

- Unified workspace: calendar, activity viewer, routes, planned workouts
- Rule engine (**3.1**), integrations hub (Strava, … — по priority matrix)
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
| Domain model v0 | [DOMAIN-MODEL.md](DOMAIN-MODEL.md) | H1 |
| Connections в БД | **2.7** | H1 |
| Garmin login UI | **2.12** | H1 / v0.7 |
| Garmin pull | **3.11.*** | H1 |
| Modularity | **3.9**, **2.8** | H1→H2 |
| Rule engine | **3.1** | H2 |
| Full hub | **3.5** | H2 |
| Public API | **3.12** | H2 |
| Visualization | **3.10** | H2 |
| OAuth login | **3.4** | H2 |
| AI layer | **4.1** | H3 |
| Clubs / teams | **4.2** | H3 |

---

## 14. Главный вывод

GetSync — не просто сервис синхронизации, а попытка создать unified athlete history и независимый слой спортивных данных между fragmented ecosystems.

**Фокус сейчас:** canonical data model, modularity, reliable sync foundation — при bounded ops UI в v0.7.

Тактические задачи и реестр: [PLAN.md](PLAN.md).
