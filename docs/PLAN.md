# Roadmap fit_sinc

> **Статус (2026-05-25):** MVP (фазы 0–5) в production; **5b** в работе (5b.0–5b.1 ✅, UI ✅, остаток 5b.2 — Settings в nav).

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
| 5 Мультипользовательность (tenants, `/admin`, `/app`) | ✅ MVP |
| **5b** Единый кабинет, регистрация, настройки, без Basic Auth | 🔄 5b.0–5b.1 ✅ · UI ✅ · 5b.2 ⏳ Settings в nav |
| **UI** Новый интерфейс приложения (Jinja2 + Tailwind) | ✅ |
| 6 UI v2 (календарь, поиск, баннер, failed) | 📋 план |
| 6.1 Алерты (Telegram / email) | 📋 план |
| 6.2 Локализация (i18n: ru, en, …) | 📋 план |
| — Ops: README + тесты CI | ✅ README / 📋 расширить тесты |
| 7 Синхронизация из нескольких источников | 📋 план |
| 8 Маршруты (routes) | 📋 план / исследование |

---

## Roadmap v2

Порядок работ: **5 (MVP) ✅ → UI ✅ → 5b → 6 (календарь, баннер, failed) → 6.2 (i18n) → 7/8**. Routes — в конце (исследование Garmin).

```mermaid
flowchart TB
    subgraph done [Сделано]
        P5[Фаза 5 MVP: tenants, /app, admin CRUD]
    end
    subgraph p5b [Фаза 5b]
        R1[is_admin + /app/admin ✅]
        UI[новый интерфейс Jinja+Tailwind ✅]
        UNI[Settings в nav ⏳]
        REG[саморегистрация]
        SET[настройки: профиль + HH/Garmin]
        NGX[без nginx Basic Auth]
        R1 --> UI
        UI --> UNI
        UNI --> REG
        UNI --> SET
        SET --> NGX
    end
    subgraph p6 [Фаза 6]
        UI2[календарь + поиск, баннер, ошибки]
        I18N[локализация ru / en / …]
        UI2 --> I18N
    end
    subgraph p7 [Фаза 7]
        SRC[источники: HH, файл, …]
    end
    subgraph p8 [Фаза 8]
        RTE[routes HH ↔ Garmin courses]
    end
    done --> p5b --> UI2 --> p7 --> p8
```

### Фаза 5: Мультипользовательность (MVP) — ✅

**Сделано (2026-05):** `user_id` в БД и sync; `data/users/{id}/`; webhook → tenant; `/app/login` + кабинет; CRUD users (сейчас `/app/admin`); сессии cookie; CLI `--user`.

**Ограничения MVP (ещё открыты в 5b):**

- nginx **Basic Auth** на весь UI (двойной вход) — снять в **5b.5**
- Нет `/register` — **5b.3**
- Нет `/app/settings` — профиль и HH/Garmin только через админку / CLI — **5b.4**
- Даты в таблицах пока в MSK ([`timeutil.py`](../fit_sinc/timeutil.py)); поле `users.timezone` есть, форматирование в TZ пользователя — вместе с **6** / settings

**Уже сделано в 5b.1:** один логин; админка `/app/admin/*` по `users.is_admin`; legacy `/admin/*` → 301; `ADMIN_PASSWORD` убран.

Ниже — **целевая** модель Phase 5 (частично уже в коде); детальный план доработки — **Фаза 5b**.

#### Две зоны доступа (целевая, после 5b)

| Зона | URL | Кто | Auth |
|------|-----|-----|------|
| **Публичное API** | `/webhooks/*`, `/health` | Hammerhead, мониторинг | HMAC / без auth |
| **Публичный UI** | `/login`, `/register` | Гость | — |
| **Кабинет** | `/app/*` | Владелец аккаунта | Сессия (email + password) |
| **Админ внутри кабинета** | `/app/admin/*` | `users.is_admin = 1` | та же сессия + проверка роли |

> **Устарело:** отдельный `/admin/login` и nginx `auth_basic` на `/` — убираем в 5b.

#### nginx (целевая схема, после 5b)

