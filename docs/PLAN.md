# Roadmap fit_sinc

> **Статус (2026-05-25):** MVP (фазы 0–4) в production.

**Текущее состояние:** [README](../README.md) · [ARCHITECTURE.md](ARCHITECTURE.md)  
**Операции:** [CI-CD.md](CI-CD.md) · [API Hammerhead](API_HAMMERHEAD.md) · [API Garmin](API_GARMIN.md)

**Репозиторий:** https://github.com/segallar/fit-sinc

---

## Прогресс

| Фаза | Статус |
|------|--------|
| 0a–0c DevOps (sirocco, certbot, nginx) | ✅ |
| 0d fit_sinc deploy (stub, systemd, HTTPS) | ✅ |
| 1 Hammerhead OAuth + Garmin auth | ✅ |
| 2 Sync core + webhook sync + UI | ✅ |
| 3 Garmin upload (web JWT, browser, fallback) | ✅ код / ⚠️ ops на сервере |
| 4 CI (GitHub Actions test + deploy main) | ✅ |
| 5 Мультипользовательность (tenants, `/admin`, `/app`) | ✅ |
| 6 UI v2 (календарь, поиск, баннер, failed) | 📋 план |
| 6.1 Алерты (Telegram / email) | 📋 план |
| — Ops: README + тесты CI | ✅ README / 📋 расширить тесты |
| 7 Синхронизация из нескольких источников | 📋 план |
| 8 Маршруты (routes) | 📋 план / исследование |

---

## Roadmap v2

Порядок работ: **сначала фундамент (tenants + админка)**, потом UI и новые источники, routes — в конце (исследование Garmin).

```mermaid
flowchart TB
    subgraph now [Сейчас v1]
        WH[webhook HMAC]
        UI1[UI + один Basic Auth]
        D1[data/ без user_id]
    end
    subgraph p5 [Фаза 5]
        T[tenants + user_id в БД]
        ADM["/admin — отдельная привилегия"]
        APP["/app — кабинет пользователя"]
    end
    subgraph p6 [Фаза 6]
        UI2[календарь + поиск, баннер, ошибки]
    end
    subgraph p7 [Фаза 7]
        SRC[источники: HH, файл, …]
    end
    subgraph p8 [Фаза 8]
        RTE[routes HH ↔ Garmin courses]
    end
    now --> p5 --> p6 --> p7 --> p8
```

### Фаза 5: Мультипользовательность + разделение админ / пользователь

**Проблема v1:** один пароль nginx на весь UI; webhook шлёт `userId`, но сервис его не маршрутизирует; все токены в `data/` без изоляции.

**Цель:** несколько пользователей сервиса, каждый со своими Hammerhead/Garmin и своими данными; **админка под отдельной привилегией**, не смешивать с кабинетом райдера.

#### Две зоны доступа

| Зона | URL (черновик) | Кто | Auth |
|------|----------------|-----|------|
| **Публичное API** | `/webhooks/*`, `/health` | Hammerhead, мониторинг | HMAC / без auth |
| **Кабинет пользователя** | `/app/*` или `/u/{slug}/*` | Владелец аккаунта | Сессия приложения (логин/пароль или magic link) |
| **Админка** | `/admin/*` | Оператор сервиса (ты) | **Отдельный** nginx Basic Auth *или* отдельный admin-login в приложении |

Не использовать один `htpasswd` на всё: сейчас любой с паролем видит все данные.

#### nginx (целевая схема)

```
/webhooks/     → без auth
/health        → без auth
/admin/        → auth_basic admin (отдельный .htpasswd_fit_sinc_admin)
/app/          → proxy в FastAPI (auth внутри приложения по user)
```

Либо оставить Basic Auth только на `/admin/`, а пользователей пускать через cookie после POST `/app/login`.

#### Роли

| Роль | Права |
|------|--------|
| **admin** | В админке: завести/редактировать пользователей (email, Telegram, timezone, пароль), привязка `hammerhead_user_id`, disable, просмотр логов и статусов по всем; **не** видит пароли Garmin/Hammerhead в открытом виде |
| **user** | Вход в `/app` своим email + паролем; только свой кабинет, HH/Garmin OAuth, sync; смена пароля у себя (опционально v2.1) |

