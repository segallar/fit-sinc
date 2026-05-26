"""User UI locale (EN default; RU, DE for landing and profile)."""

from __future__ import annotations

DEFAULT_LOCALE = "en"
SUPPORTED_LOCALES = ("en", "ru", "de")

_LOCALE_LABELS = {
    "en": "English",
    "ru": "Русский",
    "de": "Deutsch",
}


def normalize_locale(value: str | None) -> str:
    if not value:
        return DEFAULT_LOCALE
    code = value.strip().lower().split("-", 1)[0]
    if code in SUPPORTED_LOCALES:
        return code
    return DEFAULT_LOCALE


def locale_label(code: str) -> str:
    return _LOCALE_LABELS.get(normalize_locale(code), _LOCALE_LABELS["en"])


def options_for_select(selected: str | None = None) -> list[tuple[str, str, bool]]:
    sel = normalize_locale(selected)
    return [
        (locale_label(code), code, code == sel) for code in SUPPORTED_LOCALES
    ]
