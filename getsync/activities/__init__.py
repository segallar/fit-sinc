"""Backward-compat shim: re-export workspace + catalog APIs."""

from getsync.activities.browse import (  # noqa: F401
    ActivityBrowseRow,
    fetch_activities_page,
)
from getsync.activities.catalog import persist_browse_rows  # noqa: F401
from getsync.catalog.api import RefreshResult, get_catalog, refresh_from_providers  # noqa: F401

__all__ = [
    "ActivityBrowseRow",
    "RefreshResult",
    "fetch_activities_page",
    "get_catalog",
    "persist_browse_rows",
    "refresh_from_providers",
]
