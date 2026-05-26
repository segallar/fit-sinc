# Web UI (Jinja2 + Bootstrap 5)

> Индекс: [docs/README.md](README.md) · архитектура маршрутов: [ARCHITECTURE.md](ARCHITECTURE.md).

Кабинет `/app`, админка `/app/admin` и публичные страницы — Jinja2 + **Bootstrap 5.3** (CDN) + HTMX.

| Что | Где |
|-----|-----|
| Шаблоны | `getsync/web/templates/` |
| Layout | `layouts/base.html` — Bootstrap CSS/JS CDN |
| Кабинет | `layouts/cabinet.html` (nav-pills) |
| Вход / регистрация | `layouts/auth.html` (card) |
| Лендинг | `layouts/site.html` (navbar) |
| Тема (цвет primary) | `getsync/web/static/app.css` |
| HTMX | CDN в `layouts/base.html` |

## Локальный запуск

```bash
pip install -e .
uvicorn getsync.web.app:app --reload --port 8080
# http://127.0.0.1:8080/app/
```

Node.js **не нужен** для UI (Bootstrap с jsDelivr).

## Стили

- Основа: [Bootstrap 5.3](https://getbootstrap.com/) в `layouts/base.html`
- Бренд teal: переменные в `static/app.css` (`--bs-primary`)
- Классы: `btn`, `card`, `table`, `nav-pills`, `alert`, `badge`, `form-control`

## Компоненты

- `components/user_bar.html` — карточка пользователя
- `components/status_badge.html` — macro `status_badge`
- `components/pager.html`, `resync_form.html`, `flash.html`
- `components/timezone_select.html`, `locale_select.html`
- `components/connections_banner.html`, `datetime_cell.html`

## Новая страница

1. `templates/pages/...html` → extends `cabinet.html` / `auth.html` / `site.html`
2. `render_cabinet(request, "pages/....html", active="/app/...", **context)`
3. Разметка на Bootstrap; при смене primary — правка `app.css`
