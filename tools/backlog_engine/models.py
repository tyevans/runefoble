"""Data models and enum definitions for the backlog execution engine."""

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any


class TaskStatus(StrEnum):
    PROPOSED = "proposed"
    READY = "ready"
    IN_PROGRESS = "in-progress"
    REVIEW = "review"
    COMPLETE = "complete"


@dataclass
class Task:
    id: str
    title: str
    status: TaskStatus
    file_path: Path
    dependencies: list[str] = field(default_factory=list)
    governing_adrs: list[str] = field(default_factory=list)
    claimed_by: str | None = None
    branch: str | None = None
    pr_url: str | None = None
    priority_rank: int = 999999
    raw_frontmatter: dict[str, Any] = field(default_factory=dict)
    body: str = ""

    @property
    def canonical_id(self) -> str:
        """Returns TASK-XXXX format."""
        clean = self.id.upper().replace("TASK-", "")
        return f"TASK-{clean.zfill(4)}"

    @property
    def slug(self) -> str:
        """File slug without directory or extension."""
        return self.file_path.stem
