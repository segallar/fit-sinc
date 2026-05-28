"""Provider registry and adapters (integrations layer)."""

from getsync.providers.bootstrap import register_default_providers
from getsync.providers.registry import get_sink, get_source, list_sinks, list_sources

__all__ = [
    "get_sink",
    "get_source",
    "list_sinks",
    "list_sources",
    "register_default_providers",
]