```
/webhooks/     → без auth
/health        → без auth
/              → proxy в FastAPI (только сессия приложения)
```

#### Роли (целевая, после 5b)

| Роль | Права |
|------|--------|
| **admin** | Пункты меню **Admin** в том же `/app`: users CRUD, disable, promote admin, логи по всем; **не** видит пароли Garmin/Hammerhead |
| **user** | Свой кабинет, **Настройки** (профиль, пароль, HH/Garmin connect/disconnect), sync |

#### Профиль пользователя

**После 5b:** пользователь редактирует сам в `/app/settings`; админ — disable, promote, сброс чужого пароля, поддержка `hammerhead_user_id`.

| Поле | Назначение |
|------|------------|
| `slug` | URL/id: `/app` после логина, пути в CLI `--user slug` |
| `display_name` | Имя в UI |
| `email` | Логин в кабинет (unique), уведомления (опционально) |
| `telegram` | `@username` или `chat_id` — алерты об ошибках sync (Phase 6+), контакт для админа |
| `timezone` | IANA, напр. `Europe/Moscow`, `Europe/Berlin` — **все даты в кабинете** пользователя |
| `locale` | **6.2:** язык UI, напр. `ru`, `en` — см. [Фаза 6.2](#фаза-62-локализация-i18nl10n) |
| `password` | Регистрация / смена в кабинете; админ может сбросить; в БД только `password_hash` |
| `is_admin` | **5b:** флаг в БД; пункты меню Admin только при `is_admin=1` |
| `hammerhead_user_id` | Связь с webhook `userId`; заполняется после OAuth Hammerhead в настройках |
| `disabled` | Запрет входа и sync (только админ) |

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
  locale TEXT NOT NULL DEFAULT 'ru',   -- 6.2: BCP 47, напр. ru, en
  hammerhead_user_id TEXT UNIQUE,
  password_hash TEXT NOT NULL,
  is_admin INTEGER DEFAULT 0,   -- 5b
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

#### Админка (`/app/admin/*` — ✅ с 5b.1; legacy `/admin` → 301)

| Страница | Действия |
|----------|----------|
| **Users** | Таблица: имя, email, Telegram, TZ, HH id, HH/Garmin status, последний sync, disabled |
| **User → New** | Форма (при закрытой регистрации); иначе только promote/disable |
| **User → Edit** | disable/enable, promote admin, сброс пароля, правка HH id (поддержка) |
| **User → Log** | sync_events / session_refresh по `user_id` |
| **System** | версия, health, сводка `upload_ready` по пользователям |

В **5b** те же страницы под `/app/admin/*`, пункты меню **Admin** видны только `is_admin`.

#### Кабинет `/app` (MVP — ✅; цель 5b — настройки)

- `GET/POST /app/login` — email + password ✅
- Дашборд, activities, log, session ✅
- **5b:** `GET/POST /register` — саморегистрация (`REGISTRATION_OPEN` в `.env`)
- **5b:** `/app/settings` — профиль (email, telegram, timezone), смена пароля, Hammerhead/Garmin (connect / disconnect / status)

Позже (6.1): Telegram bot для алертов (`/start` → `chat_id`).

---

### UI: Новый интерфейс приложения

> **Отдельный пункт roadmap** — визуальный слой и шаблоны, не путать с **Фазой 6** (календарь, баннер, failed).

**Цель:** единый современный интерфейс для `/app` и `/app/admin` вместо v1 (`html.py` + inline `BASE_CSS`).

**Сделано (2026-05):**

| Элемент | Статус |
|---------|--------|
| Jinja2 layouts: `cabinet.html`, `auth.html`, `base.html` | ✅ |
| Tailwind `app.css` (сборка из `frontend/`) | ✅ |
| Страницы: login, dashboard, activities, log, session | ✅ |
| Admin: users, user form | ✅ |
| Компоненты: user bar, nav, pager, re-sync, timezone select, status badges | ✅ |
| Удалены: `ui_v2.py`, `/ui-preview`, `H.page()` / `BASE_CSS` | ✅ |
| `html.py` — только форматтеры (`esc`, `fmt_*`) | ✅ |

**Остаток (не блокирует UI, идёт в 5b):**

| Элемент | Фаза |
|---------|------|
| Пункт **Settings** в nav → `/app/settings` | 5b.4 |
| Полировка UX (календарь, баннер, failed-очередь) | 6 |

**Документация:** [UI.md](UI.md) · коммит `feat(web): мигрировать UI на Jinja2 и Tailwind`.

---

### Фаза 5b: Единый кабинет, регистрация, настройки, без Basic Auth

**Цель:** одно приложение и одна сессия; админ — часть UI по привилегии; пользователи сами регистрируются и управляют профилем и подключениями HH/Garmin; nginx без Basic Auth.

```mermaid
flowchart TB
    subgraph public [Публично]
        WH["/webhooks/*"]
        HL["/health"]
        REG["/register"]
        LOG["/login"]
    end
    subgraph session [Сессия cookie]
        APP["/app/* кабинет"]
        SET["/app/settings"]
        ADM["/app/admin/* только is_admin"]
    end
    WH --> Sync
    LOG --> APP
    REG --> APP
    APP --> SET
    APP --> ADM
```

| Требование | Решение |
|------------|---------|
| Админка «часть системы» | Один layout `/app`; в nav блок **Admin** (Users, System) только если `user.is_admin` |
| Саморегистрация | `GET/POST /register` (+ `REGISTRATION_OPEN=true` в `.env`) |
| HH/Garmin на пользователя | Уже `data/users/{id}/`; UI **Настройки → Подключения** + OAuth в контексте сессии |
| Профиль | **Настройки → Профиль** — email, telegram, timezone, display_name; смена пароля |
| Без Basic Auth | Убрать `auth_basic` в `deploy/nginx/fit.conf`; cookie `https_only` на prod |

#### Подфазы и оценка

| Подфаза | Содержание | Оценка |
|---------|------------|--------|
| **5b.0** | Решения: открытая регистрация / invite-only; bootstrap первого admin (`BOOTSTRAP_ADMIN_EMAIL` или CLI `user promote-admin`) | ✅ [5b-DECISIONS.md](5b-DECISIONS.md) |
| **5b.1** | `users.is_admin`; один логин; убрать `SESSION_ADMIN_KEY` + `/admin/login`; guard `/app/admin/*`; legacy `/admin` → 301 | ✅ |
| **5b.2** | Остаток layout: пункт **Settings** в nav → `/app/settings` (основной UI — см. раздел **UI** выше) | ⏳ 5b.4 |
| **5b.3** | `/register`: slug/email/password/timezone, rate limit, auto-login → `/app/settings` | 1 вечер |
| **5b.4** | `/app/settings`: профиль + пароль; HH OAuth callback с привязкой к сессии; Garmin connect/status; admin edit — disable, promote, сброс | 2 вечера |
| **5b.5** | nginx: снять Basic Auth; `SESSION_SECRET` + `https_only`; обновить [CI-CD.md](CI-CD.md), README | ½ дня |
| **5b.6** | Тесты: register, settings, `/app/admin` 403/200; зачистка `ADMIN_PASSWORD` из docs | 1 вечер |

**Порядок (актуальный):** `5b.1` ✅ → **UI** ✅ → **`5b.4`** (Settings + HH/Garmin) → **`5b.5`** (nginx) → **`5b.3`** (register) → **5b.6**.

**MVP «можно пользоваться»:** 5b.1 ✅ + **UI** ✅ + **5b.4** + **5b.5** + **5b.3**.

#### 5b.2 — остаток (Settings в nav)

| Элемент | Статус |
|---------|--------|
| Пункт **Settings** в nav → `/app/settings` | ⏳ ждёт 5b.4 |

> User bar, формы, Jinja layout, Tailwind — перенесены в раздел **[UI: Новый интерфейс приложения](#ui-новый-интерфейс-приложения)** ✅.

#### Garmin Connect — сессия на каждого пользователя (уже в коде)

Каждый tenant: `data/users/{id}/garmin_web/session.json` (`JWT_WEB`, `session`, …), отдельно `garth/` для OAuth fallback.

| Вопрос | Как сейчас |
|--------|------------|
| JWT общий? | **Нет** — свой на `user_id`; фоновый цикл в `app.py` обновляет по списку пользователей |
| N виртуальных браузеров? | **Нет** — headless Chromium **по операции** (refresh/upload), затем `browser.close()` |
| Refresh JWT | Сначала HTTP (`curl_cffi` + cookie `session`), Playwright — fallback |
| Первичная привязка | На пользователя: `fit_sinc --user <slug> garmin login` или import cookies (до **5b.4** — только CLI) |

**Чеклист нового пользователя (ops, до Settings UI):**

1. Создать user (админка или `fit_sinc user create`)
2. Заполнить `hammerhead_user_id` (= `userId` в webhook)
3. `fit_sinc --user <slug> hammerhead auth`
4. `fit_sinc --user <slug> garmin login` (или import-web-cookies)
5. `fit_sinc --user <slug> garmin status` → `upload_ready`

**Техдолг:** глобальные `GARMIN_EMAIL` / `GARMIN_PASSWORD` в `.env` используются как fallback при отсутствии сессии — для нескольких разных Garmin-аккаунтов **не подходит**; убрать из prod-сценария после **5b.4** (логин только в контексте сессии пользователя).

#### `/app/settings` (детально)

| Секция | Поля / действия |
|--------|------------------|
| **Профиль** | `display_name`, `email`, `telegram`, `timezone`, `locale` (язык UI — см. [6.2](#фаза-62-локализация-i18nl10n)) |
| **Безопасность** | смена пароля (старый + новый) |
| **Hammerhead** | статус; «Подключить» / «Отключить»; OAuth → `hammerhead_user_id` + `data/users/{id}/hammerhead_tokens.json` |
| **Garmin** | `upload_ready`, JWT TTL; «Подключить» (garmin login / import cookies / refresh); пароль в UI не показывать |

**Техника OAuth Hammerhead:** callback с `state` (подписанный `user_id`); redirect URI production; не писать в глобальный `data/`.

#### Риски 5b

| Риск | Mitigation |
|------|------------|
| Спам-регистрации | `REGISTRATION_OPEN=false` по умолчанию на prod; rate limit; позже captcha |
| Снятие Basic Auth до готового login | 5b.5 после 5b.1 ✅ и желательно после 5b.4 (Settings) |
| Несколько Garmin-аккаунтов | Не использовать общий `GARMIN_*` в `.env`; per-user cookies в **5b.4** |
| Много пользователей + частый Playwright refresh | Последовательный цикл refresh; при росте — очередь/лимиты (post-5b) |
| Смена email | UNIQUE + понятная ошибка |
| HH OAuth без привязки к сессии | signed `state` в callback |

**Не переписывать:** `user_id` в store/sync, `data/users/{id}/`, webhook routing, per-user JWT refresh (HTTP → Playwright fallback).

**Документация:** детали upload/JWT — [API_GARMIN.md](API_GARMIN.md); runtime — [ARCHITECTURE.md](ARCHITECTURE.md) (обновить схему `data/users/{id}/` при 5b.4).

См. **[UI: Новый интерфейс приложения](#ui-новый-интерфейс-приложения)** и [UI.md](UI.md).

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
- Re-sync / force с подтверждением — ✅ в `/app` (дашборд + activities, bulk errors)

Админ-раздел (`/app/admin`) — без календаря райдеров (таблица пользователей + лог); общий shell с кабинетом (после 5b).

**Оценка календарь + поиск:** ~1 вечер (SQLite aggregate + шаблон); +0.5 вечера с HTMX и полировкой.

---

### Фаза 6.2: Локализация (i18n/l10n)

**Цель:** интерфейс кабинета и админки на нескольких языках; даты/числа — по `timezone` + `locale` пользователя.

**Когда:** после **[UI](#ui-новый-интерфейс-приложения)** ✅ и основных экранов **6** — иначе дважды выносить строки из шаблонов.

#### Языки (приоритет)

| Этап | Языки | Примечание |
|------|--------|------------|
| **6.2.0** | `ru` (default), `en` | Покрыть весь `/app` + `/app/admin` |
| **6.2.1+** | `de`, `fr`, `es`, … | По запросу; тот же механизм каталогов |
| Вне scope v1 | CLI, `docs/`, логи сервера | Остаются EN или RU как сейчас |

#### Хранение и выбор языка

| Источник | Поведение |
|----------|-----------|
| **Профиль** | `users.locale` (`ru` / `en` / …) — главный источник для залогиненного UI |
| **Настройки** | `/app/settings` → выпадающий список языка (рядом с timezone) |
| **Регистрация** | **5b.3:** опционально выбор языка; иначе `Accept-Language` браузера → fallback `ru` |
| **Гость** | `Accept-Language` на `/login`, `/register`; cookie `fit_sinc_lang` на 14 дней |
| **Админ** | Тот же `locale` что у пользователя-оператора (не отдельный «язык админки») |

#### Техника (рекомендация)

```text
fit_sinc/locale/
  ru.json          # или ru/LC_MESSAGES/messages.po (gettext)
  en.json
fit_sinc/web/i18n.py   # t("nav.dashboard", locale=...) → str
```

| Вариант | Плюсы | Минусы |
|---------|--------|--------|
| **JSON-каталоги** + `t(key)` | Просто, без Babel, удобно в Jinja `{{ t('…') }}` | Нет plural/forms без доп. логики |
| **gettext (Babel)** | Стандарт, plural, `pybabel extract` | Тяжелее CI, `.po` для редакторов |

**Рекомендация для fit_sinc:** JSON + ключи `section.item` на старте; при росте — миграция на gettext.

**Jinja2:** все пользовательские строки в шаблонах (`layouts/app.html`, страницы `/app`, `/app/admin`); в Python — только `t()` для flash/ошибок валидации.

**Даты:** `timeutil` / `babel.dates` — формат по `user.timezone` + `user.locale` (не хардкод «MSK» в подписи).

#### Объём перевода (чеклист)

- Nav: Dashboard, Activities, Sync log, Garmin session, Settings, Admin, Logout
- Login / register / ошибки auth
- Dashboard: connections, статусы sync, кнопки re-sync
- Activities: фильтры, календарь, таблица
- Admin: users CRUD, promote/disable
- Telegram/email шаблоны (**6.1**) — отдельные ключи `alerts.*`

#### Подфазы

| Подфаза | Содержание | Оценка |
|---------|------------|--------|
| **6.2.0** | `locale` в БД, миграция `default` → `ru`; `t()` + `ru.json` / `en.json` | ½ дня |
| **6.2.1** | Перенос строк из `html.py` / `app_routes` в каталоги; Jinja filter `t` | 1–2 вечера |
| **6.2.2** | Выбор языка в settings + cookie для гостя; `lang` в `<html>` | ½ вечера |
| **6.2.3** | Тесты: `t()` fallback, страница login с `Accept-Language: en` | ½ вечера |

**Порядок:** **[UI](#ui-новый-интерфейс-приложения)** ✅ → **6.2.0–6.2.1** (можно параллельно с календарём **6**) → **6.2.2** вместе с **5b.4** settings.

#### UX

- Переключатель языка в шапке (рядом с user bar) **или** только в Settings — решить в **5b.4** / **6.2** (не дублировать везде).
- Непереведённый ключ → показывать ключ в dev, fallback на `ru` в prod + лог warning.

#### Вне scope

- Автоперевод API (DeepL) для имён активностей с Hammerhead/Garmin
- RTL (арабский) — только если явный запрос
- Локализация README/docs на сайте — отдельно от приложения

---

### Надёжность и ops

> **Не путать с Фазой 5 (tenants).** Здесь — меньше сюрпризов ночью и порядок в репозитории.

| Задача | Фаза | Статус | Зависимости |
|--------|------|--------|-------------|
| Smoke-тесты в CI (`compileall`, unittest) | 4 | ✅ | — |
| README на GitHub | ops | ✅ | — |
| Тесты: webhook HMAC endpoint, `sync_activity` с моками HH/Garmin | ops | ✅ | webhook, tenant, /app login, sync skip |
| **Баннер статуса** на дашборде | 6 | 📋 | лучше после 5 (`/app`) |
| **Очередь failed** — фильтр `status=error`, retry | 6 | 📋 | retry уже в коде |
| Понятный sync log (`duplicate` ≠ error) | 6 | 📋 | — |
| **Алерты Telegram** при `sync_status=error` или N ошибок подряд | **6.1** | 📋 | поле `telegram` из Фазы 5 |
| Email-алерты | 6.1+ | 📋 | опционально |

**Порядок:** Фаза **5** ✅ → **5b** (+ **UI** ✅) → Фаза **6** (календарь, баннер, failed) → **6.2** (i18n) → **6.1** (бот).

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
| 5 tenants + admin (MVP) | — | ✅ |
| **UI** новый интерфейс (Jinja2 + Tailwind) | 5 | ✅ |
| **5b** единый кабинет, регистрация, settings, nginx | 5, UI | 2–4 вечера (5b.0–5b.1, UI ✅) |
| 6 UI v2 (календарь, поиск, баннер, failed) | 5b, UI | 2–3 дня |
| 6.1 алерты Telegram | 5, 6 | 0.5–1 день |
| **6.2** локализация (ru/en + `users.locale`) | UI, 6 | 2–3 вечера |
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
- [x] CI: GitHub Actions [`test.yml`](../.github/workflows/test.yml) + [`deploy.yml`](../.github/workflows/deploy.yml), smoke tests
- [x] **UI:** новый интерфейс приложения (Jinja2 + Tailwind, `/app` + `/app/admin`) — [UI.md](UI.md)
- [x] **5b.2 (часть):** user bar, форма пользователя, IANA timezone select, тесты auth/admin form → см. **UI** выше
- [x] Secret `SSH_PRIVATE_KEY` в GitHub
- [x] README GitHub + разделение docs (ARCHITECTURE / PLAN)
- [x] Push в `main` → https://github.com/segallar/fit-sinc
- [x] UI: re-sync в кабинете (Re-sync, force + confirm, retry all errors, redirect `next`)

### Roadmap v2 (план)

- [x] Фаза 5: tenants, `user_id` в БД, webhook → user, `data/users/{id}/`
- [x] Фаза 5: CRUD users (email, telegram, timezone, password, HH id) — сейчас `/app/admin`
- [x] Фаза 5: `/app` — login email+password, сессия, UI в TZ пользователя
- [x] **Фаза 5b.0:** `is_admin`, bootstrap, `REGISTRATION_OPEN`, CLI `promote-admin` — [5b-DECISIONS.md](5b-DECISIONS.md)
- [x] **Фаза 5b.1:** один логин, `/app/admin/*`, убрать `/admin/login` + `ADMIN_PASSWORD`
- [ ] **Фаза 5b.2:** пункт **Settings** в nav (страница — 5b.4)
- [ ] **Фаза 5b.3:** `/register` + `REGISTRATION_OPEN`
- [ ] **Фаза 5b.4:** `/app/settings` — профиль, пароль, Hammerhead/Garmin (приоритет)
- [ ] **Фаза 5b.5:** nginx без Basic Auth; `https_only` cookie
- [ ] **Фаза 5b.6:** тесты register/settings/admin guard
- [ ] Docs: ARCHITECTURE — multi-tenant `data/users/{id}/`, без глобального `data/garmin_web`
- [ ] Фаза 6: календарь + поиск на `/app/activities`, баннер, failed, лог
- [ ] Фаза 6.1: Telegram-алерты при ошибках sync
- [ ] **Фаза 6.2.0:** `users.locale`, каталоги `ru` / `en`, функция `t()`
- [ ] **Фаза 6.2.1:** перевести `/app` и `/app/admin` (Jinja + html.py)
- [ ] **Фаза 6.2.2:** выбор языка в settings, cookie / Accept-Language для гостя
- [x] Ops: расширить smoke (webhook endpoint, tenant routing, /app login, sync skip)
- [ ] Фаза 7: абстракция Source/Sink, manual FIT
- [ ] Фаза 8: spike routes / Garmin courses
