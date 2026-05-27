from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    data_dir: Path = Path("data")

    # Activity artifacts: local | s3 (S3 adapter — phase 11.1)
    storage_backend: str = "local"
    s3_bucket: str = ""
    s3_region: str = ""
    s3_endpoint_url: str = ""
    s3_prefix: str = ""

    hammerhead_client_id: str = ""
    hammerhead_client_secret: str = ""
    hammerhead_webhook_secret: str = ""
    hammerhead_redirect_uri: str = "http://127.0.0.1:8765/callback"
    hammerhead_web_redirect_uri: str = ""
    hammerhead_scope: str = "activity:read"

    # Legacy global fallback — prefer per-user store (2.16); avoid on multi-tenant prod
    garmin_email: str = ""
    garmin_password: str = ""

    # Fernet key for data/users/{id}/connections/*/secrets.enc (44-char url-safe base64)
    getsync_secrets_key: str = ""

    garmin_jwt_refresh_interval_sec: int = 1800
    garmin_jwt_refresh_before_sec: int = 3600

    session_secret: str = "change-me-in-production"
    session_cookie_secure: bool = False

    default_user_id: str = "default"
    registration_open: bool = False
    bootstrap_admin_email: str = ""

    # Email (2.1e) — MAIL_BACKEND=null in dev/CI unless configured
    mail_backend: str = "null"
    resend_api_key: str = ""
    mail_from: str = "GetSync <noreply@getsync.me>"
    mail_reply_to: str = ""
    app_public_url: str = "http://127.0.0.1:8765"

    # Logging: stderr always; file under data/logs/ when log_to_file=true
    log_to_file: bool = True
    log_file: Path | None = None
    log_level: str = "INFO"
    log_max_bytes: int = 5_000_000
    log_backup_count: int = 5

    @property
    def resolved_log_file(self) -> Path | None:
        if not self.log_to_file:
            return None
        if self.log_file is not None and str(self.log_file).strip():
            path = Path(self.log_file)
            return path if path.is_absolute() else self.data_dir / path
        return self.data_dir / "logs" / "getsync.log"

    @property
    def hammerhead_tokens_path(self) -> Path:
        """Legacy v1 path; prefer UserContext.hammerhead_tokens_path."""
        return self.data_dir / "hammerhead_tokens.json"

    @property
    def garth_dir(self) -> Path:
        return self.data_dir / "garth"

    @property
    def db_path(self) -> Path:
        return self.data_dir / "getsync.db"

    def session_secret_is_default(self) -> bool:
        return self.session_secret.strip() in (
            "",
            "change-me-in-production",
            "change-me-in-production-use-long-random-string",
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
