# Хранилище активностей

> Статус: local ✅ · S3 — [PLAN.md](PLAN.md#33--s3) **3.3**.

## Принципы

1. **Изоляция tenant** — артефакты каждого пользователя только под `data/users/{user_id}/`.
2. **Логический ключ** — в SQLite `storage_key`, не абсолютный путь VPS (готовность к S3).
3. **Один контракт** — `StorageBackend` для local и будущего S3; код синка/UI не знает, где физически лежит файл.

## Раскладка на диске (local)

```text
data/users/{user_id}/
  activities/
    hammerhead/
      {external_id}.fit
    garmin/
      {external_id}.fit      # при появлении артефактов
  fits/                      # legacy; миграция → activities/hammerhead/
  hammerhead_tokens.json
  garmin_web/
  garth/
```

## Ключи объектов

| Поле | Пример |
|------|--------|
| `storage_key` (в БД) | `activities/hammerhead/ride-42.fit` |
| Полный ключ S3 (позже) | `{user_id}/activities/hammerhead/ride-42.fit` |
| Локальный путь | `data/users/{user_id}/activities/hammerhead/ride-42.fit` |

Функция: `getsync.storage.build_object_key(source, external_id, kind="fit")`.

## SQLite

Таблица `activities`:

- `(user_id, source, activity_id)` — каталог (метаданные + статус sync).
- `storage_key` — ссылка на FIT в `StorageBackend`.
- `fit_path` — **legacy**, абсолютный путь; постепенно выводится.

## Код

| Модуль | Назначение |
|--------|------------|
| [`getsync/storage/backend.py`](../getsync/storage/backend.py) | `StorageBackend`, `LocalFilesystemBackend`, заглушка `S3StorageBackend` |
| [`getsync/storage/activity.py`](../getsync/storage/activity.py) | `ActivityStorage` — per-user facade |
| [`getsync/storage/migrate.py`](../getsync/storage/migrate.py) | `fits/` → `activities/hammerhead/` |
| [`getsync/sync/service.py`](../getsync/sync/service.py) | `put_fit` после download HH |

## Конфигурация (`.env`)

```env
STORAGE_BACKEND=local
# Будущее:
# STORAGE_BACKEND=s3
# S3_BUCKET=getsync-prod
# S3_REGION=eu-central-1
# S3_ENDPOINT_URL=https://storage.yandexcloud.net
```

## Миграция

При старте [`migrate_legacy_files`](../getsync/users/migrate.py) копирует старый `data/fits/` в `users/{id}/fits/` и переносит `.fit` в `activities/hammerhead/` с заполнением `storage_key`.

## Дальше (фаза 11)

- Реализация `S3StorageBackend` (boto3).
- Signed URL для скачивания из UI.
- Опциональный LRU-кэш на VPS при `STORAGE_BACKEND=s3`.
- Таблица `activity_objects` для нескольких артефактов на активность (GPX, preview).

См. также [ARCHITECTURE.md](ARCHITECTURE.md), [PLAN.md](PLAN.md) §11.
