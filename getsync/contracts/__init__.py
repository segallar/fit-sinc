"""Cross-module contracts: Protocols and normalized DTOs."""

from getsync.contracts.activities import (
    ActivityPage,
    ActivitySink,
    ActivitySource,
    ActivitySourceWithArtifacts,
    NormalizedActivity,
    UploadResult,
)
from getsync.contracts.connections import ConnectionStatus
from getsync.contracts.persistence import (
    ActivityCatalog,
    AuditLog,
    GarminSessionLog,
    SyncEventLog,
    SyncIndexEntry,
    UserRepository,
)

__all__ = [
    "ActivityCatalog",
    "ActivityPage",
    "ActivitySink",
    "ActivitySource",
    "ActivitySourceWithArtifacts",
    "AuditLog",
    "ConnectionStatus",
    "GarminSessionLog",
    "NormalizedActivity",
    "SyncEventLog",
    "SyncIndexEntry",
    "UploadResult",
    "UserRepository",
]
