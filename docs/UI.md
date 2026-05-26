# Web UI (Jinja2 + Bootstrap 5)

> Индекс: [docs/README.md](README.md) · **Страницы `/app`:** [APP-UI.md](APP-UI.md) · карта URL: [design/SCREENS.md](design/SCREENS.md) · архитектура: [ARCHITECTURE.md](ARCHITECTURE.md).

Кабинет `/app`, админка `/app/admin` и публичные страницы — Jinja2 + **Bootstrap 5.3** (CDN) + HTMX.

| Что | Где |
|-----|-----|
| Шаблоны | `getsync/web/templates/` |
| Layout | `layouts/base.html` — Bootstrap CSS/JS CDN |
| Кабинет (prod) | `layouts/cabinet.html` — nav-pills, `app_header` |
| Кабинет (прототип) | `layouts/cabinet_sidebar.html` — `/app/ui-preview` |
| Вход / регистрация | `layouts/site_auth.html` |
| Лендинг | `layouts/site.html` |
| Design tokens | `getsync/web/static/tokens.css` |
| Тема | `getsync/web/static/app.css` — `.getsync-app`, `.getsync-site`, `.getsync-cal-*` |
| **Спецификация** | **[APP-UI.md](APP-UI.md)** |
| Дизайн-индекс | [design/README.md](design/README.md) |
| HTMX | CDN в `layouts/base.html` |

## Локальный запуск

```bash
python3 -m venv .venv && source .venv/bin/activate   # один раз
python3 -m pip install -e .
python3 -m uvicorn getsync.web.app:app --reload --port 8080
```

| URL | Назначение |
|-----|------------|
| http://127.0.0.1:8080/app/login | Вход |
| http://127.0.0.1:8080/app/activities | Prod: list + calendar |
| http://127.0.0.1:8080/app/ui-preview | Прототип sidebar |

Редизайн (**2.10**) сначала на **ui-preview**; prod — после переноса `cabinet.html` → sidebar.

Node.js **не нужен** (Bootstrap с jsDelivr). `frontend/tailwind.config.js` — не в prod, см. [frontend/README.md](../frontend/README.md).

## Стили

- Основа: [Bootstrap 5.3](https://getbootstrap.com/) в `layouts/base.html`
- **Tokens:** `static/tokens.css` — палитра, `--getsync-status-*`, радиусы
- **Тема:** `static/app.css` — `.getsync-app`, `.getsync-site`, календарь `.getsync-cal-grid` / `.getsync-cal-day--*`
- Классы: `getsync-data-card`, `getsync-filter-card`, `table-sm`, `nav-pills`

Подробности плотности и tokens — [APP-UI.md §3–4](APP-UI.md).

## Кабинет `/app` (текущее)

| Экран | Шаблон |
|-------|--------|
| Activities | `pages/app/activities.html` + `activities_tabs`, `activity_calendar`, `activities_sync_panel` |
| Settings | `pages/app/settings.html` + `settings_subnav`, `connection_card`, `garmin_session_section` |
| Admin sync log | `pages/admin/sync_log.html` + `sync_log_section` |
| Admin Garmin log | `pages/admin/log.html` + `garmin_refresh_log_table` |

Nav: Activities → Settings ([`cabinet.py`](../getsync/web/cabinet.py)). `/app/` → redirect Activities.

## Компоненты

| Компонент | Файл | Где используется |
|-----------|------|------------------|
| Page header | `page_header.html` | Все страницы кабинета |
| Status badge | `status_badge.html` (macro) | Activities, admin |
| Pager | `pager.html` | Activities list, sync log |
| Re-sync | `resync_form.html` | Activities |
| Datetime | `datetime_cell.html` | Activities (TZ user) |
| Activities tabs | `activities_tabs.html` | List \| Calendar |
| Activity calendar | `activity_calendar.html` | `view=calendar` |
| Sync summary | `activities_sync_panel.html` | Activities (без таблицы лога) |
| Sync log | `sync_log_section.html` | Admin `/app/admin/sync-log` |
| Connections | `connection_card.html` | Settings `#connections` |
| Garmin session | `garmin_session_section.html` | Settings `#garmin-session` |
| Settings subnav | `settings_subnav.html` | Settings |
| Flash | `flash.html` | `cabinet.html` |
| Selects | `timezone_select`, `locale_select` | Settings, admin |
| Build footer | `build_footer.html` | `base.html` |

**Legacy (есть в репо, не на dashboard):** `connections_banner.html` — статус HH/Garmin только в Settings.

**Цель 2.10:** `app_sidebar.html` заменит pills + `app_header`.

## Рендер из Python

```python
from getsync.web.cabinet import render_cabinet

return render_cabinet(
    request,
    "pages/app/activities.html",
    active="/activities",
    activities_view="list",  # или calendar + calendar=...
    ...
)
```

Маршруты: [`app_routes.py`](../getsync/web/app_routes.py) — `view=list|calendar`, legacy redirects.

## Новая страница

1. `templates/pages/...html` → `extends layouts/cabinet.html`
2. `page_header` + компоненты из [APP-UI.md §5](APP-UI.md)
3. `render_cabinet(..., active="/app/…")`
4. Запись в [design/SCREENS.md](design/SCREENS.md)
