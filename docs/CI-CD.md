# CI/CD и деплой fit_sinc

> Личный сервис на одном VPS. **CI:** GitHub Actions ([`.github/workflows/ci.yml`](../.github/workflows/ci.yml)) — test на push/PR, deploy на `main` → sirocco. Альтернатива: [`.gitlab-ci.yml`](../.gitlab-ci.yml). Ручной deploy с Mac — ниже.

## Схема

```mermaid
flowchart LR
    Dev[Mac локально] -->|rsync + ssh| VPS[sirocco /opt/fit_sinc]
    VPS --> Systemd[fit-sinc.service]
    Systemd --> App[uvicorn :8080]
    Nginx[nginx TLS] --> App
    HH[Hammerhead webhook] --> Nginx
    User[Браузер + Basic Auth] --> Nginx
```

| Компонент | Значение |
|-----------|----------|
| Сервер | `sirocco.romansegalla.online` (`134.209.133.187`) |
| SSH | `ssh -i ~/.ssh/id_ed25519 root@sirocco.romansegalla.online` |
| Домен | `fit.romansegalla.online` (DNS only, без Cloudflare proxy) |
| Каталог приложения | `/opt/fit_sinc` |
| Пользователь сервиса | `fit_sinc:fit_sinc` |
| Python venv | `/opt/fit_sinc/.venv` |
| Конфиг | `/opt/fit_sinc/.env` (не в git) |
| Данные | `/opt/fit_sinc/data/` (tokens, garth session, fits, SQLite) |

---

## Первичная настройка сервера (один раз)

```bash
# На сервере
apt install -y python3.12-venv apache2-utils nginx certbot python3-certbot-nginx

useradd -r -d /opt/fit_sinc -s /usr/sbin/nologin fit_sinc
mkdir -p /opt/fit_sinc/data/fits
chown -R fit_sinc:fit_sinc /opt/fit_sinc

# nginx + Basic Auth
htpasswd -nbB admin 'YOUR_PASSWORD' > /etc/nginx/.htpasswd_fit_sinc
chmod 640 /etc/nginx/.htpasswd_fit_sinc
chown root:www-data /etc/nginx/.htpasswd_fit_sinc

cp deploy/nginx/fit.conf /etc/nginx/conf.d/fit.conf
cp deploy/fit-sinc.service /etc/systemd/system/fit-sinc.service
nginx -t && systemctl reload nginx
systemctl enable --now fit-sinc
```

Certbot для `fit.romansegalla.online` — отдельно, если cert ещё не выпущен.

---

## Continuous Deployment (текущий процесс)

### 1. Код приложения

```bash
cd /Users/roman/fit_sinc

rsync -avz \
  --exclude '.venv' \
  --exclude '__pycache__' \
  --exclude '.git' \
  --exclude 'data' \
  --exclude '.env' \
  -e "ssh -i ~/.ssh/id_ed25519" \
  ./ root@sirocco.romansegalla.online:/opt/fit_sinc/

ssh -i ~/.ssh/id_ed25519 root@sirocco.romansegalla.online <<'EOF'
set -euo pipefail
chown -R fit_sinc:fit_sinc /opt/fit_sinc
sudo -u fit_sinc bash -c 'cd /opt/fit_sinc && .venv/bin/pip install -e .'
systemctl restart fit-sinc
sleep 2
systemctl is-active fit-sinc
curl -sf http://127.0.0.1:8080/health
EOF
```

**Не синхронизируем через rsync:** `.env`, `data/` — секреты и runtime-состояние.

### 2. Секреты и сессии (при смене или первом деплое)

```bash
# .env — client_id, webhook secret (без пароля Garmin, если уже есть session)
scp -i ~/.ssh/id_ed25519 .env root@sirocco.romansegalla.online:/opt/fit_sinc/

# OAuth tokens и Garmin session — после локального auth
scp -i ~/.ssh/id_ed25519 data/hammerhead_tokens.json \
  root@sirocco.romansegalla.online:/opt/fit_sinc/data/
scp -i ~/.ssh/id_ed25519 -r data/garth \
  root@sirocco.romansegalla.online:/opt/fit_sinc/data/

ssh -i ~/.ssh/id_ed25519 root@sirocco.romansegalla.online \
  'chown -R fit_sinc:fit_sinc /opt/fit_sinc && systemctl restart fit-sinc'
```

### 3. Локальная настройка auth (на Mac)

```bash
cd /Users/roman/fit_sinc
cp .env.example .env   # заполнить Hammerhead credentials
.venv/bin/fit_sinc hammerhead auth
.venv/bin/fit_sinc garmin login
```

Затем — шаг 2 (копирование `data/` на сервер).

---

## Проверка после деплоя

