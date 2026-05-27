# Дизайн кабинета GetSync (подготовка к **2.10**)

> **Создано:** 2026-05-26 · **Обновлено:** 2026-05-27 · **Версия:** 0.7.0  
> **Главный документ:** **[APP-UI.md](../APP-UI.md)** — решения, layout, компоненты, страницы.  
> **Карта экранов:** [SCREENS.md](SCREENS.md) · roadmap: [PLAN.md](../PLAN.md#210--дизайн-uiux) · стек: [UI.md](../UI.md)

## Стек

| Слой | Технология |
|------|------------|
| Разметка | Jinja2 (`getsync/web/templates/`) |
| CSS | Bootstrap 5.3 (CDN) |
| Тема | [`tokens.css`](../../getsync/web/static/tokens.css) + [`app.css`](../../getsync/web/static/app.css) |
| Интерактив | HTMX 2 (CDN), без SPA |

**Не в prod:** Tailwind из `frontend/` — см. [frontend/README.md](../../frontend/README.md).

## Зоны UI

| Класс на `<body>` | Где | Спецификация |
|-------------------|-----|--------------|
| `.getsync-site` | `/`, `/register`, login | Лендинг |
| `.getsync-app` | `/app/*`, `/app/admin/*` | [APP-UI.md](../APP-UI.md) |

## Файлы документации

| Файл | Назначение |
|------|------------|
| [APP-UI.md](../APP-UI.md) | Q&A, компоненты, §6 по страницам, чеклист |
| [SCREENS.md](SCREENS.md) | URL, flows, mermaid, wireframes |
| [DESIGN-FEEDBACK.md](DESIGN-FEEDBACK.md) | **Замечания к дизайну** (текущий шаг) |
| [UI.md](../UI.md) | Стек, запуск, список компонентов |
| [CONNECTIONS.md](../CONNECTIONS.md) | Sources / destinations в Settings |
| `static/tokens.css` | Design tokens |
| `static/app.css` | Тема + calendar grid |

## Статус реализации

> **Фокус roadmap:** замечания → [DESIGN-FEEDBACK.md](DESIGN-FEEDBACK.md) → **2.10** → **2.13** тесты. [PLAN.md](../PLAN.md#фокус-сейчас-тестирование-и-кабинет-app)

| Этап | Статус | Где в коде |
|------|--------|------------|
| Функциональность list/calendar/connections | ✅ | см. PLAN снимок кабинета |
| **2.13** тестирование + багфикс | ▶ **P0** | чеклист в PLAN |
| Sidebar prod (**2.10**) | ▶ **P0** | `cabinet_sidebar.html`, ui-preview |
| Sync log UX (**2.14**) | ▶ **P0** | `sync_log_section.html` |
| Garmin login UI (**2.12**) | P1 | Connections |
| Admin / mobile (**2.10.3**) | 📋 | после основной волны |

Чеклист — **§11** [APP-UI.md](../APP-UI.md).

## Локальный цикл

1. `uvicorn getsync.web.app:app --reload --port 8080`
2. Правки в `templates/`, `app.css`, `tokens.css`
3. Сверка: `/app/ui-preview/*` и prod `/app/activities`, `/app/settings`
4. `python -m unittest discover -s tests -p "test_*.py"`
5. Деплой после переноса layout на весь кабинет
