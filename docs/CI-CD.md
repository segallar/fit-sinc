# CI/CD и деплой GetSync

> **Создано:** 2026-05-25 · **Обновлено:** 2026-05-27 · **Версия:** 0.7.0  
> Личный сервис на одном VPS. **CI/CD:** [GitHub Actions](#github-actions) — основной путь; репозиторий [github.com/segallar/getsync](https://github.com/segallar/getsync). Альтернатива: [GitLab CI](#gitlab-ci).  
> Индекс документации: [docs/README.md](README.md).

## Содержание

- [Схема](#схема)
- [DNS и домены](#dns-и-домены)
- [Первичная настройка сервера](#первичная-настройка-сервера-один-раз)
- [Continuous Deployment](#continuous-deployment) — [GitHub Actions](#основной-путь-github-actions) (основной) · [ручной deploy](#ручной-deploy-fallback)
- [GitHub Actions](#github-actions) — workflow, secrets, оптимизации
- [GitLab CI](#gitlab-ci) — legacy/alternative
- [Проверка после деплоя](#проверка-после-деплоя)
- [nginx](#nginx) · [systemd](#systemd) · [Rollback](#rollback)
- [Чеклист релиза](#чеклист-релиза)

## Схема

```mermaid
flowchart LR
    Dev[Mac / GitHub Actions] -->|rsync + ssh| VPS[sirocco /opt/getsync]
    VPS --> Systemd[getsync.service]
    Systemd --> App[uvicorn :8080]
    Nginx[nginx TLS] --> App
    HH[Hammerhead webhook] --> Nginx
    User[Браузер] --> Nginx
```

| Компонент | Значение |
|-----------|----------|
| Сервер | `sirocco.romansegalla.online` (`134.209.133.187`) |
| SSH | `ssh -i ~/.ssh/id_ed25519 root@sirocco.romansegalla.online` |
| **App (целевой)** | `getsync.me`, `app.getsync.me` |
| App (legacy DNS) | `fit.romansegalla.online` — 301 → `app.getsync.me` ✅ ([`fit.conf`](../deploy/nginx/fit.conf)) |
| Лендинг (личный) | `romansegalla.online` — proxy на `:8080` |
| Каталог приложения | `/opt/getsync` |
| Пользователь сервиса | `getsync:getsync` |
| Python venv | `/opt/getsync/.venv` |
| Конфиг | `/opt/getsync/.env` (не в git) |
| Данные | `/opt/getsync/data/` (`getsync.db`, `users/{id}/…`) |

---

## DNS и домены

### GetSync — `getsync.me`

| Роль | Значение |
|------|----------|
| **Регистратор** | GoDaddy — `getsync.me` |
| **DNS** | GoDaddy NS `ns37` / `ns38.domaincontrol.com` |
| **Приложение** | `app.getsync.me` → A `134.209.133.187` |
| **Лендинг** | `getsync.me` → A `@` на sirocco |
| **nginx** | [`deploy/nginx/getsync.conf`](../deploy/nginx/getsync.conf) |

#### A-записи

| Type | Name | Value |
|------|------|-------|
| A | `@` | `134.209.133.187` |
| A | `app` | `134.209.133.187` |

Проверка:

```bash
dig +short getsync.me A
dig +short app.getsync.me A
```

#### nginx + TLS на sirocco

```bash
scp -i ~/.ssh/id_ed25519 deploy/nginx/getsync.conf \
  root@sirocco.romansegalla.online:/etc/nginx/conf.d/getsync.conf

ssh -i ~/.ssh/id_ed25519 root@sirocco.romansegalla.online \
  'nginx -t && systemctl reload nginx'

ssh -i ~/.ssh/id_ed25519 root@sirocco.romansegalla.online \
  'certbot --nginx -d getsync.me -d app.getsync.me'
```

Smoke:

```bash
curl -sk https://getsync.me/health
curl -sk https://app.getsync.me/health
curl -sk -o /dev/null -w "%{http_code}\n" https://app.getsync.me/app/login
```

#### Hammerhead (после HTTPS)

| Поле | URL |
|------|-----|
| Webhook | `https://app.getsync.me/webhooks/hammerhead` |
| OAuth redirect (UI) | `https://app.getsync.me/app/settings/hammerhead/callback` |

В `.env` на prod: `HAMMERHEAD_WEB_REDIRECT_URI`, при необходимости обновить webhook secret в Developer Portal.

#### Чеклист DNS

- [ ] A `@` и `app` → `134.209.133.187`
- [x] `getsync.conf` + certbot (2026-05-27)
- [ ] `/health` на обоих хостах
- [ ] Hammerhead webhook URL обновлён

---

## Первичная настройка сервера (один раз)

```bash
apt install -y python3.12-venv nginx certbot python3-certbot-nginx

useradd -r -d /opt/getsync -s /usr/sbin/nologin getsync
mkdir -p /opt/getsync/data/users/default/fits
chown -R getsync:getsync /opt/getsync

python3.12 -m venv /opt/getsync/.venv
sudo -u getsync /opt/getsync/.venv/bin/pip install -e /opt/getsync

cp deploy/nginx/getsync.conf /etc/nginx/conf.d/getsync.conf
cp deploy/getsync.service /etc/systemd/system/getsync.service
nginx -t && systemctl reload nginx
systemctl enable --now getsync
```

Playwright (для Garmin upload):

```bash
sudo -u getsync /opt/getsync/.venv/bin/playwright install chromium
```

---

## Continuous Deployment

### Основной путь (GitHub Actions)

**Репозиторий:** [github.com/segallar/getsync](https://github.com/segallar/getsync) · badge CI в [README](../README.md).

Push или merge в `main` / `master` / `hotfix/*` → workflow [**CI**](../.github/workflows/test.yml) → job `test` → job `deploy` → [`deploy.sh`](../scripts/ci/deploy.sh) (rsync + restart на sirocco).

| Триггер | `test` | `deploy` |
|---------|--------|----------|
| push `main` / `master` / `hotfix/*` | да | да (после успешного `test`) |
| pull_request | да | **нет** |
| `workflow_dispatch` | да | **нет** (deploy только при `push`) |

Подробности: [GitHub Actions](#github-actions) (secrets, concurrency, оптимизации). Экстренный деплой без CI — [ручной deploy](#ручной-deploy-fallback).

### Ручной deploy (fallback)

UI: Bootstrap 5 с CDN в шаблонах; [`getsync/web/static/app.css`](../getsync/web/static/app.css) — только переопределение темы (коммитится). Node.js для деплоя **не нужен**. Скрипт [`scripts/ci/build-frontend-css.sh`](../scripts/ci/build-frontend-css.sh) — заглушка для совместимости.

```bash
cd /path/to/getsync

./scripts/ci/build-frontend-css.sh

rsync -avz --delete --exclude-from=.rsyncignore \
  -e "ssh -i ~/.ssh/id_ed25519" \
  ./ root@sirocco.romansegalla.online:/opt/getsync/

# предпочтительно: полный цикл как в CI
SSH_PRIVATE_KEY="$(cat ~/.ssh/id_ed25519)" ./scripts/ci/deploy.sh
```

**Не синхронизируем** ([`.rsyncignore`](../.rsyncignore)):

| Путь | Причина |
|------|---------|
| `.env`, `data/` | Секреты и runtime на сервере |
| `.venv`, `.git` | Создаётся / живёт на VPS |
| `frontend/node_modules/` | CSS собирается до rsync |

После rsync на сервере (в CI делает [`deploy.sh`](../scripts/ci/deploy.sh)):

- при первом деплое или отсутствии `.playwright-chromium.ok` — `playwright install chromium` под пользователем `getsync` в `/opt/getsync/.cache/ms-playwright` (см. `PLAYWRIGHT_BROWSERS_PATH` в unit);
- однократно на VPS при ошибках запуска браузера: `sudo .venv/bin/playwright install-deps chromium` (системные lib).


```bash
# rsync от root с --chown=getsync:getsync — отдельный chown -R не нужен
# pip install -e . — только если изменился pyproject.toml (editable install)
systemctl restart getsync
curl -sf http://127.0.0.1:8080/health
```

### Секреты и сессии

```bash
scp -i ~/.ssh/id_ed25519 .env root@sirocco:/opt/getsync/

# per-tenant (пример: default)
scp -i ~/.ssh/id_ed25519 data/users/default/hammerhead_tokens.json \
  root@sirocco:/opt/getsync/data/users/default/
scp -i ~/.ssh/id_ed25519 -r data/users/default/garth data/users/default/garmin_web \
  root@sirocco:/opt/getsync/data/users/default/

ssh root@sirocco 'chown -R getsync:getsync /opt/getsync/data && systemctl restart getsync'
```

### Локальная настройка auth (Mac)

```bash
cd /path/to/getsync
cp .env.example .env
pip install -e .
getsync hammerhead auth
getsync garmin login
```

Затем — копирование `data/users/default/` на сервер (шаг 2).

---

## Проверка после деплоя

```bash
curl -sk https://app.getsync.me/health

curl -sk -o /dev/null -w "%{http_code}\n" -X POST \
  https://app.getsync.me/webhooks/hammerhead \
  -H "Content-Type: application/json" \
  -d '{"activityId":"test","userId":"192184"}'
# без HMAC → 403

curl -sk -o /dev/null -w "%{http_code}\n" https://app.getsync.me/app/login
# → 200

ssh root@sirocco \
  'systemctl status getsync; journalctl -u getsync -n 20 --no-pager'
```

---

## nginx

| Path | Auth | Назначение |
|------|------|------------|
| `/webhooks/*` | нет | Hammerhead (HMAC в приложении) |
| `/health` | нет | Healthcheck |
| `/`, `/static/*`, `/app/*` | сессия приложения | UI |

Конфиг: [`deploy/nginx/getsync.conf`](../deploy/nginx/getsync.conf) (целевой), legacy redirect: [`deploy/nginx/fit.conf`](../deploy/nginx/fit.conf) (`fit.romansegalla.online` → `https://app.getsync.me$request_uri`).

Legacy redirect (уже на sirocco с 2026-05-27):

```bash
scp -i ~/.ssh/id_ed25519 deploy/nginx/fit.conf \
  root@sirocco.romansegalla.online:/etc/nginx/conf.d/fit.conf
ssh -i ~/.ssh/id_ed25519 root@sirocco.romansegalla.online \
  'nginx -t && systemctl reload nginx'
curl -sI https://fit.romansegalla.online/health | grep -i location
```

**Production `.env`:**

- `SESSION_SECRET` — длинная случайная строка  
- `SESSION_COOKIE_SECURE=true`  

**romansegalla.online** (личный лендинг): [`deploy/nginx/romansegalla.conf`](../deploy/nginx/romansegalla.conf).

---

## systemd

[`deploy/getsync.service`](../deploy/getsync.service)

```bash
systemctl restart getsync
journalctl -u getsync -f
```

Приложение слушает **только** `127.0.0.1:8080`.

### Логи приложения

| Назначение | Куда |
| ---------- | ---- |
| Отладка, webhook, ошибки | **journald** (`journalctl -u getsync`) |
| Файл (ротация 5×5 MB) | **`{data_dir}/logs/getsync.log`** (prod: `/opt/getsync/data/logs/getsync.log`) |
| События синка (UI) | SQLite `sync_events` → Admin → Sync log |
| Audit-дубль sync/session | та же строка в файле/journald: `getsync.audit` |

Переменные `.env` (опционально):

| Переменная | По умолчанию |
| ---------- | ------------ |
| `GETSYNC_LOG_TO_FILE` | `true` |
| `GETSYNC_LOG_FILE` | `data/logs/getsync.log` (относительно `data_dir`) |
| `GETSYNC_LOG_LEVEL` | `INFO` |

Отключить файл, оставить только journald: `GETSYNC_LOG_TO_FILE=false`.

```bash
tail -f /opt/getsync/data/logs/getsync.log
grep garmin_duplicate /opt/getsync/data/logs/getsync.log
```

---

## Rollback

```bash
cd /opt/getsync
# откат к предыдущему rsync-снимку или git checkout
sudo -u getsync .venv/bin/pip install -e .
systemctl restart getsync
```

`data/` и `.env` при rollback не трогаем.

---

## GitHub Actions

Workflow: [`.github/workflows/test.yml`](../.github/workflows/test.yml) — один pipeline **CI** (`actions/checkout@v6`, `actions/setup-python@v6`, Node 24 runtime).

**Настройка (один раз):** репозиторий → **Settings → Secrets and variables → Actions** — secret `SSH_PRIVATE_KEY` (приватный ключ `root@sirocco`); variables `GETSYNC_SSH_*` — через [`sync-github-vars.sh`](../scripts/ci/sync-github-vars.sh) или UI.

| Job | Когда | Действие |
|-----|--------|----------|
| `test` | push, PR, `workflow_dispatch` | `pip install -e .`, `compileall getsync`, unittest |
| `deploy` | **только push** `main` / `master` / `hotfix/*` после `test` | rsync → `/opt/getsync`, restart, `/health` |

Поведение workflow:

- **`concurrency`** — группа `ci-<workflow>-<ref>`, `cancel-in-progress: true` (новый push отменяет предыдущий run на той же ветке).
- **`environment: production`** — job `deploy` привязан к GitHub Environment (опционально protection rules).
- **PR** — только gate `test`; prod не трогаем.
- **`GETSYNC_DEPLOY_NUMBER`** — `github.run_number` в metadata деплоя.

Скрипт деплоя: [`scripts/ci/deploy.sh`](../scripts/ci/deploy.sh).

### Ускорение deploy

| Оптимизация | Эффект |
|-------------|--------|
| **Один workflow** (без `workflow_run`) | Нет второго запуска runner и паузы ~30–90 с между Test и Deploy |
| **pip cache** в job `test` | Быстрее установка зависимостей в CI |
| **rsync без tests/docs/.github** | Меньше файлов на wire (см. [`.rsyncignore`](../.rsyncignore)) |
| **`rsync --chown=getsync:getsync`** | Без `chown -R /opt/getsync` (в т.ч. не трогаем `data/`) |
| **skip `pip install -e .`** если `pyproject.toml` не менялся | Обычный код-фикс: rsync + restart (~10–30 с на сервере) |
| **health poll** — первая попытка сразу, далее до 10× с `sleep 2` | Быстрый happy-path; retry при медленном старте uvicorn |

Прогон только тестов: Actions → **CI** → **Run workflow** (deploy не запустится). Экстренный деплой: [ручной deploy](#ручной-deploy-fallback).

### Secrets / variables

| Имя | Тип | По умолчанию |
|-----|-----|--------------|
| `SSH_PRIVATE_KEY` | Secret | — |
| `GETSYNC_SSH_HOST` | Variable | `sirocco.romansegalla.online` |
| `GETSYNC_SSH_USER` | Variable | `root` |
| `GETSYNC_DEPLOY_PATH` | Variable | `/opt/getsync` |

Переменные в GitHub (после `gh auth login`):

```bash
./scripts/ci/sync-github-vars.sh
```

Скрипт выставляет `GETSYNC_SSH_*` и удаляет legacy `FIT_SINC_*`. В `deploy.sh` fallback на старые имена остаётся, пока vars не обновлены.

**Не хранить в CI:** `.env`, `data/`, пароли Garmin.

### Локально как CI

```bash
pip install -e .
python -m compileall -q getsync
python -m unittest discover -s tests -p "test_*.py" -v
```

Полная стратегия, каталог тестов и назначение скриптов: [TESTING.md](TESTING.md). Метаданные документов: [DOC-CONVENTION.md](DOC-CONVENTION.md).

---

## GitLab CI

**Статус:** legacy / alternative — основной pipeline на GitHub. Файл [`.gitlab-ci.yml`](../.gitlab-ci.yml) сохранён для зеркала или миграции; job'ы те же по смыслу (`test` → `deploy`), общий [`deploy.sh`](../scripts/ci/deploy.sh).

| | GitHub Actions | GitLab CI |
|--|----------------|-----------|
| Основной | да | нет |
| Deploy branches | `main`, `master`, `hotfix/*` | `main`, `master`, `hotfix/*` |
| Deploy number | `github.run_number` | `CI_PIPELINE_IID` |
| pip cache в test | да | нет |
| Secret SSH | `SSH_PRIVATE_KEY` (Secret) | `SSH_PRIVATE_KEY` (File, masked) |
| Environment URL | — | `https://app.getsync.me` |

Переменные (Settings → CI/CD → Variables): `SSH_PRIVATE_KEY` (File); опционально `GETSYNC_SSH_HOST`, `GETSYNC_SSH_USER`, `GETSYNC_DEPLOY_PATH`.

---

## Чеклист релиза

- [ ] rsync + `pip install -e .`
- [ ] `systemctl is-active getsync` → `active`
- [x] `https://app.getsync.me/health` → 200
- [ ] Webhook без HMAC → 403
- [ ] `SESSION_COOKIE_SECURE=true` в `/opt/getsync/.env`
- [ ] `/app/login` без nginx Basic Auth
- [ ] `getsync hammerhead status` и `getsync garmin status` на сервере (от пользователя `getsync`)
