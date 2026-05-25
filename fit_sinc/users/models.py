from dataclasses import dataclass


@dataclass(frozen=True)
class UserRow:
    id: str
    slug: str
    display_name: str
    email: str
    telegram: str | None
    timezone: str
    hammerhead_user_id: str | None
    disabled: bool
    created_at: str
    updated_at: str
