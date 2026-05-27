# Документация GetSync

> **Создано:** 2026-05-26 · **Обновлено:** 2026-05-26 · **Версия:** 0.7.0  
> **Продукт:** [GetSync](https://getsync.me) — синхронизация тренировок **Hammerhead Karoo → Garmin Connect**.  
> **Код:** пакет `getsync`, CLI `getsync`.  
> **Быстрый старт:** [README](../README.md).

---

## Навигация

| Документ | Для кого | Содержание |
|----------|----------|------------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Разработчик, ops | Поток данных, tenants, модули, безопасность, ограничения |
| [API_HAMMERHEAD.md](API_HAMMERHEAD.md) | Интеграции | OAuth, REST, webhook HMAC, Developer Portal |
| [API_GARMIN.md](API_GARMIN.md) | Интеграции | Web JWT, Playwright upload, garth-ng, refresh |
| [CI-CD.md](CI-CD.md) | Ops | VPS, nginx, certbot, rsync, GitHub Actions |
| [TESTING.md](TESTING.md) | QA / Dev | Стратегия тестов, каталог `tests/`, скрипты `scripts/` |
| [DOC-CONVENTION.md](DOC-CONVENTION.md) | Все | Соглашение: даты, версия продукта, шапка документов |
| [UI.md](UI.md) | Frontend | Jinja2, Bootstrap 5, tokens + `app.css` |
| **[APP-UI.md](APP-UI.md)** | Frontend | **Единая спецификация** всех страниц `/app` и admin |
| [design/SCREENS.md](design/SCREENS.md) | Frontend | Карта URL, user flows, wireframes |
| [design/DESIGN-FEEDBACK.md](design/DESIGN-FEEDBACK.md) | Frontend | Замечания к дизайну кабинета (текущий ввод) |
| [design/README.md](design/README.md) | Frontend | Дизайн-индекс, статус **2.10** / **2.3** |
| [CONNECTIONS.md](CONNECTIONS.md) | Product / FE | Sources и destinations в Settings |
| [STORAGE.md](STORAGE.md) | Backend | FIT: пути, `storage_key`, миграция, download |
| [DATABASE.md](DATABASE.md) | Backend | SQLite: таблицы, индексы, tenant, журналы |
| [PLAN.md](PLAN.md) | Roadmap | v0.6 / v0.7, реестр задач, горизонты |
| [CHANGELOG.md](../CHANGELOG.md) | Releases | Версии и release notes |
| [archive/](archive/) | Архив | [PLAN-ARCHIVE](archive/PLAN-ARCHIVE.md), [1.5](archive/1.5-RENAME.md), [5b](archive/5b-DECISIONS.md) |
| [2.1-REGISTER.md](2.1-REGISTER.md) | Auth | Саморегистрация `/register`, план email verify (**2.1e**) |
| [2.1e-EMAIL.md](2.1e-EMAIL.md) | Auth / Ops | Отправка email: SMTP/API, verify, алерты (**2.1e**, **2.6**) |
| [3.4-OAUTH-LOGIN.md](3.4-OAUTH-LOGIN.md) | Auth | Вход через Google / Apple (OIDC), **3.4** / фаза 10 |
| [3.11-GARMIN-PULL.md](3.11-GARMIN-PULL.md) | Integrations | Скачивание FIT, шаги и сон из Garmin (**3.11**) |

---

## Соглашения в документах

Каждый файл в `docs/` начинается с метаданных: **Создано** · **Обновлено** · **Версия** (продукта). Правила — [DOC-CONVENTION.md](DOC-CONVENTION.md).

| Термин | Значение |
|--------|----------|
| **GetSync** | Публичное имя продукта |
| **getsync** | Python-пакет и основная CLI-команда |
| **История rename** | fit_sinc → GetSync — [archive/1.5-RENAME.md](archive/1.5-RENAME.md) (миграции в коде сняты) |
| **tenant** | Пользователь сервиса (`users.id`, каталог `data/users/{id}/`) |
| **Production app** | `https://app.getsync.me` · legacy `fit.romansegalla.online` (301 → новый host — backlog) |

---

## Ключевые URL (production)

| Назначение | URL |
|------------|-----|
| Лендинг | `https://getsync.me/` |
| Кабинет / webhook | `https://app.getsync.me/` |
| Health | `https://app.getsync.me/health` |
| Webhook Hammerhead | `https://app.getsync.me/webhooks/hammerhead` |
| OAuth Hammerhead (UI) | `https://app.getsync.me/app/settings/hammerhead/callback` |

---

## Данные на диске

```text
data/
  getsync.db              # SQLite — см. DATABASE.md
  users/
    {user_id}/
      activities/           # FIT: hammerhead/, garmin/, …
      hammerhead_tokens.json
      garmin_web/session.json
      garth/                # OAuth garth-ng (fallback upload)
      activities/           # FIT: hammerhead/, garmin/ — см. STORAGE.md
```

Подробнее: [STORAGE.md](STORAGE.md) · [ARCHITECTURE.md](ARCHITECTURE.md).

Bootstrap Hammerhead user id: [`getsync/users/migrate.py`](../getsync/users/migrate.py).

---

## Локальная разработка

```bash
pip install -e .
python -m compileall -q getsync
python -m unittest discover -s tests -p "test_*.py" -v
getsync serve   # http://127.0.0.1:8080
```

См. также [TESTING.md](TESTING.md) (стратегия и скрипты), [UI.md](UI.md) (Bootstrap) и [CI-CD.md](CI-CD.md) (деплой).
