"""Domain models and data structures for PRD lifecycle management."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any


class PRDStage(StrEnum):
    """PRD lifecycle stage directories."""

    IDEA = "idea"
    SHAPED = "shaped"
    ACCEPTED = "accepted"
    SHIPPED = "shipped"


@dataclass
class PRDRecord:
    """Canonical PRD document model parsed from disk."""

    id: str
    number: int
    title: str
    status: PRDStage | str
    created: str
    file_path: Path
    who_for: str = ""
    problem_statement: str = ""
    good_looks_like: list[str] = field(default_factory=list)
    does_not_do: list[str] = field(default_factory=list)
    costs_at_scale: str = ""
    checkable_outcomes: list[str] = field(default_factory=list)
    linked_stories: list[str] = field(default_factory=list)
    implementing_tasks: list[str] = field(default_factory=list)
    raw_frontmatter: dict[str, Any] = field(default_factory=dict)
    body: str = ""
    target_bc: str = "platform"

    @property
    def canonical_id(self) -> str:
        clean = self.id.upper().replace("PRD-", "")
        return f"PRD-{clean.zfill(4)}"

    @property
    def slug(self) -> str:
        return self.file_path.stem


PRD = PRDRecord


@dataclass
class AuditSummary:
    """Audit metrics across PRD lifecycle and backlog task buffers."""

    total_prds: int = 0
    undecomposed_prds: list[str] = field(default_factory=list)
    underdecomposed_prds: list[str] = field(default_factory=list)
    stale_task_links: list[dict[str, str]] = field(default_factory=list)
    epic_proposed_tasks: list[dict[str, Any]] = field(default_factory=list)
    buffer: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_prds": self.total_prds,
            "undecomposed_prds": self.undecomposed_prds,
            "underdecomposed_prds": self.underdecomposed_prds,
            "stale_task_links": self.stale_task_links,
            "epic_proposed_tasks": self.epic_proposed_tasks,
            "buffer": dict(self.buffer),
        }

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)

    def get(self, item: str, default: Any = None) -> Any:
        return getattr(self, item, default)

    def __contains__(self, item: str) -> bool:
        return hasattr(self, item)
