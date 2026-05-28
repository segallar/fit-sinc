from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from getsync.config import Settings, get_settings

DEFAULT_USER_ID = "default"


@dataclass(frozen=True)
class UserContext:
    """Per-tenant paths and identity."""

    user_id: str
    settings: Settings

    @property
    def user_data_dir(self) -> Path:
        return self.settings.data_dir / "users" / self.user_id

    @property
    def hammerhead_tokens_path(self) -> Path:
        return self.user_data_dir / "hammerhead_tokens.json"

    @property
    def strava_tokens_path(self) -> Path:
        return self.user_data_dir / "strava_tokens.json"

    @property
    def garth_dir(self) -> Path:
        return self.user_data_dir / "garth"

    @property
    def garmin_web_dir(self) -> Path:
        return self.user_data_dir / "garmin_web"

    @property
    def activities_dir(self) -> Path:
        """Per-user activity artifacts (FIT/GPX): activities/{source}/…"""
        return self.user_data_dir / "activities"

    def activity_storage(self) -> "ActivityStorage":
        from getsync.storage.activity import ActivityStorage

        return ActivityStorage(self)

    @property
    def db_path(self) -> Path:
        return self.settings.db_path


def resolve_user_context(user_id: str | None = None) -> UserContext:
    settings = get_settings()
    uid = (user_id or settings.default_user_id or DEFAULT_USER_ID).strip()
    return UserContext(user_id=uid, settings=settings)


def as_context(ctx: UserContext | None = None, user_id: str | None = None) -> UserContext:
    if ctx is not None:
        return ctx
    return resolve_user_context(user_id)
