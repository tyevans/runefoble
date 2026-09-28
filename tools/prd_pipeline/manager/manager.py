"""PRD pipeline manager orchestrating scanning, auditing, and lifecycle flows."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .auditor import RequirementAuditor
from .lifecycle import PRDLifecycle
from .models import AuditSummary, PRDRecord
from .scanner import PRDScanner


class PRDManager:
    """Manages PRD lifecycle files, audits, and registry synchronizations."""

    def __init__(self, repo_root: Path | str):
        self.repo_root = Path(repo_root).resolve()
        self.product_dir = self.repo_root / "docs" / "project" / "product"
        self.backlog_dir = self.repo_root / "docs" / "project" / "backlog"
        self.stories_dir = self.repo_root / "docs" / "project" / "user_stories"

        self.scanner = PRDScanner(self.product_dir)
        self.auditor = RequirementAuditor(self.backlog_dir)
        self.lifecycle = PRDLifecycle(self.product_dir)

    def list_prd_files(self) -> list[Path]:
        """Finds all PRD markdown files across product subdirectories."""
        return self.scanner.list_files()

    def load_prds(self) -> dict[str, PRDRecord]:
        """Loads and parses all PRD documents keyed by canonical ID."""
        return self.scanner.scan()

    def get_next_prd_number(self) -> int:
        """Determines the next available integer for PRD numbering."""
        return self.lifecycle.get_next_number(self.load_prds())

    def create_prd(
        self,
        title: str,
        persona: str,
        target_bc: str,
        summary: str,
        status: str = "Accepted",
        outcomes: list[str] | None = None,
    ) -> PRDRecord:
        """Creates a new PRD document in the target lifecycle directory."""
        next_num = self.get_next_prd_number()
        prd_id, file_path = self.lifecycle.create(
            title=title,
            persona=persona,
            target_bc=target_bc,
            summary=summary,
            status=status,
            outcomes=outcomes,
            next_num=next_num,
        )
        return self.scanner.parse_file(file_path)

    def update_prd_links(
        self,
        prd: PRDRecord,
        tasks: list[tuple[str, str, str]],
        stories: list[tuple[str, str, str]] | None = None,
    ) -> None:
        """Updates Linked User Stories and Implementing Backlog Tasks in a PRD file."""
        self.lifecycle.update_links(prd, tasks, stories)

    def audit_prds(self) -> dict[str, Any]:
        """Audits PRDs, finding undecomposed PRDs, stale links, and buffer health."""
        return self.auditor.audit(self.load_prds()).to_dict()

    def audit_summary(self) -> AuditSummary:
        """Audits PRDs and returns typed AuditSummary dataclass."""
        return self.auditor.audit(self.load_prds())
