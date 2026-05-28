"""Use-case test harness: HTTP flows over FastAPI TestClient (no network).

Maps to user journeys in docs/design/SCREENS.md and PLAN **2.13**.
Each flow exercises the app like a user (login → navigate → assert HTML/redirect).
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi.testclient import TestClient
from getsync.state.store import Store


@dataclass
class FlowSession:
    client: TestClient
    store: Store
    email: str
    password: str


def login(
    client: TestClient,
    email: str,
    password: str,
    *,
    expect_location: str = "/app/activities",
) -> None:
    r = client.post(
        "/app/login",
        data={"email": email, "password": password},
        follow_redirects=False,
    )
    if r.status_code != 303:
        raise AssertionError(f"login expected 303, got {r.status_code}: {r.text[:200]}")
    loc = r.headers.get("location") or ""
    if loc != expect_location:
        raise AssertionError(f"login redirect expected {expect_location!r}, got {loc!r}")


def logout(client: TestClient) -> None:
    r = client.get("/app/logout", follow_redirects=False)
    if r.status_code != 303:
        raise AssertionError(f"logout expected 303, got {r.status_code}")


def assert_redirect(
    client: TestClient,
    path: str,
    *,
    location: str,
    status: int = 303,
) -> None:
    r = client.get(path, follow_redirects=False)
    if r.status_code != status:
        raise AssertionError(f"GET {path} expected {status}, got {r.status_code}")
    loc = r.headers.get("location") or ""
    if loc != location:
        raise AssertionError(f"GET {path} expected Location {location!r}, got {loc!r}")


def assert_redirect_prefix(
    client: TestClient,
    path: str,
    *,
    location_prefix: str,
    status: int = 303,
) -> None:
    r = client.get(path, follow_redirects=False)
    if r.status_code != status:
        raise AssertionError(f"GET {path} expected {status}, got {r.status_code}")
    loc = r.headers.get("location") or ""
    if not loc.startswith(location_prefix):
        raise AssertionError(
            f"GET {path} expected Location starting with {location_prefix!r}, got {loc!r}"
        )


def seed_default_user(store: Store, email: str, password: str) -> str:
    store.ensure_default_user(email=email, password=password)
    row = store.get_user_by_email(email)
    assert row is not None
    return row.id


def seed_regular_user(
    store: Store,
    *,
    slug: str,
    email: str,
    password: str,
) -> str:
    row = store.create_user(
        slug=slug,
        display_name=slug.title(),
        email=email,
        password=password,
        is_admin=False,
    )
    return row.id
