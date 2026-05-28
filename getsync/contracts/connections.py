"""Connection status DTO for Settings / registry UI."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ConnectionStatus:
    """Provider-agnostic connection state for one source or sink."""

    connected: bool
    label: str
    status_text: str
    status_variant: str  # success | warning | secondary | danger
    upload_ready: bool = False
    details: tuple[tuple[str, str], ...] = ()  # (label, value) pairs
