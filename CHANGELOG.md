# Changelog

Формат основан на [Keep a Changelog](https://keepachangelog.com/). Версии — [SemVer](https://semver.org/).

## [0.7.0] — в разработке

### Планируется

- **2.10** — sidebar и вёрстка кабинета
- **2.12** — Garmin login в Settings
- **2.13** — регрессионные тесты
- **2.14** — UX sync log в admin

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

MVP: Hammerhead → Garmin sync, multi-tenant, кабинет, регистрация. Детали — [PLAN-ARCHIVE.md](docs/PLAN-ARCHIVE.md).
