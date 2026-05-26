# Карта экранов `/app`

> Полная спецификация: **[APP-UI.md](../APP-UI.md)** · архитектура: [ARCHITECTURE.md](../ARCHITECTURE.md) · roadmap: [PLAN.md](../PLAN.md#снимок-кабинета-app).

**Статус (2026-05-26):** функциональная IA в prod (`cabinet.html`, nav-pills). Sidebar — прототип `/app/ui-preview`. Dashboard снят; sync log — admin.

## User flows

```text
Гость → /register или /app/login
     → /app/activities          ← главный экран (List | Calendar, sync summary)
     → /app/settings            ← profile, connections, garmin-session, password
     (layout: full width, left-aligned — APP-UI §1)

Просмотр поездки:
  Calendar → клик дня → /app/activities?view=list&date_from=&date_to=
  List → фильтры q / status / source / dates → re-sync / .fit

Admin (is_admin):
  /app/admin/              ← users CRUD
  /app/admin/sync-log      ← sync events всех tenants
  /app/admin/log           ← Garmin JWT refresh

Legacy (редирект):
  /app/        → /app/activities
  /app/log     → /app/admin/sync-log#sync-log
  /app/session → /settings#garmin-session
```

```mermaid
flowchart LR
  A["/app/activities"] --> B["view=list\nтаблица HH+Garmin"]
  A --> C["view=calendar\nSQLite aggregate"]
  C -->|день| B
  A --> S["sync summary\nretry errors"]
  F["/app/settings"] --> G["#connections"]
  G --> H["#garmin-session"]
  AD["/app/admin/sync-log"] --> L["#sync-log\nall tenants"]
```

## Экраны (индекс)

| URL | Шаблон / компонент | § APP-UI | Примечание |
|-----|-------------------|----------|------------|
| `/app/activities` | `pages/app/activities.html` | §6.2 | `view=list` (default) \| `calendar`; `activities_sync_panel` |
| `/app/activities` (calendar) | `components/activity_calendar.html` | §6.2 | `year`, `month`, фильтр `source` |
| `/app/` | — | — | **303** → `/app/activities` |
| `/app/settings` | `pages/app/settings.html` | §6.3 | `#profile` · `#connections` · `#password` |
| `/app/settings` | `components/garmin_session_section.html` | §6.3 | `#garmin-session` внутри Connections |
| `/app/log` | — | §6.4 | **303** → `/app/admin/sync-log` |
| `/app/session` | — | §6.3 | **303** → settings `#garmin-session` |
| `/app/admin/` | `pages/admin/users.html` | §6.5 | |
| `/app/admin/sync-log` | `pages/admin/sync_log.html` | §6.4 | + `sync_log_section.html` |
| `/app/admin/log` | `pages/admin/log.html` | §6.5 | Garmin JWT refresh |
| `/app/admin/users/*` | `pages/admin/user_form.html` | §6.5 | |
| `/app/login` | `pages/app/login.html` | — | `site_auth`, вне app shell |
| `/register` | `pages/site/register.html` | — | `site_auth` |
| 403 | `pages/forbidden.html` | §6.6 | |
| `/app/ui-preview` | `ui_preview_*.html` | APP-UI §2 | Wireframe sidebar + экраны |

**Удалены:** `pages/app/dashboard.html` · отдельные `pages/app/log.html`, `pages/app/session.html` (только redirect).

## Nav (prod)

Порядок в [`cabinet.py`](../../getsync/web/cabinet.py): **Activities** → **Settings** · Admin — ссылка в topbar если `is_admin`.  
Admin subnav: **Users** · **Sync log** · **Garmin log**.

## Компоненты по экранам

| Экран | Ключевые includes |
|-------|-------------------|
| Activities | `activities_tabs`, `activity_calendar`, `activities_sync_panel`, filters, pager, `resync_form` |
| Settings | `settings_subnav`, `connection_card`, `garmin_session_section`, `locale_select`, `timezone_select` |
| Admin sync log | `sync_log_section` (`show_user_column`) |
| Admin Garmin log | `garmin_refresh_log_table` |

## Wireframes (`/app/ui-preview`)

| URL | Шаблон |
|-----|--------|
| `/app/ui-preview` | `ui_preview_index.html` |
| `/app/ui-preview/dashboard` | `ui_preview_dashboard.html` (legacy wireframe) |
| `/app/ui-preview/activities` | `ui_preview_activities.html` (tabs + calendar) |
| `/app/ui-preview/settings` | `ui_preview_settings.html` |
| `/app/ui-preview/admin` | `ui_preview_admin.html` |

## Боли → mitigation

| Боль | Где зафиксировано |
|------|-------------------|
| Два входа (Basic + app) | Снято **1.4** |
| HH/Garmin не на Activities | Connections в Settings — APP-UI §1 |
| Log/session в nav | Убраны; sync log в admin, session в settings |
| Календарь без облачных дней | v6.1 в PLAN **2.3** 📋 |
| Sync log: duplicate vs error | PLAN **2.3a** 📋 · APP-UI §6.4 |

Детали layout, tokens, a11y — [APP-UI.md §3–9](../APP-UI.md).
