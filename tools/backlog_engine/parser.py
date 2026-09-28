"""Task markdown frontmatter parsing and priority map loading."""

import re
from pathlib import Path
from typing import Any

import yaml

from .models import Task, TaskStatus

FRONTMATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)


def parse_task_file(file_path: Path, priority_rank: int = 999999) -> Task:
    """Parses a task markdown file with YAML frontmatter."""
    text = file_path.read_text(encoding="utf-8")
    match = FRONTMATTER_PATTERN.match(text)

    if match:
        raw_yaml, body = match.groups()
        try:
            frontmatter: dict[str, Any] = yaml.safe_load(raw_yaml) or {}
        except Exception:
            frontmatter = {}
    else:
        frontmatter = {}
        body = text

    stem_match = re.match(r"^(\d+)", file_path.stem)
    raw_id = stem_match.group(1) if stem_match else str(frontmatter.get("id", ""))

    title = str(frontmatter.get("title", ""))
    if not title:
        title_match = re.search(r"^#\s+(.+)$", body, re.MULTILINE)
        title = title_match.group(1) if title_match else file_path.stem

    status_str = str(frontmatter.get("status", "")).lower()
    if status_str == "refined":
        status = TaskStatus.READY
    elif status_str in {s.value for s in TaskStatus}:
        status = TaskStatus(status_str)
    else:
        parent = file_path.parent.name
        if parent == "complete":
            status = TaskStatus.COMPLETE
        elif parent == "refined":
            status = TaskStatus.READY
        else:
            status = TaskStatus.PROPOSED

    raw_deps = frontmatter.get("dependencies", [])
    dependencies = []
    if isinstance(raw_deps, list):
        for dep in raw_deps:
            clean = str(dep).upper().replace("TASK-", "").strip()
            if clean.isdigit():
                dependencies.append(f"TASK-{clean.zfill(4)}")
            else:
                dependencies.append(str(dep).upper())

    adrs = frontmatter.get("governing_adrs", [])
    governing_adrs = [str(a) for a in adrs] if isinstance(adrs, list) else []

    return Task(
        id=raw_id,
        title=title,
        status=status,
        file_path=file_path,
        dependencies=dependencies,
        governing_adrs=governing_adrs,
        claimed_by=frontmatter.get("claimed_by"),
        branch=frontmatter.get("branch"),
        pr_url=frontmatter.get("pr_url"),
        priority_rank=priority_rank,
        raw_frontmatter=frontmatter,
        body=body,
    )


def load_priority_map(backlog_dir: Path) -> dict[str, int]:
    """Reads PRIORITY.md and maps canonical TASK-XXXX to rank index (0-indexed)."""
    priority_file = backlog_dir / "PRIORITY.md"
    ranks = {}
    if not priority_file.exists():
        return ranks

    content = priority_file.read_text(encoding="utf-8")
    pattern = re.compile(r"^\d+\.\s+\*\*TASK-(\d+)", re.MULTILINE)
    for rank, match in enumerate(pattern.finditer(content)):
        task_num = match.group(1).zfill(4)
        ranks[f"TASK-{task_num}"] = rank
    return ranks


__all__ = ["FRONTMATTER_PATTERN", "load_priority_map", "parse_task_file"]
