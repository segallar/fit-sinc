from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    data_dir: Path = Path("data")

    hammerhead_client_id: str = ""
    hammerhead_client_secret: str = ""
    hammerhead_webhook_secret: str = ""
    hammerhead_redirect_uri: str = "http://127.0.0.1:8765/callback"
    hammerhead_web_redirect_uri: str = ""
    hammerhead_scope: str = "activity:read"

    garmin_email: str = ""
    garmin_password: str = ""

    garmin_jwt_refresh_interval_sec: int = 1800
    garmin_jwt_refresh_before_sec: int = 3600

    session_secret: str = "change-me-in-production"

    default_user_id: str = "default"
    registration_open: bool = False
    bootstrap_admin_email: str = ""

    @property
    def hammerhead_tokens_path(self) -> Path:
        """Legacy v1 path; prefer UserContext.hammerhead_tokens_path."""
        return self.data_dir / "hammerhead_tokens.json"

    @property
    def garth_dir(self) -> Path:
        return self.data_dir / "garth"

    @property
    def fits_dir(self) -> Path:
        return self.data_dir / "fits"

    @property
    def db_path(self) -> Path:
        return self.data_dir / "fit_sinc.db"


@lru_cache
def get_settings() -> Settings:
    return Settings()
