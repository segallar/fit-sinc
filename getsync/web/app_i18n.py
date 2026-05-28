"""Cabinet and auth UI strings (EN default; RU, DE)."""

from __future__ import annotations

from typing import Any

from getsync.users.locale import normalize_locale

_AUTH: dict[str, dict[str, Any]] = {}
_REGISTER: dict[str, dict[str, Any]] = {}
_CABINET: dict[str, dict[str, Any]] = {}


def auth_strings(lang: str | None) -> dict[str, Any]:
    return _AUTH.get(normalize_locale(lang), _AUTH["en"])


def register_strings(lang: str | None) -> dict[str, Any]:
    return _REGISTER.get(normalize_locale(lang), _REGISTER["en"])


def cabinet_strings(lang: str | None) -> dict[str, Any]:
    return _CABINET.get(normalize_locale(lang), _CABINET["en"])


def _register_auth(code: str, data: dict[str, Any]) -> None:
    _AUTH[code] = data


def _register_cabinet(code: str, data: dict[str, Any]) -> None:
    _CABINET[code] = data


def _register_register(code: str, data: dict[str, Any]) -> None:
    _REGISTER[code] = data


_register_register("en", {
    "html_lang": "en",
    "page_title": "Sign up — GetSync",
    "page_title_closed": "Registration closed — GetSync",
    "sign_up_h2": "Sign up",
    "intro": "Personal account for workout sync. Created automatically from your email.",
    "email_label": "Email",
    "display_name_label": "Display name (optional)",
    "password_label": "Password",
    "password_confirm_label": "Confirm password",
    "submit_button": "Create account",
    "already_have_account": "Already have an account?",
    "sign_in_link": "Sign in",
    "home_link": "Home",
    "login_link": "Login",
    "nav_language": "Language",
    "closed_h2": "Registration closed",
    "closed_body": (
        "You cannot create an account on the site right now. "
        "Ask a GetSync administrator for access, or sign in if you already have an account."
    ),
    "closed_sign_in": "Sign in",
    "closed_home": "Home",
    "error_rate_limit": "Too many attempts. Wait {wait} s.",
    "error_invalid_email": "Enter a valid email address.",
    "error_password_short": "Password must be at least {min_len} characters.",
    "error_password_mismatch": "Passwords do not match.",
    "error_email_taken": "An account with this email already exists. Sign in instead.",
    "error_create_failed": "Could not create the account. Try again later.",
})

_register_register("ru", {
    "html_lang": "ru",
    "page_title": "Регистрация — GetSync",
    "page_title_closed": "Регистрация недоступна — GetSync",
    "sign_up_h2": "Регистрация",
    "intro": "Личный аккаунт для синхронизации тренировок. Создаётся автоматически по email.",
    "email_label": "Email",
    "display_name_label": "Имя (необязательно)",
    "password_label": "Пароль",
    "password_confirm_label": "Повтор пароля",
    "submit_button": "Создать аккаунт",
    "already_have_account": "Уже есть аккаунт?",
    "sign_in_link": "Войти",
    "home_link": "Главная",
    "login_link": "Вход",
    "nav_language": "Язык",
    "closed_h2": "Регистрация недоступна",
    "closed_body": (
        "Сейчас нельзя создать аккаунт через сайт. "
        "Попросите администратора GetSync выдать доступ или войдите, если аккаунт уже есть."
    ),
    "closed_sign_in": "Войти",
    "closed_home": "На главную",
    "error_rate_limit": "Слишком много попыток. Подождите {wait} с.",
    "error_invalid_email": "Укажите корректный email.",
    "error_password_short": "Пароль не короче {min_len} символов.",
    "error_password_mismatch": "Пароли не совпадают.",
    "error_email_taken": "Аккаунт с таким email уже есть. Войдите или восстановите доступ.",
    "error_create_failed": "Не удалось создать аккаунт. Попробуйте позже.",
})

