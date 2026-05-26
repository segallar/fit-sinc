# CI/CD и деплой GetSync

> Личный сервис на одном VPS. **CI:** GitHub Actions — [`test.yml`](../.github/workflows/test.yml) (push/PR) и [`deploy.yml`](../.github/workflows/deploy.yml) (sirocco после Test на `main`). Badges в [README](../README.md). Альтернатива: [`.gitlab-ci.yml`](../.gitlab-ci.yml).  
> Индекс документации: [docs/README.md](README.md).

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
| App (legacy DNS) | `fit.romansegalla.online` — до cutover [1.5-C](1.5-RENAME.md) |
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
- [ ] `getsync.conf` + certbot
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

### 1. Код приложения

Перед rsync собирается Tailwind: [`scripts/ci/build-frontend-css.sh`](../scripts/ci/build-frontend-css.sh) → `getsync/web/static/app.css`. Нужны Node.js и `npm` на машине, с которой деплоите (или в GitHub Actions).

```bash
cd /path/to/getsync

./scripts/ci/build-frontend-css.sh

rsync -avz --delete --exclude-from=.rsyncignore \
  -e "ssh -i ~/.ssh/id_ed25519" \
  ./ root@sirocco.romansegalla.online:/opt/getsync/

# или: ./scripts/ci/deploy.sh
```

**Не синхронизируем** ([`.rsyncignore`](../.rsyncignore)):

| Путь | Причина |
|------|---------|
| `.env`, `data/` | Секреты и runtime на сервере |
| `.venv`, `.git` | Создаётся / живёт на VPS |
| `frontend/node_modules/` | CSS собирается до rsync |

После rsync на сервере:

```bash
chown -R getsync:getsync /opt/getsync
sudo -u getsync bash -c 'cd /opt/getsync && .venv/bin/pip install -e .'
systemctl restart getsync
curl -sf http://127.0.0.1:8080/health
```

### 2. Секреты и сессии

```bash
scp -i ~/.ssh/id_ed25519 .env root@sirocco:/opt/getsync/

# per-tenant (пример: default)
scp -i ~/.ssh/id_ed25519 data/users/default/hammerhead_tokens.json \
  root@sirocco:/opt/getsync/data/users/default/
scp -i ~/.ssh/id_ed25519 -r data/users/default/garth data/users/default/garmin_web \
  root@sirocco:/opt/getsync/data/users/default/

ssh root@sirocco 'chown -R getsync:getsync /opt/getsync/data && systemctl restart getsync'
```

### 3. Локальная настройка auth (Mac)

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

Конфиг: [`deploy/nginx/getsync.conf`](../deploy/nginx/getsync.conf) (целевой), legacy: [`deploy/nginx/fit.conf`](../deploy/nginx/fit.conf).

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

| Job | Когда | Действие |
|-----|--------|----------|
| `test` | push, PR | `pip install -e .`, `compileall getsync`, unittest |
| `deploy` | push `main` после успешного test | rsync → `/opt/getsync`, restart, `/health` |

Скрипт: [`scripts/ci/deploy.sh`](../scripts/ci/deploy.sh)

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

### Ручной deploy

```bash
SSH_PRIVATE_KEY="$(cat ~/.ssh/id_ed25519)" ./scripts/ci/deploy.sh
```

---

## GitLab CI

[`.gitlab-ci.yml`](../.gitlab-ci.yml) — зеркало job'ов; переменная `SSH_PRIVATE_KEY` (File).

---

## Чеклист релиза

- [ ] rsync + `pip install -e .`
- [ ] `systemctl is-active getsync` → `active`
- [ ] `https://app.getsync.me/health` → 200
- [ ] Webhook без HMAC → 403
- [ ] `SESSION_COOKIE_SECURE=true` в `/opt/getsync/.env`
- [ ] `/app/login` без nginx Basic Auth
- [ ] `getsync hammerhead status` и `getsync garmin status` на сервере (от пользователя `getsync`)
