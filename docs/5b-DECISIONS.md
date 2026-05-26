# Фаза 5b.0 — решения

> Реализовано в коде: `users.is_admin`, bootstrap, CLI, `REGISTRATION_OPEN`.  
> Решения закрыты (5b ✅). Актуальный roadmap: [PLAN.md](PLAN.md) · история: [PLAN-ARCHIVE.md](PLAN-ARCHIVE.md).

## Регистрация

| Режим | `REGISTRATION_OPEN` | Кто создаёт пользователей |
|-------|---------------------|---------------------------|
| **Invite-only (prod)** | `false` (по умолчанию) | Админ через `/app/admin` или `getsync user create` |
| **Открытая** | `true` | Саморегистрация на `/register` — [2.1-REGISTER.md](2.1-REGISTER.md) |

На production **app.getsync.me** оставляем `REGISTRATION_OPEN=false` до готовности rate limit и UI регистрации (**2.1**).

## Первый admin

Порядок при старте (`apply_bootstrap_admin`):

1. Если задан **`BOOTSTRAP_ADMIN_EMAIL`** — пользователь с этим email получает `is_admin=1`.
2. Если в БД **нет активных админов** — promote tenant **`default`** (миграция существующих установок).

Ручное управление:

```bash
getsync user promote-admin default
getsync user promote-admin owner@example.com
getsync user demote-admin rider@example.com   # нельзя снять последнего admin
getsync user list                             # флаг [admin]
```

## Что ещё не меняется (до 5b.1+)

- ~~Отдельный `/admin/login` и `ADMIN_PASSWORD`~~ — убрано в **5b.1**; админ только через `/app/login` + `users.is_admin`.
- nginx **Basic Auth** на UI — снят (**1.4**); вход только через `/app/login` + `SESSION_COOKIE_SECURE`.
- `/register` и `/app/settings` — **5b.3** / **5b.4**.

## Переменные окружения

| Переменная | По умолчанию | Назначение |
|------------|--------------|------------|
| `REGISTRATION_OPEN` | `false` | Разрешить `/register` (5b.3) |
| `BOOTSTRAP_ADMIN_EMAIL` | — | Email admin при старте |
| `DEFAULT_USER_ID` | `default` | Tenant для fallback bootstrap |

См. [`.env.example`](../.env.example).