_register_register("de", {
    "html_lang": "de",
    "page_title": "Registrieren — GetSync",
    "page_title_closed": "Registrierung geschlossen — GetSync",
    "sign_up_h2": "Registrieren",
    "intro": "Persönliches Konto zur Trainingssynchronisation. Wird automatisch aus Ihrer E-Mail erstellt.",
    "email_label": "E-Mail",
    "display_name_label": "Anzeigename (optional)",
    "password_label": "Passwort",
    "password_confirm_label": "Passwort bestätigen",
    "submit_button": "Konto erstellen",
    "already_have_account": "Bereits ein Konto?",
    "sign_in_link": "Anmelden",
    "home_link": "Startseite",
    "login_link": "Anmelden",
    "nav_language": "Sprache",
    "closed_h2": "Registrierung geschlossen",
    "closed_body": (
        "Derzeit können Sie kein Konto auf der Website erstellen. "
        "Wenden Sie sich an einen GetSync-Administrator oder melden Sie sich an, "
        "wenn Sie bereits ein Konto haben."
    ),
    "closed_sign_in": "Anmelden",
    "closed_home": "Startseite",
    "error_rate_limit": "Zu viele Versuche. Warten Sie {wait} s.",
    "error_invalid_email": "Geben Sie eine gültige E-Mail-Adresse ein.",
    "error_password_short": "Passwort mindestens {min_len} Zeichen.",
    "error_password_mismatch": "Passwörter stimmen nicht überein.",
    "error_email_taken": "Diese E-Mail ist bereits registriert. Bitte anmelden.",
    "error_create_failed": "Konto konnte nicht erstellt werden. Bitte später erneut versuchen.",
})

_register_auth("en", {
    "html_lang": "en",
    "page_title": "Login — GetSync",
    "sign_in_h2": "Sign in",
    "email_label": "Email",
    "password_label": "Password",
    "sign_in_button": "Sign in",
    "error_invalid_credentials": "Invalid email or password",
    "no_account": "No account?",
    "sign_up_link": "Sign up",
    "home_link": "Home",
    "nav_language": "Language",
})

_register_auth("ru", {
    "html_lang": "ru",
    "page_title": "Вход — GetSync",
    "sign_in_h2": "Войти",
    "email_label": "Email",
    "password_label": "Пароль",
    "sign_in_button": "Войти",
    "error_invalid_credentials": "Неверный email или пароль",
    "no_account": "Нет аккаунта?",
    "sign_up_link": "Регистрация",
    "home_link": "Главная",
    "nav_language": "Язык",
})

_register_auth("de", {
    "html_lang": "de",
    "page_title": "Anmelden — GetSync",
    "sign_in_h2": "Anmelden",
    "email_label": "E-Mail",
    "password_label": "Passwort",
    "sign_in_button": "Anmelden",
    "error_invalid_credentials": "Ungültige E-Mail oder Passwort",
    "no_account": "Noch kein Konto?",
    "sign_up_link": "Registrieren",
    "home_link": "Startseite",
    "nav_language": "Sprache",
})

_register_cabinet("en", {
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
    "settings_connections_h3": "Connections",
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
    "flash_strava_connected": "Strava connected.",
    "flash_strava_disconnected": "Strava disconnected.",
    "flash_strava_not_configured": "Strava OAuth is not configured on the server.",
    "flash_strava_state": "Strava OAuth state invalid or expired.",
    "flash_strava_user_mismatch": "Strava OAuth user mismatch.",
    "flash_strava_exchange_failed": "Strava authorization failed. Try again.",
    "flash_garmin_refreshed": "Garmin session refresh requested.",
    "flash_garmin_disconnected": "Garmin sessions removed for this account.",
    "flash_garmin_connected": "Garmin Connect linked successfully.",
    "flash_garmin_connected_no_vault": (
        "Garmin linked. Sessions saved; auto re-login needs GETSYNC_SECRETS_KEY on the server."
    ),
    "flash_garmin_credentials_required": "Garmin email and password are required.",
    "flash_garmin_login_failed": "Garmin login failed. Check email and password.",
    "garmin_email": "Garmin email",
    "garmin_password": "Garmin password",
    "garmin_save_credentials": "Store password for automatic re-login",
    "garmin_connect": "Connect Garmin",
})