#### Профиль пользователя (ведётся в админке)

Админ создаёт и обслуживает учётки; у каждого райдера — **свой** доступ в кабинет, не общий nginx-пароль.

| Поле | Назначение |
|------|------------|
| `slug` | URL/id: `/app` после логина, пути в CLI `--user slug` |
| `display_name` | Имя в UI |
| `email` | Логин в кабинет (unique), уведомления (опционально) |
| `telegram` | `@username` или `chat_id` — алерты об ошибках sync (Phase 6+), контакт для админа |
| `timezone` | IANA, напр. `Europe/Moscow`, `Europe/Berlin` — **все даты в кабинете** пользователя |
| `password` | Задаёт/сбрасывает **админ** при создании; в БД только `password_hash` (bcrypt/argon2) |
| `hammerhead_user_id` | Связь с webhook `userId` Hammerhead |
| `disabled` | Запрет входа и sync |

**Логин в кабинет:** `email` + пароль (сессия cookie, HttpOnly). Telegram — не замена пароля на старте, а канал связи и push-уведомлений.

**Часовой пояс:** сейчас в коде всё в MSK ([`timeutil.py`](../fit_sinc/timeutil.py)); в v2 — `format_* (iso, tz=user.timezone)`, «Updated …» и таблицы activities/log в TZ пользователя. UTC хранить в SQLite как сейчас.

#### Модель данных

```text
users(
  id TEXT PK,              -- uuid или slug
  slug TEXT UNIQUE,
  display_name TEXT,
  email TEXT UNIQUE,
  telegram TEXT,           -- nullable
  timezone TEXT NOT NULL DEFAULT 'Europe/Moscow',
  hammerhead_user_id TEXT UNIQUE,
  password_hash TEXT NOT NULL,
  created_at, updated_at,
  disabled INTEGER DEFAULT 0
)

activities(user_id, activity_id, …)   -- PK (user_id, activity_id)
sync_events(user_id, …)
session_refresh_events(user_id, …)

data/users/{id}/
  hammerhead_tokens.json
  garth/
  garmin_web/
  fits/
```

Отдельная таблица `user_credentials` не нужна, если hash в `users`.

**Webhook:** `userId` из payload → `users.hammerhead_user_id` → `sync_activity(..., user_id=…)`.

**Миграция v1:** один пользователь `default` из текущего `tokens.user_id` + перенос `data/*` → `data/users/default/`.

#### CLI

```bash
fit_sinc user create roman --hammerhead-user-id 192184
fit_sinc user list
fit_sinc --user roman hammerhead auth
fit_sinc --user roman garmin login
fit_sinc --user roman sync --since 2025-01-01
```

#### Админка `/admin` (MVP)

Отдельный layout, отдельный вход (nginx `htpasswd_admin` или `admin` + пароль в приложении).

| Страница | Действия |
|----------|----------|
| **Users** | Таблица: имя, email, Telegram, TZ, HH id, HH/Garmin status, последний sync, disabled |
| **User → New** | Форма: slug, display_name, email, telegram, timezone (select IANA), password ×2, hammerhead_user_id |
| **User → Edit** | То же + «Сбросить пароль», disable/enable, ссылка «открыть лог пользователя» |
| **User → Log** | sync_events / session_refresh только этого `user_id` |
| **System** | версия, disk, health, сводка `upload_ready` по пользователям |

Кабинет `/app` **не** даёт список других пользователей и не меняет email/TZ (только админ, чтобы не ломать привязку webhook).

#### Кабинет пользователя `/app` (MVP)

- `GET/POST /app/login` — email + password
- После входа: текущий дашборд (activities, log, session) **в его timezone**
- Подключения: «Подключить Hammerhead» / «Подключить Garmin» (OAuth в контексте `user_id`)
- Профиль (read-only v2.0): email, Telegram, timezone — «обратитесь к администратору»

Позже (v2.1): смена пароля в кабинете; привязка Telegram bot для алертов (`/start` → сохранить `chat_id`).

---

### Фаза 6: UI v2 (в кабинете пользователя)

После Phase 5 — UI в контексте `user_id` (`/app/...`), timezone пользователя.

#### Календарь + поиск (главный экран активностей)

