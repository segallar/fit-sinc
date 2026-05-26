"""Landing page copy (EN default, RU, DE)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from fastapi import Request

SUPPORTED_LANGS = ("en", "ru", "de")
DEFAULT_LANG = "en"
LANG_COOKIE = "getsync_lang"
LANG_LABELS: dict[str, str] = {
    "en": "English",
    "ru": "Русский",
    "de": "Deutsch",
}


def normalize_lang(value: str | None) -> str:
    if not value:
        return DEFAULT_LANG
    code = value.strip().lower().split("-", 1)[0]
    if code in SUPPORTED_LANGS:
        return code
    return DEFAULT_LANG


def lang_from_accept_language(header: str | None) -> str:
    if not header:
        return DEFAULT_LANG
    for part in header.split(","):
        code = part.split(";", 1)[0].strip().lower().split("-", 1)[0]
        if code in SUPPORTED_LANGS:
            return code
    return DEFAULT_LANG


def lang_from_request(request: Request, query_lang: str | None = None) -> str:
    if query_lang:
        return normalize_lang(query_lang)
    cookie = request.cookies.get(LANG_COOKIE)
    if cookie:
        return normalize_lang(cookie)
    return lang_from_accept_language(request.headers.get("accept-language"))


def landing_strings(lang: str) -> dict[str, Any]:
    return _COPY.get(normalize_lang(lang), _EN)


def landing_lang_options(selected: str | None = None) -> list[tuple[str, str, bool]]:
    sel = normalize_lang(selected)
    return [(LANG_LABELS[code], code, code == sel) for code in SUPPORTED_LANGS]


_EN: dict[str, Any] = {
    "html_lang": "en",
    "page_title": "GetSync — activity hub for athletes",
    "nav_benefits": "Benefits",
    "nav_faq": "FAQ",
    "nav_login": "Login",
    "nav_signup": "Sign up",
    "nav_language": "Language",
    "hero_title": "All your workouts in one place — synced where you need them",
    "hero_lead": (
        "GetSync collects activities from your devices and clouds, keeps a clear catalog "
        "in your account, and delivers files to the services you already use."
    ),
    "hero_cta_signup": "Sign up — free to start",
    "hero_cta_login": "Login",
    "hero_hint_closed": "New accounts are created by an admin. Already have access? Login.",
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
                "GetSync is a <strong>free</strong> activity hub for athletes: collect workouts, "
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
                "you get immediate access to the cabinet. "
                "Set timezone and language later in Settings. "
                "Otherwise ask the instance admin for an account."
            ),
        },
        {
            "q": "How much does it cost?",
            "a": (
                "GetSync is a <strong>free service</strong>. We do not charge subscription fees "
                "or usage tiers for GetSync. Hammerhead, Garmin, and other platforms have their "
                "own terms — GetSync only connects them for you."
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
    "nav_language": "Язык",
    "hero_title": "Все ваши тренировки в одном месте — и дальше куда нужно",
    "hero_lead": (
        "GetSync собирает активности с устройств и облаков, ведёт каталог в вашем аккаунте "
        "и доставляет файлы в нужные сервисы."
    ),
    "hero_cta_signup": "Sign up — бесплатный старт",
    "hero_cta_login": "Login",
    "hero_hint_closed": "Новые аккаунты создаёт администратор. Уже есть доступ — Login.",
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
                "GetSync — <strong>бесплатный</strong> хаб активностей для спортсменов: сбор тренировок, "
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
                "сразу попадаете в кабинет. Часовой пояс и язык — в настройках. "
                "Иначе — доступ через администратора."
            ),
        },
        {
            "q": "Сколько это стоит?",
            "a": (
                "GetSync — <strong>бесплатный сервис</strong>. Мы не берём плату за подписку "
                "или использование GetSync. У Hammerhead, Garmin и других платформ — свои условия; "
                "GetSync только связывает их для вас."
            ),
        },
    ],
    "cta_title": "Готовы перестать переносить .fit вручную?",
    "cta_lead_open": "Создайте аккаунт, подключите Hammerhead и Garmin — следующая поездка может синхронизироваться сама.",
    "cta_lead_closed": "Войдите в кабинет или запросите доступ у администратора.",
    "footer_health": "Проверка /health",
}

_DE: dict[str, Any] = {
    "html_lang": "de",
    "page_title": "GetSync — Aktivitäten-Hub für Sportler",
    "nav_benefits": "Vorteile",
    "nav_faq": "FAQ",
    "nav_login": "Anmelden",
    "nav_signup": "Registrieren",
    "nav_language": "Sprache",
    "hero_title": "Alle Trainings an einem Ort — synchronisiert, wohin Sie es brauchen",
    "hero_lead": (
        "GetSync sammelt Aktivitäten von Geräten und Clouds, führt ein klares Verzeichnis "
        "in Ihrem Konto und liefert Dateien an die Dienste, die Sie bereits nutzen."
    ),
    "hero_cta_signup": "Registrieren — kostenlos starten",
    "hero_cta_login": "Anmelden",
    "hero_hint_closed": "Neue Konten legt ein Administrator an. Bereits Zugang? Anmelden.",
    "benefits_title": "Für Sportler mit mehr als einer Plattform",
    "benefits_lead": (
        "Kein manuelles Kopieren von Dateien. GetSync wächst zu einem Hub: Import, Speicher, "
        "Status in der Oberfläche und Regeln, wohin jedes Training gehen soll."
    ),
    "benefits": [
        {
            "title": "Eine Pipeline, viele Ziele",
            "body": "Roadmap: Quellen (Hammerhead, Strava, Wahoo, …) und Ziele (Garmin, Archiv, …) mit Regeln pro Nutzer.",
        },
        {
            "title": "Jetzt live: Karoo → Garmin",
            "body": "Webhook nach der Fahrt, Original-.fit laden, Upload zu Garmin Connect — ohne doppelte Aktivitäten.",
        },
        {
            "title": "Ihre Daten, Ihr Konto",
            "body": "Mandantenfähiges Dashboard: OAuth pro Nutzer, isolierte Ablage unter data/users/{id}/, HTTPS-Sessions.",
        },
        {
            "title": "Transparenter Sync-Status",
            "body": "Erfolg, Überspringen und Fehler im Log. Bei Fehlern erneut aus der UI senden.",
        },
    ],
    "faq_title": "Häufige Fragen",
    "faq": [
        {
            "q": "Was ist GetSync?",
            "a": (
                "GetSync ist ein <strong>kostenloser</strong> Aktivitäten-Hub für Sportler: Trainings sammeln, "
                "Status im Web-Dashboard sehen und an verbundene Dienste senden. "
                "Der erste produktive Weg: Hammerhead Karoo → Garmin Connect."
            ),
        },
        {
            "q": "Welche Geräte und Dienste werden unterstützt?",
            "a": (
                "<strong>Jetzt in Production:</strong> Hammerhead (Karoo) als Quelle, Garmin Connect als Ziel. "
                "<strong>Auf der Roadmap:</strong> Strava, Wahoo, manueller FIT-Upload, weitere Ziele — siehe Projektplan. "
                "Wir versprechen keine Integrationen, die noch nicht ausgeliefert sind."
            ),
        },
        {
            "q": "Wie verbinde ich Hammerhead und Garmin?",
            "a": (
                "Registrieren, im Dashboard <strong>Settings</strong> öffnen, Hammerhead-OAuth abschließen, "
                "dann Garmin verknüpfen (erster Garmin-Login kann noch per CLI auf dem Server laufen — siehe Docs). "
                "Hammerhead-Webhook auf diese GetSync-Instanz zeigen."
            ),
        },
        {
            "q": "Wie funktioniert die Registrierung?",
            "a": (
                "Ist die öffentliche Anmeldung aktiv, nutzen Sie <strong>Registrieren</strong> auf dieser Seite — "
                "sofort Zugang zum Dashboard. Zeitzone und Sprache später unter Einstellungen. "
                "Sonst beim Administrator der Instanz ein Konto anfragen."
            ),
        },
        {
            "q": "Was kostet es?",
            "a": (
                "GetSync ist ein <strong>kostenloser Dienst</strong>. Wir erheben keine Abo- "
                "oder Nutzungsgebühren für GetSync. Hammerhead, Garmin und andere Plattformen "
                "haben eigene Bedingungen — GetSync verbindet sie nur für Sie."
            ),
        },
    ],
    "cta_title": "Schluss mit manuellem .fit-Verschieben?",
    "cta_lead_open": "Konto anlegen, Hammerhead und Garmin verbinden — die nächste Fahrt kann von selbst synchronisieren.",
    "cta_lead_closed": "Im Dashboard anmelden oder beim Administrator Zugang anfragen.",
    "footer_health": "Health-Check",
}

_COPY: dict[str, dict[str, Any]] = {
    "en": _EN,
    "ru": _RU,
    "de": _DE,
}
