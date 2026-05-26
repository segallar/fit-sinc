"""Landing page copy (EN default, RU secondary)."""

from __future__ import annotations

from typing import Any

SUPPORTED_LANGS = ("en", "ru")
DEFAULT_LANG = "en"
LANG_COOKIE = "getsync_lang"


def normalize_lang(value: str | None) -> str:
    if value and value.lower().startswith("ru"):
        return "ru"
    return "en"


def landing_strings(lang: str) -> dict[str, Any]:
    if lang == "ru":
        return _RU
    return _EN


_EN: dict[str, Any] = {
    "html_lang": "en",
    "page_title": "GetSync — activity hub for athletes",
    "nav_benefits": "Benefits",
    "nav_faq": "FAQ",
    "nav_login": "Login",
    "nav_signup": "Sign up",
    "hero_badge": "Activity hub · Hammerhead → Garmin live today",
    "hero_title": "All your workouts in one place — synced where you need them",
    "hero_lead": (
        "GetSync collects activities from your devices and clouds, keeps a clear catalog "
        "in your account, and delivers files to the services you already use. "
        "Today: automatic Hammerhead Karoo → Garmin Connect with original .fit files."
    ),
    "hero_cta_signup": "Sign up — free to start",
    "hero_cta_login": "Login",
    "hero_hint_open": "After signup, connect Hammerhead and Garmin in Settings.",
    "hero_hint_closed": "New accounts are created by an admin. Already have access? Login.",
    "preview_label": "Product preview",
    "preview_title": "Cabinet screenshots coming soon",
    "preview_body": "Dashboard, activity list, and sync log — right here on the landing page.",
    "benefits_title": "Built for athletes who use more than one platform",
    "benefits_lead": (
        "Stop copying files by hand. GetSync is growing into a hub: ingest, storage, "
        "status in the UI, and rules for where each workout should go."
    ),
    "benefits": [
        {
            "title": "One pipeline, many destinations",
            "body": "Roadmap: sources (Hammerhead, Strava, Wahoo, …) and sinks (Garmin, archive, …) with per-user rules.",
        },
        {
            "title": "Live today: Karoo → Garmin",
            "body": "Webhook after your ride, download the original .fit, upload to Garmin Connect — no duplicate activities.",
        },
        {
            "title": "Your data, your account",
            "body": "Multi-tenant cabinet: OAuth per user, isolated storage under data/users/{id}/, session auth over HTTPS.",
        },
        {
            "title": "Transparent sync status",
            "body": "See success, skip, and errors in the log. Re-sync from the UI when something failed.",
        },
    ],
    "faq_title": "Frequently asked questions",
    "faq": [
        {
            "q": "What is GetSync?",
            "a": (
                "GetSync is a self-hosted activity hub for athletes: collect workouts, "
                "view status in a web cabinet, and push them to connected services. "
                "The first production path is Hammerhead Karoo → Garmin Connect."
            ),
        },
        {
            "q": "Which devices and services are supported?",
            "a": (
                "<strong>In production now:</strong> Hammerhead (Karoo) as a source, Garmin Connect as a sink. "
                "<strong>On the roadmap:</strong> Strava, Wahoo, manual FIT upload, more sinks — see the project plan. "
                "We do not claim integrations that are not shipped yet."
            ),
        },
        {
            "q": "How do I connect Hammerhead and Garmin?",
            "a": (
                "Sign up, open <strong>Settings</strong> in the cabinet, complete Hammerhead OAuth, "
                "then link Garmin (first Garmin login may still use CLI on the server — see docs). "
                "Point your Hammerhead webhook to this GetSync instance."
            ),
        },
        {
            "q": "How does registration work?",
            "a": (
                "When public signup is enabled, use <strong>Sign up</strong> on this page — "
                "you get a personal slug, timezone, and immediate access to the cabinet. "
                "Otherwise ask the instance admin for an account."
            ),
        },
        {
            "q": "How much does it cost?",
            "a": (
                "GetSync is <strong>free to run for yourself</strong>: deploy on your VPS or home server "
                "(self-hosted). You pay only for hosting and API access to third-party services. "
                "There are no GetSync subscription tiers today."
            ),
        },
    ],
    "cta_title": "Ready to stop moving .fit files by hand?",
    "cta_lead_open": "Create an account, connect Hammerhead and Garmin — the next ride can sync on its own.",
    "cta_lead_closed": "Log in to the cabinet or ask your administrator for access.",
    "footer_health": "Health check",
}