_register_cabinet("ru", {
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
    "settings_connections_h3": "Подключения",
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
    "flash_strava_connected": "Strava подключён.",
    "flash_strava_disconnected": "Strava отключён.",
    "flash_strava_not_configured": "Strava OAuth не настроен на сервере.",
    "flash_strava_state": "Strava OAuth: неверный или просроченный state.",
    "flash_strava_user_mismatch": "Strava OAuth: несовпадение пользователя.",
    "flash_strava_exchange_failed": "Не удалось авторизовать Strava. Попробуйте снова.",
    "flash_garmin_refreshed": "Запрошено обновление сессии Garmin.",
    "flash_garmin_disconnected": "Сессии Garmin удалены для этого аккаунта.",
    "flash_garmin_connected": "Garmin Connect успешно подключён.",
    "flash_garmin_connected_no_vault": (
        "Garmin подключён. Сессии сохранены; для авто-входа нужен GETSYNC_SECRETS_KEY на сервере."
    ),
    "flash_garmin_credentials_required": "Укажите email и пароль Garmin.",
    "flash_garmin_login_failed": "Не удалось войти в Garmin. Проверьте email и пароль.",
    "garmin_email": "Email Garmin",
    "garmin_password": "Пароль Garmin",
    "garmin_save_credentials": "Сохранить пароль для автоматического входа",
    "garmin_connect": "Подключить Garmin",
})

_register_cabinet("de", {
    "html_lang": "de",
    "nav_dashboard": "Dashboard",
    "nav_activities": "Aktivitäten",
    "nav_log": "Sync-Protokoll",
    "nav_session": "Garmin-Sitzung",
    "nav_settings": "Einstellungen",
    "nav_admin": "Admin",
    "logout": "Abmelden",
    "badge_admin": "Admin",
    "badge_disabled": "deaktiviert",
    "settings_title": "Einstellungen",
    "profile_h3": "Profil",
    "settings_connections_h3": "Verbindungen",
    "display_name": "Anzeigename",
    "email": "E-Mail",
    "telegram": "Telegram",
    "timezone_label": "Zeitzone",
    "locale_label": "Sprache",
    "save_profile": "Profil speichern",
    "slug_label": "Slug",
    "password_h3": "Passwort",
    "current_password": "Aktuelles Passwort",
    "new_password": "Neues Passwort",
    "confirm_password": "Passwort bestätigen",
    "change_password": "Passwort ändern",
    "flash_profile_saved": "Profil gespeichert.",
    "flash_password_changed": "Passwort aktualisiert.",
    "flash_hh_connected": "Hammerhead verbunden.",
    "flash_hh_disconnected": "Hammerhead getrennt.",
    "flash_strava_connected": "Strava verbunden.",
    "flash_strava_disconnected": "Strava getrennt.",
    "flash_strava_not_configured": "Strava OAuth ist auf dem Server nicht konfiguriert.",
    "flash_strava_state": "Strava OAuth: ungültiger oder abgelaufener State.",
    "flash_strava_user_mismatch": "Strava OAuth: Benutzer stimmt nicht überein.",
    "flash_strava_exchange_failed": "Strava-Autorisierung fehlgeschlagen. Erneut versuchen.",
    "flash_garmin_refreshed": "Garmin-Sitzung wird aktualisiert.",
    "flash_garmin_disconnected": "Garmin-Sitzungen für dieses Konto entfernt.",
    "flash_garmin_connected": "Garmin Connect erfolgreich verknüpft.",
    "flash_garmin_connected_no_vault": (
        "Garmin verknüpft. Sitzungen gespeichert; Auto-Login braucht GETSYNC_SECRETS_KEY auf dem Server."
    ),
    "flash_garmin_credentials_required": "Garmin-E-Mail und Passwort sind erforderlich.",
    "flash_garmin_login_failed": "Garmin-Anmeldung fehlgeschlagen. E-Mail und Passwort prüfen.",
    "garmin_email": "Garmin-E-Mail",
    "garmin_password": "Garmin-Passwort",
    "garmin_save_credentials": "Passwort für automatische Anmeldung speichern",
    "garmin_connect": "Garmin verbinden",
})


def flash_message(lang: str | None, msg_code: str) -> str | None:
    t = cabinet_strings(lang)
    mapping = {
        "profile_saved": t["flash_profile_saved"],
        "password_changed": t["flash_password_changed"],
        "hh_connected": t["flash_hh_connected"],
        "hh_disconnected": t["flash_hh_disconnected"],
        "strava_connected": t["flash_strava_connected"],
        "strava_disconnected": t["flash_strava_disconnected"],
        "garmin_refreshed": t["flash_garmin_refreshed"],
        "garmin_disconnected": t["flash_garmin_disconnected"],
        "garmin_connected": t["flash_garmin_connected"],
        "garmin_connected_no_vault": t["flash_garmin_connected_no_vault"],
    }
    return mapping.get(msg_code)
