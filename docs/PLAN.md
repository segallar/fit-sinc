# Roadmap GetSync

> **Обновлено:** 2026-05-26 · **Фокус сейчас:** [дизайн-ревью кабинета → вёрстка **2.10**](#фокус-сейчас-тестирование-и-кабинет-app) · замечания → [DESIGN-FEEDBACK.md](design/DESIGN-FEEDBACK.md).  
> Выполненное (фазы 0–5, 5b, ядро **2.3**) — [PLAN-ARCHIVE.md](PLAN-ARCHIVE.md). **~117** тестов · prod: HH→Garmin.

**Документы:** [APP-UI.md](APP-UI.md) · [design/SCREENS.md](design/SCREENS.md) · [CONNECTIONS.md](CONNECTIONS.md) · [STORAGE.md](STORAGE.md)

---

## Базовая линия (уже в production)

Не в backlog — контекст для приоритетов:

| Область | Состояние |
| ------- | --------- |
| Sync | Webhook HH → FIT → Garmin; dedup SQLite; re-sync |
| Tenants | `user_id`, `data/users/{id}/`, session auth, security tests |
| Кабинет | Activities (List \| Calendar, HH+Garmin), Dashboard + sync log, Settings (profile, connections, garmin-session) |
| Хранение | `StorageBackend` local, `storage_key`, `activities/{source}/` — [STORAGE.md](STORAGE.md) |
| Регистрация | `/register` при `REGISTRATION_OPEN` — без email verify (**2.6**) |
| Бренд в коде | Пакет `getsync`, cookie dual-read — **A+B** ✅ |
| Домен prod (сейчас) | `romansegalla.online` / legacy hosts до **1.5 C** |

---

## Идея продукта (цель)

**GetSync** — хаб спортивных активностей: **источники** → каталог + хранение → **анализ в UI** → доставка в **приёмники** по правилам.

```text
Источники ──► Ingest ──► Каталог (SQLite + файлы) ──► UI (list, calendar, log)
                              │
                              └──► Правила ──► Приёмники (Garmin, S3, …)
```

**Сейчас в prod:** один pipeline **Hammerhead → Garmin**. Остальное — горизонты ниже.

**Не в фокусе:** тренировочный планировщик (TP/Intervals), соцсеть. Приоритет — **надёжный ingest + статус + self-service**.

---

## Снимок кабинета /app

> Спека экранов: [APP-UI.md](APP-UI.md) · карта URL: [design/SCREENS.md](design/SCREENS.md)

| Экран | URL | Роль |
| ----- | --- | ---- |
| **Activities** | `/app/activities` | Главный: `view=list\|calendar`, unified sources |
| **Dashboard** | `/app/` | Сводка sync + `#sync-log` |
| **Settings** | `/app/settings` | Profile, connections, `#garmin-session`, password |
| **Admin** | `/app/admin/` | Users CRUD |

**Layout кабинета (2026-05):** все страницы `/app` и `/app/admin` — **на всю ширину экрана**, контент **к левому краю** (без центрированной колонки 64rem). Спека: [APP-UI.md §1](APP-UI.md#1-принятые-решения-qa-2026-05).

Редиректы: `/app/log` → `/?#sync-log` · `/app/session` → `/settings#garmin-session`.

---

## Фокус сейчас: тестирование и кабинет `/app`

**Цель волны (2–3 недели):** довести **основной интерфейс** `/app` до согласованного дизайна и стабильного поведения.

**Сейчас (шаг 0):** сбор **замечаний к дизайну** — [design/DESIGN-FEEDBACK.md](design/DESIGN-FEEDBACK.md). Можно прислать большим списком в чат или править файл напрямую.

**Не в этой волне:** **1.5 C**, **3.x** хаб, лендинг SEO (**2.11**).

### Критерий «кабинет готов»

| Критерий | Проверка |
| -------- | -------- |
| Все экраны без регрессий | Activities (list+calendar), Dashboard, Settings, Admin |
| Сценарии из [SCREENS.md](design/SCREENS.md) проходят вручную | login → activities → day filter → re-sync → settings |
| Автотесты зелёные | CI + новые тесты на routes/calendar/browse |
| Известные UX-долги закрыты или в backlog с приоритетом | sync log, sidebar, Garmin login UI |
| [APP-UI.md](APP-UI.md) §11 чеклист | 2.10.1–2.10.2 минимум для prod |

### План волны (порядок)

```mermaid
flowchart TB
  T0["0. Замечания к дизайну\nDESIGN-FEEDBACK"]
  T1["1. Согласовать scope P0/P1"]
  T2["2. Вёрстка 2.10\nsidebar + экраны"]
  T3["3. UX долги\n2.3a log · 2.12 Garmin"]
  T4["4. Тесты 2.13\nрегрессия"]
  T0 --> T1 --> T2 --> T3 --> T4
```

| Этап | ID | Содержание | Оценка |
| ---- | -- | ---------- | ------ |
| **0** | — | Сбор замечаний → [DESIGN-FEEDBACK.md](design/DESIGN-FEEDBACK.md) | пока идёт |
| **1** | **2.10** | Sidebar prod + правки по замечаниям (dashboard, activities, settings) | 4–7 дней |
| **2** | **2.3a** | Sync log UX (если в замечаниях / P1) | 0.5 вечера |
| **3** | **2.12** | Garmin login в UI | 1–2 вечера |
| **4** | **2.13** | Автотесты + регрессия **после** дизайна | 2–4 дня |
| **5** | **2.5** | i18n (опционально) | 1–2 вечера |

### Замечания к дизайну (шаг 0)

Файл: **[design/DESIGN-FEEDBACK.md](design/DESIGN-FEEDBACK.md)** — таблицы по экранам, приоритет P0–P3.

Присылай в любом виде, например:

- экран (Activities / Settings / …)
- что не так
- как хочешь (если есть)
- prod или ui-preview

Локально: [UI.md](UI.md).

---

## Горизонты (после текущей волны)

| Горизонт | Когда | Содержание |
| -------- | ----- | ---------- |
| ⏸ **H1 — Запуск** | После стабильного кабинета | **1.5 C** — getsync.me, certbot, HH redirect |
| 🟡 **H2 — остаток продукта** | Параллельно/следом | **2.11** SEO/скрины · **2.4** алерты · **2.6** email |
| 🔵 **H3 — Платформа** | 1–3 месяца+ | **2.8** → **3.9** → **3.1** · **3.3** → **3.5** |

```mermaid
flowchart LR
  NOW["▶ Сейчас\n2.13·2.10·2.3a·2.12"]
  H1["H1\n1.5 C"]
  H3["H3\nхаб"]
  NOW --> H1 --> H3
```

---

## Реестр открытых задач

| ID | Приоритет | Задача | Оценка | Зависимости |
| -- | --------- | ------ | ------ | ----------- |
| **—** | **▶** | **Сбор замечаний к дизайну** — [DESIGN-FEEDBACK.md](design/DESIGN-FEEDBACK.md) | сейчас | — |
| **2.10** | **P0** | Вёрстка по замечаниям: sidebar + dashboard/activities/settings — [APP-UI.md](APP-UI.md) §11 | 4–7 дней | после шага 0 |
| **2.3a** | **P1** | Sync log UX (если в замечаниях) | 0.5 вечера | — |
| **2.13** | **P1** | Тесты и регрессия **после** 2.10 | 2–4 дня | **2.10** |
| **2.12** | **P1** | Garmin login в Settings (не CLI) | 1–2 вечера | **2.10.2** |
| **2.5** | **P2** | i18n тел страниц кабинета; lang в шапке | 1–2 вечера | лучше с **2.10** |
| **2.3b** | **P3** | Календарь v6.1: дни только в облаке | 1 вечер | browse API |
| **1.5 C** | ⏸ H1 | DNS getsync.me, certbot — [1.5-RENAME.md](1.5-RENAME.md) | 1–2 дня | после волны UI |
| **2.11** | ⏸ | Лендинг SEO/скрины (**2.11.3–4**) | 2–3 вечера | **1.5 C**, **2.10** |
| **2.4** | ⏸ | Telegram-алерты | 1–2 вечера | стабильный log UX |
| **2.6** | ⏸ | Email confirm, invite — [2.1e-EMAIL.md](2.1e-EMAIL.md) | 2–4 вечера | перед публичным register |
| **2.7b** | ⏸ | Правила + реестр connections в БД | 1–2 недели | **3.1** |
| **2.8** | 🔵 | Spike ActivityRecord, Source/Sink | 2–3 вечера | — |
| **2.9** | 🔵 | Manual FIT upload | 1–2 вечера | storage ✅ |
| **3.1** | 🔵 | Rule engine, реестр источников/приёмников в БД | ~1 неделя | **2.8**, **3.9** |
| **3.2** | 🔵 | Маршруты в хабе; spike Garmin courses | 1–2 недели | **3.1** |
| **3.3** | 🔵 | S3 adapter, миграция FIT, signed URL — [STORAGE.md](STORAGE.md) | 3–5 дней | local ✅ |
| **3.4** | 🔵 | OAuth/OIDC (Google, …) — [3.4-OAUTH-LOGIN.md](3.4-OAUTH-LOGIN.md) | 2–3 вечера | **1.5 C**, **2.6** |
| **3.5** | 🔵 | Полный хаб: Strava/Wahoo, архив, сложные правила | 2–3 недели | **3.1**, **3.3** |
| **3.6** | 🔵 | Языки fr/…; перевод docs/CLI | по запросу | **2.5** |
| **3.8** | 🔵 | Email-алерты, очередь Playwright (много tenants) | post-scale | — |
| **3.9** | 🔵 | Модули, контракты, границы — [§ 3.9](#39-модульность) | 1–2 недели | **2.8** |
| **3.10** | 🔵 | Расширенные метрики тренировок, карты | backlog | **3.5** |

**Admin (в H2):** подменю Users / Statistics / Logs — 📋 (сейчас только users list).

---

## ⏸ H1 — Запуск (после кабинета)

### 1.5 C — Cutover getsync.me

> **Отложено** до завершения [фокуса на кабинете](#фокус-сейчас-тестирование-и-кабинет-app). Cutover на «сыром» UI дороже откатом.

| Шаг | Статус |
| --- | ------ |
| Код A+B, `deploy/nginx/getsync.conf` | ✅ |
| DNS A → sirocco | 📋 |
| certbot | 📋 |
| Hammerhead OAuth redirect | 📋 |
| Smoke: webhook, login, sync, **все экраны /app** | 📋 |

[1.5-RENAME.md](1.5-RENAME.md).

---

## Детали текущей волны (кабинет)

### 2.13 — Тестирование

См. [таблицу выше](#213--тестирование-кабинета-новая-задача-волны). Приоритетные автотесты:

- `GET /app/activities?view=calendar&year=&month=`
- redirects `/app/log`, `/app/session`
- `test_activities_calendar`, browse/catalog (расширить)
- smoke: login → activities → settings (TestClient)

### 2.3a — Sync log UX

| Задача | Приоритет |
| ------ | --------- |
| **2.3a** | **P0** |
| **2.3b** Calendar облачные дни | **P3** |

### 2.10 — Дизайн UI/UX

Цель: prod = sidebar + плотный SaaS-кабинет (сейчас nav-pills).

| Подзадача | Содержание | Оценка |
| --------- | ---------- | ------ |
| **2.10.1** | Перенос `cabinet.html` → `cabinet_sidebar.html` на все `/app` | 1–2 вечера |
| **2.10.2** | Полировка dashboard, activities, settings; **2.12** в Connections | 3–5 дней |
| **2.10.3** | Admin, mobile, a11y | 2–3 дня |

Прототип: `/app/ui-preview` · [design/README.md](design/README.md).

### 2.12 — Garmin login в UI

**P1** в текущей волне — часть «основного интерфейса» Settings.

### 2.5 — i18n

**P2** — в конце волны или сразу после **2.10.2** (один проход по шаблонам).

### Отложено (H2 остаток)

| ID | Когда |
| -- | ----- |
| **2.11** | После **1.5 C** + стабильный кабинет |
| **2.4** | После **2.3a** |
| **2.6** | Перед публичным register на getsync.me |
| **2.9** | По запросу |
| **2.7b** | С **3.1** |

---

## 🔵 H3 — Платформа

### Целевая архитектура хаба

```mermaid
flowchart LR
  SRC[Sources] --> ING[Ingest]
  ING --> DB[(Catalog)]
  DB --> UI[UI]
  DB --> ENG[Rules]
  ENG --> SNK[Sinks]
```

Каталог MVP в UI уже есть (HH+Garmin); не хватает **rule engine** и вторых адаптеров.

### 3.9 — Модульность

| Шаг | Содержание |
| --- | ---------- |
| 3.9.0 | Граф импортов, hot spots |
| 3.9.1 | `docs/MODULES.md` — целевая схема |
| 3.9.2 | Protocols: Source, Sink, Store, Storage |
| 3.9.3 | Рефактор pipeline без смены поведения |
| 3.9.4 | Контрактные тесты на границах |

**Порядок H3:** **2.8** → **3.9** → **3.1** ∥ **3.3** → **3.5** · **3.4** после **1.5 C**.

### 3.3 — S3

Local `StorageBackend` ✅. Открыто: boto3 adapter, migrate CLI, signed download URL.

### 3.4 — OAuth/OIDC

Детали: [3.4-OAUTH-LOGIN.md](3.4-OAUTH-LOGIN.md). После email/identity (**2.6**) и cutover домена.

### 3.5 — Полный хаб

Strava/Wahoo, импорт архива, сложные правила — только после **3.1** + **3.9**.

---

## Ops и качество (открытое)

| Задача | ID | Примечание |
| ------ | -- | ---------- |
| Garmin upload на sirocco: `upload_ready` в мониторинге | ops | Код ✅, проверка на VPS |
| Убрать prod-зависимость от `GARMIN_EMAIL` в `.env` | ops | Multi-tenant |
| Admin: Statistics / Logs | H2 | Отдельные страницы |

Закрыто (не трекать): CI smoke, security tests, build footer, legacy cookie — см. [PLAN-ARCHIVE.md](PLAN-ARCHIVE.md).

---

## Риски

| Риск | Mitigation |
| ---- | ---------- |
| Garmin меняет auth/upload | JWT + HTTP + Playwright + garth; pin versions |
| Календарь пустой до browse | Подсказка в UI; **2.3b** не блокирует волну |
| Регрессия при **2.10** | Сначала **2.13**, потом sidebar — тесты до merge |
| Регистрация без **2.6** | `REGISTRATION_OPEN=false` на prod |
| Cutover до готовности UI | **1.5 C** только после чеклиста кабинета |

---

## Ссылки

| Документ | Назначение |
| -------- | ---------- |
| [PLAN-ARCHIVE.md](PLAN-ARCHIVE.md) | История фаз 0–5, 5b, выполненные чеклисты |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Поток данных, tenants, модули |
| [APP-UI.md](APP-UI.md) | Страницы и компоненты `/app` |
| [1.5-RENAME.md](1.5-RENAME.md) | Cutover бренда |
| [2.1-REGISTER.md](2.1-REGISTER.md) | Регистрация (реализовано) |
| [2.1e-EMAIL.md](2.1e-EMAIL.md) | Email (**2.6**) |
