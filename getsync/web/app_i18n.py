"""Cabinet UI strings (EN default, RU secondary)."""

from __future__ import annotations

from typing import Any

from getsync.users.locale import DEFAULT_LOCALE, normalize_locale


def cabinet_strings(lang: str | None) -> dict[str, Any]:
    if normalize_locale(lang) == "ru":
        return _RU
    return _EN


_EN: dict[str, Any] = {
    "html_lang": "en",
    "nav_dashboard": "Dashboard",
    "nav_activities": "Activities",
    "nav_log": "Sync log",
    "nav_session": "Garmin session",
    "nav_settings": "Settings",
    "nav_admin": "Admin",
    "logout": "Logout",
    "badge_admin": "admin",
    "badge_disabled": "disabled",
    "settings_title": "Settings",
    "profile_h3": "Profile",
    "display_name": "Display name",
    "email": "Email",
    "telegram": "Telegram",
    "timezone_label": "Timezone",
    "locale_label": "Language",
    "save_profile": "Save profile",
    "slug_label": "Slug",
    "password_h3": "Password",
    "current_password": "Current password",
    "new_password": "New password",
    "confirm_password": "Confirm new password",
    "change_password": "Change password",
    "flash_profile_saved": "Profile saved.",
    "flash_password_changed": "Password updated.",
    "flash_hh_connected": "Hammerhead connected.",
    "flash_hh_disconnected": "Hammerhead disconnected.",
    "flash_garmin_refreshed": "Garmin session refresh requested.",
    "flash_garmin_disconnected": "Garmin sessions removed for this account.",
}

_RU: dict[str, Any] = {
    "html_lang": "ru",
    "nav_dashboard": "Дашборд",
    "nav_activities": "Активности",
    "nav_log": "Лог sync",
    "nav_session": "Сессия Garmin",
    "nav_settings": "Настройки",
    "nav_admin": "Админка",
    "logout": "Выйти",
    "badge_admin": "админ",
    "badge_disabled": "отключён",
    "settings_title": "Настройки",
    "profile_h3": "Профиль",
    "display_name": "Имя",
    "email": "Email",
    "telegram": "Telegram",
    "timezone_label": "Часовой пояс",
    "locale_label": "Язык интерфейса",
    "save_profile": "Сохранить профиль",
    "slug_label": "Slug",
    "password_h3": "Пароль",
    "current_password": "Текущий пароль",
    "new_password": "Новый пароль",
    "confirm_password": "Подтвердите пароль",
    "change_password": "Сменить пароль",
    "flash_profile_saved": "Профиль сохранён.",
    "flash_password_changed": "Пароль обновлён.",
    "flash_hh_connected": "Hammerhead подключён.",
    "flash_hh_disconnected": "Hammerhead отключён.",
    "flash_garmin_refreshed": "Запрошено обновление сессии Garmin.",
    "flash_garmin_disconnected": "Сессии Garmin удалены для этого аккаунта.",
}


def flash_message(lang: str | None, msg_code: str) -> str | None:
    t = cabinet_strings(lang)
    mapping = {
        "profile_saved": t["flash_profile_saved"],
        "password_changed": t["flash_password_changed"],
        "hh_connected": t["flash_hh_connected"],
        "hh_disconnected": t["flash_hh_disconnected"],
        "garmin_refreshed": t["flash_garmin_refreshed"],
        "garmin_disconnected": t["flash_garmin_disconnected"],
    }
    return mapping.get(msg_code)