_RU: dict[str, Any] = {
    "html_lang": "ru",
    "page_title": "GetSync — хаб активностей для спортсменов",
    "nav_benefits": "Преимущества",
    "nav_faq": "Вопросы",
    "nav_login": "Login",
    "nav_signup": "Sign up",
    "hero_badge": "Хаб активностей · Hammerhead → Garmin уже в проде",
    "hero_title": "Все ваши тренировки в одном месте — и дальше куда нужно",
    "hero_lead": (
        "GetSync собирает активности с устройств и облаков, ведёт каталог в вашем аккаунте "
        "и доставляет файлы в нужные сервисы. Сейчас в production: автоматический "
        "Hammerhead Karoo → Garmin Connect с оригинальными .fit."
    ),
    "hero_cta_signup": "Sign up — бесплатный старт",
    "hero_cta_login": "Login",
    "hero_hint_open": "После регистрации подключите Hammerhead и Garmin в Settings.",
    "hero_hint_closed": "Новые аккаунты создаёт администратор. Уже есть доступ — Login.",
    "preview_label": "Превью продукта",
    "preview_title": "Скриншоты кабинета — скоро",
    "preview_body": "Дашборд, список активностей и лог синхронизации появятся на этой странице.",
    "benefits_title": "Для спортсменов на нескольких платформах",
    "benefits_lead": (
        "Без ручного копирования файлов. GetSync развивается как хаб: приём, хранение, "
        "статусы в UI и правила, куда отправлять каждую тренировку."
    ),
    "benefits": [
        {
            "title": "Один pipeline — разные приёмники",
            "body": "В планах: источники (Hammerhead, Strava, Wahoo, …) и приёмники (Garmin, архив, …) с правилами per user.",
        },
        {
            "title": "Уже работает: Karoo → Garmin",
            "body": "Webhook после поездки, оригинальный .fit, загрузка в Garmin Connect — без дубликатов.",
        },
        {
            "title": "Ваши данные, ваш аккаунт",
            "body": "Мультиарендный кабинет: OAuth на пользователя, изоляция в data/users/{id}/, сессии по HTTPS.",
        },
        {
            "title": "Понятный статус sync",
            "body": "Успех, пропуск и ошибки в логе. Re-sync из UI при сбое.",
        },
    ],
    "faq_title": "Частые вопросы",
    "faq": [
        {
            "q": "Что такое GetSync?",
            "a": (
                "GetSync — self-hosted хаб активностей для спортсменов: сбор тренировок, "
                "кабинет со статусами и доставка в подключённые сервисы. "
                "Первый рабочий сценарий — Hammerhead Karoo → Garmin Connect."
            ),
        },
        {
            "q": "Какие устройства и сервисы поддерживаются?",
            "a": (
                "<strong>Сейчас в production:</strong> Hammerhead (Karoo) как источник, Garmin Connect как приёмник. "
                "<strong>В планах:</strong> Strava, Wahoo, ручной FIT, другие приёмники — см. roadmap. "
                "Мы не обещаем интеграции, которых ещё нет в коде."
            ),
        },
        {
            "q": "Как подключить Hammerhead и Garmin?",
            "a": (
                "Зарегистрируйтесь, откройте <strong>Settings</strong>, пройдите OAuth Hammerhead, "
                "привяжите Garmin (первый вход Garmin может быть через CLI на сервере — см. docs). "
                "Укажите webhook Hammerhead на этот инстанс GetSync."
            ),
        },
        {
            "q": "Как устроена регистрация?",
            "a": (
                "Если открыта публичная регистрация — кнопка <strong>Sign up</strong> на этой странице: "
                "личный slug, часовой пояс и сразу кабинет. Иначе — доступ через администратора."
            ),
        },
        {
            "q": "Сколько это стоит?",
            "a": (
                "GetSync <strong>бесплатен для self-hosted</strong>: разверните на своём VPS или домашнем сервере. "
                "Вы платите только за хостинг и доступ к API сторонних сервисов. "
                "Подписок GetSync сейчас нет."
            ),
        },
    ],
    "cta_title": "Готовы перестать переносить .fit вручную?",
    "cta_lead_open": "Создайте аккаунт, подключите Hammerhead и Garmin — следующая поездка может синхронизироваться сама.",
    "cta_lead_closed": "Войдите в кабинет или запросите доступ у администратора.",
    "footer_health": "Проверка /health",
}
