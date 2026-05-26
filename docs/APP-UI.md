# GetSync — UI приложения (единая спецификация)

> **Назначение:** один документ для всех страниц `/app` и `/app/admin` — layout, компоненты, плотность, поведение.  
> **Roadmap:** [PLAN.md](PLAN.md) **2.10** · **Стек:** [UI.md](UI.md) · **Карта URL / flows:** [design/SCREENS.md](design/SCREENS.md)

**Статус (2026-05-26):** **функциональная IA и 2.3** в prod-layout (`cabinet.html`, nav-pills) — unified Activities, вкладки List/Calendar, dashboard sync log, Settings connections. 🔄 визуальный редизайн (**2.10**, sidebar) и i18n тел страниц (**2.5**). Снимок IA — [PLAN.md § снимок кабинета](PLAN.md#снимок-кабинета-app).

---

## 1. Принятые решения (Q&A, 2026-05)

| Тема | Решение |
|------|---------|
| **Визуал** | Та же **mint**-палитра, что лендинг ([`tokens.css`](../getsync/web/static/tokens.css)), но кабинет **плотнее** («рабочий» SaaS: меньше воздуха, чётче таблицы) |
| **Навигация** | **Боковое меню** слева (desktop); на mobile — collapse / offcanvas |
| **Первая волна** | Пакетом: **Dashboard + Settings + Activities** |
| **Scope v1** | `/app/*` + `/app/admin/*` в **одном** стиле |
| **i18n** | Сначала **EN**-вёрстка и тексты в шаблонах; перевод **2.5** отдельным проходом |
| **Login/register** | Пока `site_auth` (как лендинг); выравнивание с app — после v1 кабинета |

### Блок 2 (зафиксировано)

| Тема | Решение |
|------|---------|
| **Sidebar** | Пункты nav + внизу **блок user** (display/email, slug, Logout). Пункт **Admin** в nav только если `is_admin` |
| **HH / Garmin** | **Только Settings** → `#connections` (+ `#garmin-session` внутри) — **нет** `connections_banner` на dashboard |
| **Activities** | **Главный экран**; вкладки **List \| Calendar** (`?view=`); unified HH+Garmin; календарь ✅ **2.3** |
| **Dashboard** | Сводка sync + CTA на Activities; **sync log** внизу (`#sync-log`); отдельного `/app/log` нет |
| **Settings** | Одна страница: `#profile` · `#connections` · `#password` — `settings_subnav.html` ✅ |
| **Garmin login** | Status/refresh в карточке Garmin; **первичный login** — CLI (**2.12** 📋 UI в Connections) |

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
│ [ico] GetSync   Activities  Dashboard  Settings   [Admin]  user  │
├──────────────────────────────────────────────────────────────────┤
│  page_header · main content                                       │
└──────────────────────────────────────────────────────────────────┘
```

**Сейчас в коде** ([`cabinet.py`](../getsync/web/cabinet.py)): nav-pills + `app_header` · порядок: **Activities** → Dashboard → Settings · Admin — если `is_admin`.

| URL legacy | Куда |
|------------|------|
| `/app/log` | `303` → `/?#sync-log` |
| `/app/session` | `303` → `/settings#garmin-session` |

HH/Garmin — **Settings → Connections**; монитор сессии — **`#garmin-session`** под карточками destinations.

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
| `--getsync-page-max` | Max width main column (64rem) |

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
| Подзаголовок секции | `h6 text-primary mb-3` | Внутри card (Settings) |
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
| **Sync log** | `components/sync_log_section.html` | Только на dashboard `#sync-log` |
| **Connection card** | `components/connection_card.html` | Settings → sources / destinations |
| **Garmin session** | `components/garmin_session_section.html` | Settings `#garmin-session` (внутри Connections) |
| **Status badge** | `status_badge` macro | Только macro для sync status |
| **Connections** | секция в Settings | HH OAuth + Garmin status/login; **не** на dashboard |
| **Settings subnav** | `components/settings_subnav.html` *(цель)* | Якоря Profile \| Connections \| Password |
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

### 6.1 Dashboard — `/app/`

| Блок | Содержание | Компоненты |
|------|------------|------------|
| Header | Title «Dashboard», lead: sync summary + ссылка на **Activities** + errors | `page_header` |
| Actions | «Re-sync all errors (N)» если `error_count` | `btn-outline-secondary btn-sm` |
| Main | Карточка sync status (SQLite counts) + CTA «Open activities» | `getsync-data-card` |
| **Sync log** | Секция `#sync-log` внизу: таблица событий + pager `?log_page=` | `sync_log_section.html` |
| Footer meta | `Updated … · TZ …` | `small text-muted` |

**Нет** таблицы активностей и **нет** `connections_banner` — полный каталог на Activities. Отдельного пункта меню «Sync log» **нет**; `/app/log` → redirect на dashboard.

### 6.2 Activities — `/app/activities` (основной экран) ✅

| Блок | Содержание |
|------|------------|
| Header | Title, lead («all sources»), optional «Show errors only» |
| **Tabs** | **List** (default) \| **Calendar** — `activities_tabs.html` |
| Filters | List: source, `q`, status, type, date_from/to, per_page · Calendar: **source** only |
| **Calendar view** | `?view=calendar&year=&month=` — сетка месяца, worst status, счётчик; ‹ › Today |
| **List view** | `?view=list` — meta, table, pager |
| Table | **Source** (badge), Date, Name, Type, Distance, Duration, GetSync, Linked, Actions |
| Pager | `pager.html` (только List) |

**Query (основное):**

| Параметр | List | Calendar |
|----------|------|----------|
| `view` | `list` (default) | `calendar` |
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

### 6.3 Settings — `/app/settings` ✅

Одна прокручиваемая страница · subnav: Profile \| Connections \| Password.

| Секция | id | Содержание |
|--------|-----|------------|
| **Profile** | `profile` | display_name, email, telegram, locale, timezone, slug, Save |
| **Connections** | `connections` | Sources + Destinations — `list_connections()` → `connection_card.html`; Strava/Wahoo planned; «Add connection» disabled |
| **Garmin session** | `garmin-session` | Внутри Connections: upload_ready, refresh history, POST refresh — `garmin_session_section.html` |
| **Password** | `password` | current, new, confirm |

Модель соединений: [CONNECTIONS.md](CONNECTIONS.md) · код: [`connections.py`](../getsync/web/connections.py).

**Garmin:** status/refresh/disconnect в карточке destination; **первичный login** — CLI (**2.12** 📋).

### 6.4 Sync log — на Dashboard (`#sync-log`) ✅

| Блок | Содержание |
|------|------------|
| Заголовок | «Sync log», `log_range_label` |
| Table | Time, Event, Activity, Message — `table-sm` |
| Pager | `/?log_page=N#sync-log` — Prev / Next |

Legacy `/app/log` → **303** на `/?#sync-log`. **Осталось (2.3 📋):** стили/фильтры duplicate vs error — [SCREENS.md](design/SCREENS.md).

### 6.5 Admin — `/app/admin/`

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

### 6.6 Forbidden — `/app/forbidden` (403)

Минимальная card по центру; те же tokens; ссылка на `/app/`.

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
| `≥ lg` | Settings: subnav + секции; activities: calendar grid 7 col, list filters 2–3 col |
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
2. **2.5:** вынести hardcoded (dashboard, activities list+calendar, sync log, connections, admin)
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
- [x] Dashboard — sync log section; `/app/log` redirect
- [x] Settings — connections list, `#garmin-session`; `/app/session` redirect
- [ ] Sync log — UX duplicate vs error (фильтры / badge по типу события)
- [ ] Calendar v6.1 — дни только в облаке (опционально)

### Страницы **2.10.2b** (визуал, один PR / волна)

- [ ] Dashboard — data card polish (banner не возвращать)
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
| 2026-05-26 | Синхронизация с кодом: List/Calendar tabs, unified activities, dashboard log, connections+garmin-session, legacy redirects |
