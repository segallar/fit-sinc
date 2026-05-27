# GetSync — UI приложения (единая спецификация)

> **Создано:** 2026-05-26 · **Обновлено:** 2026-05-28 (topbar, calendar default) · **Версия:** 0.7.0  
> **Назначение:** один документ для всех страниц `/app` и `/app/admin` — layout, компоненты, плотность, поведение.  
> **Roadmap:** [PLAN.md](PLAN.md) **2.10** · **Стек:** [UI.md](UI.md) · **Карта URL / flows:** [design/SCREENS.md](design/SCREENS.md)

**Статус (2026-05-26):** **функциональная IA и 2.3** в prod (`cabinet.html`, nav-pills) — Activities (List/Calendar + sync summary), Settings connections, Admin sync log (все tenants). Dashboard снят. 🔄 **2.10** sidebar · **2.5** i18n. Снимок — [PLAN.md § снимок кабинета](PLAN.md#снимок-кабинета-app).

---

## 1. Принятые решения (Q&A, 2026-05)

| Тема | Решение |
|------|---------|
| **Визуал** | Та же **mint**-палитра, что лендинг ([`tokens.css`](../getsync/web/static/tokens.css)), но кабинет **плотнее** («рабочий» SaaS: меньше воздуха, чётче таблицы) |
| **Навигация** | **Боковое меню** слева (desktop); на mobile — collapse / offcanvas |
| **Первая волна** | Пакетом: **Activities + Settings + Admin** |
| **Scope v1** | `/app/*` + `/app/admin/*` в **одном** стиле |
| **i18n** | Сначала **EN**-вёрстка и тексты в шаблонах; перевод **2.5** отдельным проходом |
| **Login/register** | Пока `site_auth` (как лендинг); выравнивание с app — после v1 кабинета |

### Блок 2 (зафиксировано)

| Тема | Решение |
|------|---------|
| **Topbar** | Nav: только **Activities**. **Settings** — иконка шестерёнки между user и Logout. **Admin** — зелёный pill справа (только `is_admin`), не в nav |
| **Activities default** | **`view=calendar`** при открытии `/app/activities` без query; вкладки: Calendar \| List |
| **HH / Garmin** | **Только Settings** → `?section=hammerhead|garmin` (+ `#garmin-session` на Garmin) — **нет** banner на Activities |
| **Activities** | **Главный экран**; List \| Calendar; unified HH+Garmin; внизу **sync summary** + retry errors (без таблицы лога) |
| **Sync log** | **Только admin** → `/app/admin/sync-log` (все tenants, колонка User); legacy `/app/log` → redirect |
| **Dashboard** | **Снят** — `/app/` → `/app/activities` |
| **Settings** | Одна страница `/app/settings?section=…` — слева subnav: Profile · Connections (подменю по системам) · Password ✅ |
| **Garmin login** | Status/refresh в карточке Garmin; **первичный login** — CLI (**2.12** 📋 UI в Connections) |
| **Ширина кабинета** | **На всю ширину viewport**, контент **прижат к левому краю** — без `max-width` и без `margin: auto` по центру (`getsync-app-main` в [`app.css`](../getsync/web/static/app.css)). Лендинг и `/app/login` — отдельно (узкая колонка допустима). |
| **Calendar view** | Сетка месяца дополнительно **растягивается по высоте** доступной области (`getsync-app-main--activities-calendar`). |

---

## 2. Зоны продукта

| Зона | URL | Layout | Спецификация |
|------|-----|--------|--------------|
| Лендинг | `/` | `site.html` | Отдельно; общие **tokens** |
| Auth | `/register`, `/app/login` | `site_auth.html` | Позже подтянуть к app |
| **Приложение** | `/app/*` | `cabinet.html` → **sidebar** | **Этот документ** |
| **Админка** | `/app/admin/*` | тот же `cabinet.html` | Те же компоненты + таблицы |

```text
┌──────────────────────────────────────────────────────────────────┐
│ [ico] GetSync   Activities          user  [Admin]  ⚙  Logout      │
├──────────────────────────────────────────────────────────────────┤
│  page_header · main content (full width, left-aligned)              │
└──────────────────────────────────────────────────────────────────┘
```

**Сейчас в коде** ([`app_topbar.html`](../getsync/web/templates/components/app_topbar.html), [`cabinet.py`](../getsync/web/cabinet.py)): topbar · nav **только Activities** · Settings (`settings_href`) — **иконка** ⚙ · Admin — **pill** `.getsync-topbar-admin-pill` (зелёный). **Main:** full width, left edge (см. §1 «Ширина кабинета»).

| URL legacy | Куда |
|------------|------|
| `/app/` | `303` → `/app/activities` |
| `/app/log` | `303` → `/app/admin/sync-log` |
| `/app/session` | `303` → `/settings?section=garmin#garmin-session` |

HH/Garmin — **Settings → подменю Connections** (отдельный `section` на интеграцию); монитор сессии Garmin — **`#garmin-session`** на `section=garmin`.

**Целевой layout (2.10):** sidebar `.getsync-sidebar` · прототип — [`/app/ui-preview`](../getsync/web/app_routes.py) + `layouts/cabinet_sidebar.html`.

### Локальный цикл (без деплоя на сервер)

1. Запустить приложение на машине разработчика (ниже).
2. Согласовать вёрстку на **`/app/ui-preview`** — правки только в `templates/`, `static/app.css`, `tokens.css`.
3. Когда макет ок — перенести layout на остальные страницы (`cabinet.html` → `cabinet_sidebar.html`).
4. **Деплой на sirocco** — только после того, как весь кабинет на новом shell и прогнаны тесты; до этого prod остаётся на старых pills.

```bash
cd /path/to/getsync

# один раз: виртуальное окружение (на macOS Homebrew pip в систему не ставит)
python3 -m venv .venv
source .venv/bin/activate

python3 -m pip install -e .
python3 -m uvicorn getsync.web.app:app --reload --port 8080
```

Если `pip: command not found` — нормально: после `source .venv/bin/activate` есть `pip`, либо всегда `python3 -m pip`.  
Если порт 8080 занят: `--port 8081` и открывать `http://127.0.0.1:8081/...`.

| URL | Назначение |
|-----|------------|
| http://127.0.0.1:8080/app/login | Вход (нужна сессия) |
| http://127.0.0.1:8080/app/ui-preview | **Прототип** sidebar + Settings |
| http://127.0.0.1:8080/app/settings | Текущий prod-layout (для сравнения) |

Пользователь для входа: bootstrap из `.env` / `getsync user create` / тестовый из `ensure_default_user` при первом старте с пустой БД.

---

## 3. Design tokens (не дублировать в шаблонах)

Источник: [`getsync/web/static/tokens.css`](../getsync/web/static/tokens.css).

| Token | Значение / роль |
|-------|-----------------|
| `--getsync-primary-600` | Primary buttons, active nav |
| `--getsync-primary-700` | Links, labels |
| `--getsync-primary-50/100` | Subtle backgrounds, borders |
| `--getsync-text` / `--getsync-text-muted` | Body / secondary text |
| `--getsync-surface` / `--getsync-surface-muted` | Cards, filter panels |
| `--getsync-status-*` | synced / error / pending / neutral |
| `--getsync-radius-md` | Cards, inputs (0.75rem) |
| `--getsync-page-max` | Узкая колонка только **site / auth**; кабинет `/app` — **не** использует |

**Плотность кабинета (дополнить в `app.css` при редизайне):**

| Элемент | Marketing (site) | App (dense) |
|---------|------------------|-------------|
| Card body padding | `1.25rem 1.375rem` | `1rem 1.125rem` |
| Table | — | `table-sm`, `table-hover` |
| Page header margin | `mb-3` | `mb-2` |
| Form controls | default | `form-control-sm` где уместно |
| Section gap | `g-4` | `g-3` |

Не использовать inline `color:` / hex в HTML — только Bootstrap + CSS variables.

---

## 4. Типографика

| Уровень | Класс | Где |
|---------|-------|-----|
| Заголовок страницы | `h4 fw-semibold` | `page_header` → один **h1** на страницу |
| Заголовок карточки | `h5 mb-0` или `h6` | `.card-header` |
| Подзаголовок секции (Settings) | `.getsync-settings-heading` | `0.9rem`, как пункты subnav |
| Подзаголовок секции (прочее) | `h6 text-primary mb-3` | Cards вне Settings |
| Lead / meta | `small text-muted` | Под заголовком, под таблицей |
| ID / время | `font-monospace small` | activity_id, log time |
| Код | `<code>` | slug, CLI hints |

---

## 5. Компоненты (обязательные)

Все страницы `/app` собираются из этого набора — **не копировать** разметку card/header вручную.

| Компонент | Файл | Правило |
|-----------|------|---------|
| **Sidebar** | `components/app_sidebar.html` *(цель)* | Единственная навигация; `active` по `active_nav` |
| **Page header** | `components/page_header.html` | `title` + опционально `lead_html` |
| **Flash** | `components/flash.html` | Уже в `cabinet.html` под main |
| **User block** | внизу `app_sidebar.html` | email, slug, Logout; убрать `user_bar.html` с страниц |
| **Data card** | класс `.getsync-data-card` | Таблицы: header + `table-responsive` |
| **Activities tabs** | `components/activities_tabs.html` | List \| Calendar; сохраняет фильтры в query |
| **Activity calendar** | `components/activity_calendar.html` | `view=calendar`; SQLite aggregate; клик дня → `view=list&date_from=&date_to=` |
| **Filter card** | класс `.getsync-filter-card` | Под вкладками; на Calendar — только **source** (+ hidden year/month) |
| **Sync summary** | `components/activities_sync_panel.html` | Activities: counts, errors link, bulk retry |
| **Sync log** | `components/sync_log_section.html` | Admin `/app/admin/sync-log` (`show_user_column`) |
| **Connection card** | `components/connection_card.html` | Settings → sources / destinations |
| **Garmin session** | `components/garmin_session_section.html` | Settings `#garmin-session` (внутри Connections) |
| **Status badge** | `status_badge` macro | Только macro для sync status |
| **Connections** | секция в Settings | HH OAuth + Garmin status/login |
| **Settings subnav** | `components/settings_subnav.html` | Белая карточка (`surface` + shadow); справа у пункта — `settings_nav_icon.html` |
| **Topbar actions** | `app_topbar.html` | Admin pill · Settings gear · Logout |
| **Settings form row** | `components/settings_form_macros.html` → `settings_field` | Label и control **в одну строку** (`col-sm-4` / `col-sm-8`, `form-control-sm`) |
| **Re-sync** | `resync_form.html` | POST + confirm для force |
| **Pager** | `pager.html` | Log, activities |
| **Datetime** | `datetime_cell.html` | TZ пользователя |
| **Selects** | `timezone_select`, `locale_select` | Settings, admin form |
| **Build footer** | `build_footer.html` | В `base.html` footer |

### Кнопки

| Действие | Класс |
|----------|-------|
| Primary (Save, Connect, Filter) | `btn btn-primary` (+ `btn-sm` в таблицах) |
| Secondary (Reset, Cancel) | `btn btn-outline-secondary btn-sm` |
| Destructive (Disconnect, Delete) | `btn btn-outline-danger btn-sm` + `confirm()` |
| Link action | `btn btn-link` или обычный `<a>` |

### Таблицы

```html
<div class="card getsync-data-card shadow-sm">
  <div class="card-header">…</div>
  <div class="table-responsive">
    <table class="table table-hover table-sm mb-0 align-middle">
      <thead class="table-light">…</thead>
      <tbody>…</tbody>
    </table>
  </div>
</div>
```

Пустое состояние: одна строка `text-center text-muted py-4`.

### Alerts

| Тип | Класс |
|-----|-------|
| Success (flash, saved) | `alert alert-success` |
| Error | `alert alert-danger` |
| Warning (not connected) | `alert alert-warning` |
| Info | `alert alert-info` |

---

## 6. Спецификация по страницам

### 6.1 Activities — `/app/activities` (основной экран) ✅

| Блок | Содержание |
|------|------------|
| Header | Sub-header: title, date/type dropdowns, view toggle List \| Calendar \| Map |
| **Tabs** | **Calendar** (default) \| **List** — `activities_tabs.html`; без `view` → `calendar` |
| Filters | List: source, `q`, status, type, date_from/to, per_page · Calendar: **source** only |
| **Calendar view** | `?view=calendar&year=&month=` — сетка месяца, worst status, счётчик; ‹ › Today |
| **List view** | `?view=list` — meta, table, pager |
| Table | **Source** (badge), Date, Name, Type, Distance, Duration, GetSync, Linked, Actions |
| Pager | `pager.html` (только List) |
| **Sync summary** | Строка внизу: HH sync counts, catalog total, link errors, «Re-sync all errors» | `activities_sync_panel.html` |

**Нет** таблицы sync log на этой странице — журнал в admin.

**Query (основное):**

| Параметр | List | Calendar |
|----------|------|----------|
| `view` | `list` | `calendar` (default) |
| `source` | all / hammerhead / garmin | то же |
| `q`, `status`, `activity_type`, `date_from`, `date_to`, `page`, `per_page` | ✅ | скрыты (кроме source) |
| `year`, `month` | — | текущий или из URL |

**Клик по дню в календаре** → `view=list&date_from=YYYY-MM-DD&date_to=YYYY-MM-DD` (фильтры source сохраняются).

**Данные:**

- **Список:** merge HH+Garmin API — [`browse.py`](../getsync/activities/browse.py); дедуп; сортировка по дате.
- **Каталог SQLite:** PK `(user_id, source, activity_id)`; `persist_browse_rows()` при browse — [`catalog.py`](../getsync/activities/catalog.py).
- **Календарь:** агрегат `activity_date` + `sync_status` из SQLite — [`calendar.py`](../getsync/activities/calendar.py). Дни «только в облаке» без записи в БД — **не** в v1 (см. PLAN 2.3 v6.1).
- **FIT:** `storage_key` → [STORAGE.md](STORAGE.md).

Вкладок Hammerhead/Garmin **нет** — `source` обычная колонка и фильтр.

### 6.2 Settings — `/app/settings` ✅

Одна страница, **без прокрутки всех блоков сразу**: слева subnav, справа **одна** секция по query `section`.

#### Layout

```text
┌─────────────────┬──────────────────────────────────────┐
│ Profile         │  [заголовок секции .getsync-settings-heading]
│ CONNECTIONS     │  label ───────────── input (одна строка)
│   Hammerhead    │  …
│   Garmin Connect│
│   Strava        │
│   Wahoo         │
│ Password        │
└─────────────────┴──────────────────────────────────────┘
```

| Класс / token | Значение |
|---------------|----------|
| Subnav link | `font-size: 0.9rem` — `.getsync-settings-nav-list .nav-link`; фон **белый** + border primary-100 + shadow (не сливаться с `bg-light`) |
| Subnav icon | справа — `.getsync-settings-nav-icon` 18×18, **цветные** по провайдеру |
| Connections | `<details>` — клик по заголовку раскрывает подменю; `open` если активна интеграция |
| Active nav item | `primary-50` фон + тёмный текст (без полоски слева) |
| Settings gear | `icons/settings_gear.html` — классическая 6-зубая шестерёнка outline |
| Панель + поля | `0.9rem` — `.getsync-settings-panel`, `.getsync-settings-label`, controls |
| Заголовок секции | `.getsync-settings-heading` — тот же размер, `font-weight: 500`, primary-700 |

#### Query `section`

| `section` | Содержание |
|-----------|------------|
| `profile` (default) | display_name, email, telegram, locale, timezone, slug — горизонтальные строки, Save |
| `hammerhead` | Карточка Hammerhead (`connection_card.html`) |
| `garmin` | Карточка Garmin + **`#garmin-session`** (`garmin_session_section.html`) |
| `strava`, `wahoo` | Planned — карточка disabled |
| `password` | current, new, confirm — горизонтальные строки |

Legacy: `?section=connections` → **`hammerhead`**.  
Редиректы после OAuth/refresh/disconnect — на соответствующий `section` (HH → `hammerhead`, Garmin → `garmin`).

Модель соединений: [CONNECTIONS.md](CONNECTIONS.md) · список для subnav: `list_connections()` в [`connections.py`](../getsync/web/connections.py).

**Garmin:** status/refresh/disconnect в карточке; **первичный login** — CLI (**2.12** 📋).

### 6.3 Sync log — Admin `/app/admin/sync-log` ✅

| Блок | Содержание |
|------|------------|
| Subnav | Users · **Sync log** · Garmin log — `admin_subnav.html` |
| Заголовок | «Sync log», lead: все tenants |
| Table | Time, **User**, Event, Activity, Message — `sync_log_section.html` |
| Pager | `/app/admin/sync-log?log_page=N#sync-log` |

Данные: `sync_events` в SQLite, `list_events(user_id=None)` — общий журнал.  
Legacy `/app/log` → **303** сюда (нужен `is_admin`). **Осталось (2.14 📋):** фильтры duplicate vs error — [SCREENS.md](design/SCREENS.md).

### 6.4 Admin — `/app/admin/`

Тот же sidebar + **Admin** section.

#### Users list

| Элемент | Стиль |
|---------|-------|
| Header | `page_header` + primary «New user» `btn-sm` |
| Table | users table `getsync-data-card` |

#### User form (new/edit)

| Секция | Поля |
|--------|------|
| Account | slug, display_name, email, password (new), locale, timezone |
| Contacts | telegram |
| Hammerhead | hammerhead_user_id |
| Access | is_admin, disabled |

Legends: `h6 text-primary` — как в settings.

#### Garmin JWT log — `/app/admin/log`

Таблица refresh-событий JWT для всех аккаунтов — `garmin_refresh_log_table.html` (не путать с sync log).

### 6.5 Forbidden — `/app/forbidden` (403)

Минимальная card по центру; те же tokens; ссылка на `/app/activities`.

---

## 7. Состояния и статусы

### Sync status (badge)

| status | CSS class | Bootstrap fallback |
|--------|-----------|-------------------|
| synced | `getsync-badge--synced` | green |
| error | `getsync-badge--error` | red |
| pending | `getsync-badge--pending` | yellow |
| not synced / skipped | `getsync-badge--neutral` | gray |

### Connection status (text)

| State | Класс |
|-------|-------|
| OK | `text-success` + `fw-medium` |
| Warning (not connected) | `text-warning` |
| Error | `text-danger` |

---

## 8. Responsive

| Breakpoint | Поведение |
|------------|-----------|
| `< md` | Sidebar → offcanvas / hamburger; таблицы в `table-responsive` |
| `≥ md` | Settings: колонка subnav + панель; `< md` — subnav горизонтально сверху |
| `≥ lg` | Activities: calendar grid 7 col, list filters 2–3 col |
| Touch | Кнопки в actions не менее ~44px height где primary CTA |

---

## 9. Доступность

- Один `h1` на страницу (`page_header`)
- `aria-label` на nav («Cabinet», «Admin»)
- Focus: Bootstrap focus ring через `--bs-focus-ring-color`
- `lang` на `<html>` из `user.locale` / `lang` в cabinet
- Confirm на destructive и force re-sync
- Таблицы: `<th scope="col">`

---

## 10. i18n (порядок работ)

1. **Редизайн v1:** строки на **английском** в шаблоне или `app_i18n.py` (`cabinet_strings`)
2. **2.5:** вынести hardcoded (activities list+calendar, sync summary, admin sync log, connections, admin)
3. Не смешивать языки на одной странице

Уже в i18n: nav, settings (часть), login/register.

---

## 11. Реализация (чеклист)

### Layout **2.10.2a**

- [x] `app_sidebar.html` + `cabinet_sidebar.html` — прототип на **`GET /app/ui-preview`**
- [ ] Переключить `cabinet.html` → sidebar (убрать pills)
- [ ] Убрать дубли: `app_header` + `app_nav` pills → sidebar
- [ ] CSS: `.getsync-sidebar`, collapse mobile

### Функциональность **2.3** (логика без sidebar-редизайна)

- [x] Activities — unified list (HH+Garmin), SQLite catalog, re-sync
- [x] Activities — вкладки List \| Calendar, `activity_calendar.html`
- [x] Sync log в admin (`/app/admin/sync-log`, все tenants); `/app/log` redirect
- [x] Activities — sync summary (`activities_sync_panel`); Dashboard снят; `/app/` → activities
- [x] Settings — subnav + подменю по интеграциям (`?section=`), inline form rows, 0.9rem; Garmin session на `section=garmin`; `/app/session` redirect
- [ ] Sync log — UX duplicate vs error (фильтры / badge по типу события)
- [ ] Calendar v6.1 — дни только в облаке (опционально)

### Страницы **2.10.2b** (визуал, один PR / волна)

- [ ] Settings — sidebar shell; **Garmin login UI** (**2.12**)
- [ ] Activities — sidebar + calendar CSS polish
- [ ] Admin users + user form

### Полировка **2.10.3**

- [ ] Focus / contrast pass
- [ ] Admin mobile tables
- [ ] Auth pages alignment (optional)

---

## 12. Ссылки на код

| Артефакт | Путь |
|----------|------|
| Tokens | `getsync/web/static/tokens.css` |
| Theme (+ `.getsync-cal-*`) | `getsync/web/static/app.css` |
| Layout | `getsync/web/templates/layouts/cabinet.html` |
| Routes | `getsync/web/app_routes.py` — `view=list\|calendar` |
| Browse / catalog / calendar | `getsync/activities/browse.py`, `catalog.py`, `calendar.py` |
| Connections | `getsync/web/connections.py` |
| Strings | `getsync/web/app_i18n.py` |
| Render | `getsync/web/cabinet.py` → `render_cabinet()` |

**Новая страница `/app`:**

1. `extends layouts/cabinet.html`
2. `{% block page_content %}` — только `page_header` + cards/tables из §5–6
3. `render_cabinet(..., active="/app/…")`
4. Проверить по чеклисту §11

---

## История решений

| Дата | Изменение |
|------|-----------|
| 2026-05-26 | Документ создан; Q&A блок 1 |
| 2026-05-26 | Q&A блок 2: sidebar+user, connections только Settings, calendar+activities, settings anchors, Garmin UI v1 |
| 2026-05-26 | Dashboard снят; sync log → admin; Activities sync summary; List/Calendar; connections+garmin-session |
| 2026-05-27 | Settings: subnav 0.9rem, подменю по интеграциям (`section=hammerhead|garmin|…`), горизонтальные form rows |
| 2026-05-28 | Activities default Calendar; topbar Admin pill + Settings gear; settings subnav контраст + иконки |
