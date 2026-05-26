# Web UI (Jinja2 + Tailwind)

> Индекс: [docs/README.md](README.md) · архитектура маршрутов: [ARCHITECTURE.md](ARCHITECTURE.md).

Весь кабинет `/app` и админка `/app/admin` рендерятся через Jinja2-шаблоны и собранный `app.css`.

| Что | Где |
|-----|-----|
| Шаблоны | `getsync/web/templates/` |
| Layout кабинета | `layouts/cabinet.html` (extends `base.html`) |
| Layout входа | `layouts/auth.html` |
| Роуты | `getsync/web/app_routes.py`, `admin_routes.py` |
| Рендер | `getsync/web/cabinet.py` → `render_cabinet()` |
| Форматтеры | `getsync/web/html.py` (`esc`, `fmt_*`, `query_string`) |
| Jinja helpers | `getsync/web/templating.py` |
| CSS | `frontend/` → `getsync/web/static/app.css` |
| HTMX | CDN в `layouts/base.html` |

## Локальный запуск

```bash
pip install -e .
cd frontend && npm install && npm run build:css   # при изменении Tailwind-классов
uvicorn getsync.web.app:app --reload --port 8080
# http://127.0.0.1:8080/app/
```

## Сборка Tailwind

```bash
cd frontend
npm ci
npm run build:css
npm run watch:css    # при вёрстке
```

`app.css` коммитим в репозиторий — CI и деплой **не требуют** Node.js.

## Компоненты

- `components/user_bar.html` — полоса пользователя + logout
- `components/status_badge.html` — статус синка
- `components/pager.html`, `resync_form.html`, `timezone_select.html`, `flash.html`
- `components/datetime_cell.html` — дата/время в таблицах

## Новая страница

1. Добавить `templates/pages/...html`, extends `layouts/cabinet.html` или `auth.html`.
2. В handler вызвать `render_cabinet(request, "pages/....html", active="/app/...", **context)`.
3. Передавать структурированные данные (dict/dataclass), не HTML-строки.
4. При новых Tailwind-классах — `npm run build:css` и закоммитить `static/app.css`.
