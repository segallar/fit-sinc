# Web UI (Jinja2 + Tailwind)

Весь кабинет `/app` и админка `/app/admin` рендерятся через Jinja2-шаблоны и собранный `app.css`.

| Что | Где |
|-----|-----|
| Шаблоны | `fit_sinc/web/templates/` |
| Layout кабинета | `layouts/cabinet.html` (extends `base.html`) |
| Layout входа | `layouts/auth.html` |
| Роуты | `fit_sinc/web/app_routes.py`, `admin_routes.py` |
| Рендер | `fit_sinc/web/cabinet.py` → `render_cabinet()` |
| Форматтеры | `fit_sinc/web/html.py` (`esc`, `fmt_*`, `query_string`) |
| Jinja helpers | `fit_sinc/web/templating.py` |
| CSS | `frontend/` → `fit_sinc/web/static/app.css` |
| HTMX | CDN в `layouts/base.html` |

## Локальный запуск

```bash
pip install -e .
cd frontend && npm install && npm run build:css   # при изменении Tailwind-классов
uvicorn fit_sinc.web.app:app --reload --port 8080
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