```bash
# Health (без auth)
curl -sk https://fit.romansegalla.online/health

# Webhook без подписи → 403
curl -sk -o /dev/null -w "%{http_code}\n" -X POST \
  https://fit.romansegalla.online/webhooks/hammerhead \
  -H "Content-Type: application/json" \
  -d '{"activityId":"test","userId":"192184"}'

# UI (с Basic Auth)
curl -sk -u admin:PASSWORD https://fit.romansegalla.online/

# На сервере
ssh root@sirocco.romansegalla.online \
  'systemctl status fit-sinc; journalctl -u fit-sinc -n 20 --no-pager'
```

---

## nginx: маршрутизация и auth

| Path | Auth | Назначение |
|------|------|------------|
| `/webhooks/*` | нет | Hammerhead webhook (HMAC в приложении) |
| `/health` | нет | Healthcheck |
| `/`, `/static/*`, `/favicon.ico` | Basic Auth | UI и статика |

Конфиг: [`deploy/nginx/fit.conf`](../deploy/nginx/fit.conf)

---

## systemd

Конфиг: [`deploy/fit-sinc.service`](../deploy/fit-sinc.service)

```bash
systemctl restart fit-sinc
systemctl status fit-sinc
journalctl -u fit-sinc -f
```

Приложение слушает только `127.0.0.1:8080` — порт 8080 наружу не открыт.

---

## Rollback

```bash
# На сервере — откат к предыдущей версии кода (если есть бэкап или git)
cd /opt/fit_sinc
# git checkout <prev-commit>  # когда появится git на сервере
sudo -u fit_sinc .venv/bin/pip install -e .
systemctl restart fit-sinc
```

Секреты и `data/` при rollback не трогаем.

---

## GitHub Actions (основной)

Конфиг: [`.github/workflows/ci.yml`](../.github/workflows/ci.yml), деплой: [`scripts/ci/deploy.sh`](../scripts/ci/deploy.sh).

```mermaid
flowchart LR
    Push[push / PR] --> Test[test: compileall + unittest]
    Main[push main] --> Test
    Test --> Deploy[deploy]
    Deploy --> VPS[sirocco rsync + restart]
```

| Job | Когда | Действие |
|-----|--------|----------|
| `test` | push и pull_request | `pip install -e .`, `compileall`, `tests/test_smoke.py` |
| `deploy` | push в `main` / `master` после test | rsync → `/opt/fit_sinc`, `pip install -e .`, `systemctl restart fit-sinc`, `/health` |

### Secrets и variables (GitHub → Settings → Secrets and variables → Actions)

| Имя | Тип | Описание |
|-----|-----|----------|
| `SSH_PRIVATE_KEY` | **Secret** | Полный текст приватного ключа (`~/.ssh/id_ed25519` или deploy-only key) |
| `FIT_SINC_SSH_HOST` | Variable (optional) | По умолчанию `sirocco.romansegalla.online` |
| `FIT_SINC_SSH_USER` | Variable (optional) | По умолчанию `root` |
| `FIT_SINC_DEPLOY_PATH` | Variable (optional) | По умолчанию `/opt/fit_sinc` |

Environment **production** (опционально): защита ветки / approval перед deploy.

**Не хранить в CI:** `.env`, `data/`, пароли Garmin — только на сервере.

**На сервере один раз:** venv, `.env`, tokens в `data/` (см. «Первичная настройка» и «Секреты»).

### Первый запуск

1. Репозиторий: https://github.com/segallar/fit-sinc
2. Secret `SSH_PRIVATE_KEY` в Settings → Secrets and variables → Actions.
3. Push в `main` — в Actions появятся `test` и `deploy`.

## GitLab CI (альтернатива)

Если зеркалируете на GitLab: [`.gitlab-ci.yml`](../.gitlab-ci.yml) — те же job'ы, переменная `SSH_PRIVATE_KEY` (тип File) в Settings → CI/CD → Variables.

### Локально прогнать то же, что CI

```bash
cd /Users/roman/fit_sinc
pip install -e .
python -m compileall -q fit_sinc
python -m unittest discover -s tests -p "test_*.py" -v
```

### Ручной deploy (без CI)

```bash
FIT_SINC_SSH_HOST=sirocco.romansegalla.online SSH_PRIVATE_KEY="$(cat ~/.ssh/id_ed25519)" ./scripts/ci/deploy.sh
```

Auth tokens (Hammerhead/Garmin) по-прежнему обновляются вручную через CLI, не через pipeline.

---

## Чеклист релиза

- [ ] Код задеплоен (`rsync` + `pip install -e .`)
- [ ] `systemctl is-active fit-sinc` → `active`
- [ ] `/health` → 200
- [ ] Webhook без HMAC → 403, с HMAC → 200
- [ ] Dashboard открывается с Basic Auth
- [ ] `fit_sinc hammerhead status` и `garmin status` на сервере → connected
