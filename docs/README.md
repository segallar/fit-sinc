# Документация GetSync

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
| [UI.md](UI.md) | Frontend | Jinja2, Tailwind, сборка `app.css` |
| [PLAN.md](PLAN.md) | Roadmap | Фазы, горизонты 1.x–3.x, реестр задач |
| [1.5-RENAME.md](1.5-RENAME.md) | Cutover | Бренд GetSync, DNS, cookie, SQLite |
| [5b-DECISIONS.md](5b-DECISIONS.md) | Auth | Регистрация, bootstrap admin |

---

## Соглашения в документах

| Термин | Значение |
|--------|----------|
| **GetSync** | Публичное имя продукта |
| **getsync** | Python-пакет и основная CLI-команда |
| **Legacy** | cookie `fit_sinc_session` (14 дней), файл `fit_sinc.db` — см. [1.5-RENAME.md](1.5-RENAME.md) |
| **tenant** | Пользователь сервиса (`users.id`, каталог `data/users/{id}/`) |
| **Production app** | `https://app.getsync.me` (целевой); legacy `fit.romansegalla.online` до DNS cutover |

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
  getsync.db              # SQLite (или legacy fit_sinc.db)
  users/
    {user_id}/
      hammerhead_tokens.json
      garmin_web/session.json
      garth/                # OAuth garth-ng (fallback upload)
      fits/                 # кэш .fit
```

Миграция с плоского `data/*` → `data/users/default/` при старте: [`getsync/users/migrate.py`](../getsync/users/migrate.py).

---

## Локальная разработка

```bash
pip install -e .
python -m compileall -q getsync
python -m unittest discover -s tests -p "test_*.py" -v
getsync serve   # http://127.0.0.1:8080
```

См. также [UI.md](UI.md) (Tailwind) и [CI-CD.md](CI-CD.md) (проверки как в CI).
