"""PRD pipeline manager facade maintaining backwards compatibility."""

from __future__ import annotations

from .manager import (
    PRD,
    AuditSummary,
    PRDLifecycle,
    PRDManager,
    PRDRecord,
    PRDScanner,
    PRDStage,
    RequirementAuditor,
)

__all__ = [
    "AuditSummary",
    "PRD",
    "PRDLifecycle",
    "PRDManager",
    "PRDRecord",
    "PRDScanner",
    "PRDStage",
    "RequirementAuditor",
]