**Сейчас (v1):** `/activities` — таблица + поля `date_from` / `date_to` + `q` (имя). Календаря нет, даты не видны «с высоты месяца».

**Цель:** быстро найти поездку по дню и по названию.

| Элемент | Поведение |
|---------|-----------|
| **Поиск** | Одна строка сверху (`q`): имя активности, substring; Enter / debounce → обновить таблицу; сохранять в query string |
| **Календарь** | Месяц в TZ пользователя; на каждом дне — метки: есть активности, цвет по worst `fit_sinc_status` (synced / error / pending / none) |
| **Клик по дню** | `date_from` = `date_to` = выбранный день → таблица под календарём |
| **Навигация** | ‹ › месяц; «Сегодня»; опционально неделя |
| **Связка с фильтрами** | status (error / synced), source (HH/Garmin), type — как сейчас, не сбрасывать при смене дня |

**Данные для календаря:**

- **v6.0 (быстро):** агрегат из SQLite `activities` по `user_id` + `DATE(activity_date)` — counts и max severity (уже синкнутые в fit_sinc)
- **v6.1 (полнее):** опционально подгрузка HH/Garmin за месяц для дней «только в облаке, ещё не в SQLite» — тяжелее, по кнопке «Обновить месяц»

**Техника (без SPA):** Jinja2 + HTMX или отдельный `GET /app/activities/calendar?year=&month=` → HTML fragment; клик дня — `GET /app/activities?...&date_from=...`. Стили в `html.py` / static CSS.

**Макет:**

```text
[ 🔍 Поиск по названию________________________ ]

     [ ‹ ]   Май 2026   [ › ]   [Сегодня]

   Пн Вт Ср Чт Пт Сб Вс
        ·  ●  ●  ○  ·     ← точки/цвета статуса
   ...

   [ Hammerhead | Garmin ]  status ▼  type …

   ┌─ таблица активностей (как сейчас) ─┐
```

#### Остальное UI v2

- Баннер: Hammerhead + Garmin `upload_ready` + TTL JWT
- Карточки: synced / error / pending (дашборд)
- Вкладка/быстрый фильтр «только ошибки», понятный лог (`duplicate` vs error)
- Re-sync / force с подтверждением (частично уже есть `retry` на `/activities`)

Админка — отдельный layout (`/admin`), без календаря райдеров (только таблица пользователей + лог).

**Оценка календарь + поиск:** ~1 вечер (SQLite aggregate + шаблон); +0.5 вечера с HTMX и полировкой.

---

### Надёжность и ops

> **Не путать с Фазой 5 (tenants).** Здесь — меньше сюрпризов ночью и порядок в репозитории.

| Задача | Фаза | Статус | Зависимости |
|--------|------|--------|-------------|
| Smoke-тесты в CI (`compileall`, unittest) | 4 | ✅ | — |
| README на GitHub | ops | ✅ | — |
| Тесты: webhook HMAC endpoint, `sync_activity` с моками HH/Garmin | 6 / ops | 📋 | можно параллельно 5 |
| **Баннер статуса** на дашборде | 6 | 📋 | лучше после 5 (`/app`) |
| **Очередь failed** — фильтр `status=error`, retry | 6 | 📋 | retry уже в коде |
| Понятный sync log (`duplicate` ≠ error) | 6 | 📋 | — |
| **Алерты Telegram** при `sync_status=error` или N ошибок подряд | **6.1** | 📋 | поле `telegram` из Фазы 5 |
| Email-алерты | 6.1+ | 📋 | опционально |

**Порядок:** Фаза **5** → Фаза **6** (баннер, failed, **календарь**, поиск) → **6.1** (бот) → расширить тесты в щели.

**Быстрый путь без Фазы 5 (опционально):** календарь на текущем `/activities` за 1–2 вечера — потом перенести под `/app` при tenants.

---

### Фаза 7: Несколько источников (activities)

Абстракция, чтобы не плодить `if hammerhead` в `sync/service.py`:

```text
Source (download ActivityPayload + external_id)
  → Sink Garmin (upload FIT)
  → Store (dedup по user_id + source + external_id)
```

