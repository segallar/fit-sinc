"""User UI locale (EN default, RU supported)."""

from __future__ import annotations

DEFAULT_LOCALE = "en"
SUPPORTED_LOCALES = ("en", "ru")


def normalize_locale(value: str | None) -> str:
    if not value:
        return DEFAULT_LOCALE
    code = value.strip().lower().split("-", 1)[0]
    if code == "ru":
        return "ru"
    return "en"


def locale_label(code: str) -> str:
    if code == "ru":
        return "Русский"
    return "English"


def options_for_select(selected: str | None = None) -> list[tuple[str, str, bool]]:
    sel = normalize_locale(selected)
    return [
        (locale_label(code), code, code == sel) for code in SUPPORTED_LOCALES
    ]
