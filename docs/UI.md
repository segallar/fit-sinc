# UI v2 (параллельно v1)

Старый UI (`fit_sinc/web/html.py` + inline CSS) **не трогаем** — все маршруты `/`, `/activities`, `/log`, `/session` как были.

Новый слой живёт отдельно:

| Что | Где |
|-----|-----|
| Шаблоны Jinja2 | `fit_sinc/web/templates/` |
| Роуты превью | `fit_sinc/web/ui_v2.py` → `/ui-preview` |
| Сборка CSS | `frontend/` → `fit_sinc/web/static/app.css` |
| HTMX | CDN в `layouts/base.html` |

## Превью в браузере

```bash
pip install -e .
# опционально, если меняли Tailwind-классы:
cd frontend && npm install && npm run build:css
uvicorn fit_sinc.web.app:app --reload --port 8080
# http://127.0.0.1:8080/ui-preview
```

## Работа в параллель (два потока)

1. **Функциональность / Phase 5–6** — правки в `app.py` + `html.py` как сейчас.
2. **Дизайн v2** — только `templates/`, `static/app.css`, `ui_v2.py`; перенос страницы = новый шаблон + замена `return H.page(...)` на `render_template(...)` **когда готово**.

Конфликты git минимальны: в `app.py` одна строка `app.include_router(ui_v2_router)`.

## Сборка Tailwind

```bash
cd frontend
npm ci
npm run build:css    # один раз перед коммитом, если меняли классы
npm run watch:css    # при вёрстке
```

`app.css` коммитим в репозиторий — CI и деплой **не требуют** Node.js.

## Миграция страницы (чеклист)

1. Вынести разметку в `templates/pages/<name>.html`.
2. Переиспользовать форматтеры из `html.py` (уже в `templating.jinja_env()`).
3. Подключить `layouts/base.html` (или `layouts/app.html` для `/app`).
4. Заменить handler в `app.py` / будущем `app_routes.py`.
5. Удалить дублирующий HTML из `html.py` только после проверки.

## Следующие шаги (Phase 6)

- `layouts/app.html` — кабинет пользователя `/app`
- `fragments/calendar.html` + `GET /app/activities/calendar?year=&month=`
- DaisyUI/Flowbite — по желанию, через `@plugin` или компоненты в шаблонах