| Источник | Приоритет | Триггер | Формат |
|----------|-----------|---------|--------|
| Hammerhead | ✅ есть | webhook + backfill | FIT API |
| Manual upload | средний | UI/CLI | `.fit` файл |
| Wahoo / Strava / … | низкий | исследование API | TBD |

Каждый источник настраивается **per user** в кабинете; в админке — только вкл/выкл и диагностика.

---

### Фаза 8: Маршруты (routes)

**Hammerhead API** (OpenAPI):

- `route:read` — `GET /routes` (список, polyline в summary)
- `route:write` — `POST /routes/file` (GPX, FIT, TCX, KML, KMZ → Karoo)
- Webhook **только для activities**, не для routes

**Garmin Connect:** отдельный продукт (Courses). Официального upload courses для личного аккаунта нет; нужен **spike**: GPX → Connect (web UI?), garth, ограничения.

**Варианты направления (выбрать до кода):**

1. **Garmin → Hammerhead** — курс в Garmin экспорт GPX → push в Karoo (`route:write`) — проще для v1 routes
2. **Hammerhead → Garmin** — список routes HH → дублировать в Garmin courses — сложнее (нет GET file в API, только upload в HH)
3. **Двусторонняя** — позже

Рекомендация: Phase 8.0 = spike Garmin courses + прототип GPX; Phase 8.1 = HH `route:write` из файла.

---

### Зависимости и оценка

| Фаза | Зависит от | Оценка |
|------|------------|--------|
| 5 tenants + admin | — | 3–5 дней |
| 6 UI v2 (календарь, поиск, баннер, failed) | 5 | 2–3 дня |
| 6.1 алерты Telegram | 5, 6 | 0.5–1 день |
| 7 multi-source | 5 | 2–4 дня на источник |
| 8 routes | 5, spike Garmin | 1–2 недели с исследованием |

---

## Риски

| Риск | Mitigation |
|------|------------|
| Garmin меняет auth / upload UI | Web JWT + Playwright + HTTP + garth fallback; pin `garth-ng`, `playwright` |
| Playwright на VPS (RAM, headless) | HTTP и garth fallback; cookies refresh без браузера |
| Дубликаты в Garmin | SQLite dedup по `activityId` |
| FIT ещё не готов на Hammerhead | retry 5/15/30 с |
| Потеря tokens | Hammerhead refresh; `garmin refresh-web`; backup `data/` |
| Webhook повторы | idempotency в `store.is_synced()` |

---

## TODO

### Выполнено (v1)

- [x] DevOps: sirocco, nginx, certbot, systemd
- [x] Stub + deploy fit.romansegalla.online
- [x] Hammerhead OAuth + API client
- [x] Garmin auth (garth-ng + web session)
- [x] Webhook HMAC
- [x] Favicon + dashboard
- [x] Sync service + SQLite
- [x] Webhook → background sync
- [x] Backfill CLI
- [x] UI: лог, активности, скачивание .fit
- [x] Документация деплоя → [CI-CD.md](CI-CD.md)
- [x] Garmin upload: web JWT, refresh, browser/HTTP/garth chain
- [x] Проверить на sirocco: `garmin status` → `upload_ready`, sync работает (2026-05-25)
- [x] CI pipeline: GitHub Actions, `scripts/ci/deploy.sh`, smoke tests
- [x] Secret `SSH_PRIVATE_KEY` в GitHub
- [x] README GitHub + разделение docs (ARCHITECTURE / PLAN)

### Roadmap v2 (план)

- [x] Фаза 5: tenants, `user_id` в БД, webhook → user, `data/users/{id}/`
- [x] Фаза 5: `/admin` — CRUD users (email, telegram, timezone, password, HH id)
- [x] Фаза 5: `/app` — login email+password, сессия, UI в TZ пользователя
- [ ] Фаза 6: календарь + поиск на `/app/activities`, баннер, failed, лог
- [ ] Фаза 6.1: Telegram-алерты при ошибках sync
- [ ] Ops: расширить smoke (webhook endpoint, sync mocks)
- [ ] Фаза 7: абстракция Source/Sink, manual FIT
- [ ] Фаза 8: spike routes / Garmin courses

### Открыто (мелочи v1)

- [x] Push в `main` → https://github.com/segallar/fit-sinc
- [ ] UI: re-sync в кабинете (частично есть `retry` на `/activities`)
