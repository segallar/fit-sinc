# Changelog

> **Создано:** 2026-05-26 · **Обновлено:** 2026-05-28 · **Версия:** 0.7.0  
> Релизы продукта; версии в шапках `docs/` должны соответствовать актуальному содержанию.  

Формат основан на [Keep a Changelog](https://keepachangelog.com/). Версии — [SemVer](https://semver.org/).

## [0.7.0] — в разработке

### Added

- **2.16** — CredentialStore (Fernet), per-user `connections/garmin/`, auto re-login Garmin (`ensure_garmin_session`)
- Mail module: `getsync/mail`, backends `null` / `console` / `resend`, CLI `getsync mail test`
- CI: GitHub Actions `checkout@v6`, `setup-python@v6` (Node 24 runtime)
- Ops: prod без глобальных `GARMIN_EMAIL` / `GARMIN_PASSWORD`
- **2.12** — Garmin login в Settings: email/password, сохранение credentials (`POST /app/settings/garmin/login`)
- **2.13** (часть) — `tests/flows.py`, `test_user_cases.py` (guest/user/admin journeys)

### Removed

- Legacy DNS/host `fit.romansegalla.online` (nginx `fit.conf`, A-запись в зоне romansegalla)

### Планируется

- **2.10** — sidebar и вёрстка кабинета
- **2.13** — регрессия после **2.10**
- **2.14** — UX sync log в admin
- **2.6** — email verify при регистрации

---

## [0.6.0] — 2026-05-26

### Added

- Activities: календарь, фильтры дат/типа, infinite scroll
- Admin: **Sync log** (все tenants), **Garmin JWT log**
- Sync summary на Activities (без таблицы лога)
- Документация: [DATABASE.md](docs/DATABASE.md), расширенный [STORAGE.md](docs/STORAGE.md)
- Deploy: установка Playwright Chromium на VPS

### Changed

- Главный экран — `/app/activities` (Dashboard снят)
- `/app/log` → `/app/admin/sync-log`
- Редиректы: `/app/` → activities; логин → activities
- Roadmap пересобран: единая нумерация задач ([PLAN.md](docs/PLAN.md))

### Removed

- Runtime legacy: `fit_sinc_session`, `fit_sinc.db`, миграции `fits/`, колонка `fit_path` в API
- `connections_banner`, ui-preview dashboard, nginx `fit.conf`
- Env fallback `FIT_SINC_*` в deploy

### Fixed

- Фильтры Activities (даты в URL vs отображение)
- Footer: version/commit как строки, не объекты функций
- CI: `permissions: contents: read` для checkout

---

## [0.5.0] — ранее

MVP: Hammerhead → Garmin sync, multi-tenant, кабинет, регистрация. Детали — [PLAN-ARCHIVE.md](docs/archive/PLAN-ARCHIVE.md).
