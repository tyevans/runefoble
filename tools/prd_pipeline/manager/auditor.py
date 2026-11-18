"""Requirement auditing, INVEST criteria evaluation, and gap detection."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from tools.project_visualizer.markdown_utils import extract_section

from .models import AuditSummary, PRDRecord

# Scope rule for proposed tasks (docs/how-to/decompose-prds-into-vertical-slices.md).
# A proposed task is an epic when its Scope of Work has more than EPIC_SCOPE_ITEM_LIMIT
# top-level entries, or names more than EPIC_COMPONENT_LIMIT component roots
# (services/<bc>, gateway/<x>, frontend).
EPIC_SCOPE_ITEM_LIMIT = 8
EPIC_COMPONENT_LIMIT = 1
_COMPONENT_PATTERN = re.compile(r"\b(services/[a-z_]+|gateway/[a-z_]+|frontend)\b")
_TOP_LEVEL_ITEM = re.compile(r"^(?:\d+\.|[-*])\s")

# Ready buffer bands (specops.toml buffer_target 10, buffer_warning_threshold 6).
BUFFER_LOW_THRESHOLD = 6
BUFFER_HIGH_THRESHOLD = 12


def _top_level_items(section: str) -> list[str]:
    """Counts unindented scope entries. Nested bullets are details of one entry."""
    return [line for line in section.splitlines() if _TOP_LEVEL_ITEM.match(line)]


class RequirementAuditor:
    """Audits PRDs for INVEST criteria, task linking verification, and buffer health."""

    def __init__(self, backlog_dir: Path | str):
        self.backlog_dir = Path(backlog_dir).resolve()

    def _get_stage_tasks(self, stage: str) -> list[Path]:
        target = self.backlog_dir / stage
        return list(target.glob("*.md")) if target.exists() else []

    def _find_epic_tasks(self, proposed_tasks: list[Path]) -> list[dict[str, Any]]:
        epics: list[dict[str, Any]] = []
        for tp in proposed_tasks:
            content = tp.read_text(encoding="utf-8")
            scope = extract_section(content, "Scope of Work")
            scope_items = _top_level_items(scope)
            components = set(_COMPONENT_PATTERN.findall(scope))
            if len(scope_items) > EPIC_SCOPE_ITEM_LIMIT or len(components) > EPIC_COMPONENT_LIMIT:
                m = re.search(r"(\d{4})", tp.stem)
                tid = f"TASK-{m.group(1)}" if m else tp.stem
                epics.append(
                    {
                        "id": tid,
                        "file": tp.name,
                        "title": tp.stem,
                        "scope_count": len(scope_items),
                        "component_count": len(components),
                    }
                )
        return epics

    def _find_stale_links(
        self, prds: dict[str, PRDRecord], task_map: dict[str, Path]
    ) -> list[dict[str, str]]:
        stale_links: list[dict[str, str]] = []
        for prd in prds.values():
            for tid in prd.implementing_tasks:
                if tid in task_map:
                    actual = task_map[tid]
                    expected_rel = f"../../backlog/{actual.parent.name}/{actual.name}"
                    if expected_rel not in prd.body and actual.parent.name != "proposed":
                        for old_dir in ["refined", "proposed", "complete"]:
                            if (
                                f"../../backlog/{old_dir}/{actual.name}" in prd.body
                                and old_dir != actual.parent.name
                            ):
                                stale_links.append(
                                    {
                                        "prd": prd.canonical_id,
                                        "task": tid,
                                        "referenced": f"{old_dir}/{actual.name}",
                                        "actual": f"{actual.parent.name}/{actual.name}",
                                    }
                                )
        return stale_links

    def audit(self, prds: dict[str, PRDRecord]) -> AuditSummary:
        """Audits PRDs, detecting undecomposed PRDs, stale links, and buffer health."""
        complete_tasks = self._get_stage_tasks("complete")
        refined_tasks = self._get_stage_tasks("refined")
        proposed_tasks = self._get_stage_tasks("proposed")

        task_map: dict[str, Path] = {}
        for tp in [*complete_tasks, *refined_tasks, *proposed_tasks]:
            if m := re.search(r"(\d{4})", tp.stem):
                task_map[f"TASK-{m.group(1)}"] = tp

        undecomposed = [
            p.canonical_id
            for p in prds.values()
            if p.status.lower() in ["accepted", "shaped"] and len(p.implementing_tasks) == 0
        ]
        underdecomposed = [
            p.canonical_id
            for p in prds.values()
            if p.status.lower() in ["accepted", "shaped"] and 0 < len(p.implementing_tasks) <= 2
        ]

        return AuditSummary(
            total_prds=len(prds),
            undecomposed_prds=undecomposed,
            underdecomposed_prds=underdecomposed,
            stale_task_links=self._find_stale_links(prds, task_map),
            epic_proposed_tasks=self._find_epic_tasks(proposed_tasks),
            buffer={
                "complete": len(complete_tasks),
                "refined": len(refined_tasks),
                "proposed": len(proposed_tasks),
                "ready_buffer_low": len(refined_tasks) < BUFFER_LOW_THRESHOLD,
                "ready_buffer_high": len(refined_tasks) > BUFFER_HIGH_THRESHOLD,
            },
        )
