"""Backlog queue parsing, dependency resolution, and state transitions."""

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

    # Extract ID: Prioritize filename stem digits to prevent YAML 1.1 octal parsing bugs (e.g. 0024 -> 20)
    stem_match = re.match(r"^(\d+)", file_path.stem)
    raw_id = stem_match.group(1) if stem_match else str(frontmatter.get("id", ""))

    # Extract Title
    title = str(frontmatter.get("title", ""))
    if not title:
        # Try finding # TASK-XXXX — Title
        title_match = re.search(r"^#\s+(.+)$", body, re.MULTILINE)
        title = title_match.group(1) if title_match else file_path.stem

    # Extract Status
    status_str = str(frontmatter.get("status", "")).lower()
    if status_str in {s.value for s in TaskStatus}:
        status = TaskStatus(status_str)
    else:
        # Infer from directory
        parent = file_path.parent.name
        if parent == "complete":
            status = TaskStatus.COMPLETE
        elif parent == "refined":
            status = TaskStatus.READY
        else:
            status = TaskStatus.PROPOSED

    # Dependencies normalization: TASK-XXXX
    raw_deps = frontmatter.get("dependencies", [])
    dependencies = []
    if isinstance(raw_deps, list):
        for dep in raw_deps:
            clean = str(dep).upper().replace("TASK-", "").strip()
            if clean.isdigit():
                dependencies.append(f"TASK-{clean.zfill(4)}")
            else:
                dependencies.append(str(dep).upper())

    # Governing ADRs
    adrs = frontmatter.get("governing_adrs", [])
    governing_adrs = [str(a) for a in adrs] if isinstance(adrs, list) else []

    claimed_by = frontmatter.get("claimed_by")
    branch = frontmatter.get("branch")
    pr_url = frontmatter.get("pr_url")

    return Task(
        id=raw_id,
        title=title,
        status=status,
        file_path=file_path,
        dependencies=dependencies,
        governing_adrs=governing_adrs,
        claimed_by=claimed_by,
        branch=branch,
        pr_url=pr_url,
        priority_rank=priority_rank,
        raw_frontmatter=frontmatter,
        body=body,
    )


def write_task_file(task: Task) -> None:
    """Writes updated frontmatter and body back to the task file."""
    fm = dict(task.raw_frontmatter)
    fm["id"] = task.id
    fm["title"] = task.title
    if task.status == TaskStatus.READY:
        fm["status"] = "Refined"
    elif task.status == TaskStatus.COMPLETE:
        fm["status"] = "Complete"
    elif task.status == TaskStatus.PROPOSED:
        fm["status"] = "Proposed"
    else:
        fm["status"] = task.status.value

    if task.dependencies:
        fm["dependencies"] = task.dependencies
    if task.governing_adrs:
        fm["governing_adrs"] = task.governing_adrs

    if task.claimed_by:
        fm["claimed_by"] = task.claimed_by
    elif "claimed_by" in fm:
        del fm["claimed_by"]

    if task.branch and task.status == TaskStatus.IN_PROGRESS:
        fm["branch"] = task.branch
    elif "branch" in fm and task.status in (TaskStatus.READY, TaskStatus.COMPLETE):
        del fm["branch"]

    if task.pr_url and task.status in (TaskStatus.REVIEW, TaskStatus.COMPLETE):
        fm["pr_url"] = task.pr_url
    elif "pr_url" in fm and task.status == TaskStatus.READY:
        del fm["pr_url"]

    yaml_str = yaml.dump(fm, sort_keys=False).strip()
    new_content = f"---\n{yaml_str}\n---\n{task.body.lstrip()}"
    task.file_path.write_text(new_content, encoding="utf-8")


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


class BacklogQueue:
    """Manages discovery, dependency resolution, and atomic task transitions."""

    def __init__(self, backlog_dir: Path):
        self.backlog_dir = backlog_dir
        self.complete_dir = backlog_dir / "complete"
        self.refined_dir = backlog_dir / "refined"
        self.proposed_dir = backlog_dir / "proposed"

    def list_all_tasks(self) -> list[Task]:
        """Discovers all tasks across complete, refined, and proposed directories."""
        priority_map = load_priority_map(self.backlog_dir)
        tasks = []

        for folder in [self.complete_dir, self.refined_dir, self.proposed_dir]:
            if not folder.exists():
                continue
            for p in sorted(folder.glob("*.md")):
                if p.name.startswith("."):
                    continue
                # Determine canonical ID approximation for rank lookup
                stem_match = re.match(r"^(\d+)", p.stem)
                cid = f"TASK-{stem_match.group(1).zfill(4)}" if stem_match else p.stem
                rank = priority_map.get(cid, 999999)
                tasks.append(parse_task_file(p, priority_rank=rank))

        return tasks

    def get_completed_task_ids(self) -> set[str]:
        """Returns the set of canonical IDs of all completed tasks."""
        completed = set()
        if not self.complete_dir.exists():
            return completed

        for p in self.complete_dir.glob("*.md"):
            task = parse_task_file(p)
            completed.add(task.canonical_id)
        return completed

    def get_ready_unblocked_tasks(self) -> list[Task]:
        """Returns ready tasks whose dependencies are fully satisfied, sorted by priority."""
        completed_ids = self.get_completed_task_ids()
        tasks = self.list_all_tasks()

        ready = []
        for task in tasks:
            # Only consider tasks that are ready (or in refined/) and not claimed
            if task.status != TaskStatus.READY:
                continue
            if task.claimed_by:
                continue

            # Check if all dependencies are satisfied
            unblocked = all(dep in completed_ids for dep in task.dependencies)
            if unblocked:
                ready.append(task)

        ready.sort(key=lambda t: t.priority_rank)
        return ready

    def claim_task(self, task: Task, worker_id: str, branch: str) -> None:
        """Claims a task for execution in a worker worktree."""
        task.status = TaskStatus.IN_PROGRESS
        task.claimed_by = worker_id
        task.branch = branch
        write_task_file(task)

    def release_task(self, task: Task) -> None:
        """Releases a claimed task back to ready status."""
        parent = task.file_path.parent.name
        if parent == "refined":
            task.status = TaskStatus.READY
        elif parent == "complete":
            task.status = TaskStatus.COMPLETE
        else:
            task.status = TaskStatus.PROPOSED
        task.claimed_by = None
        task.branch = None
        write_task_file(task)

    def recover_stale_tasks(self) -> list[Task]:
        """Discovers tasks in refined/ that are marked in-progress or claimed, and releases them."""
        recovered = []
        if not self.refined_dir.exists():
            return recovered

        for p in sorted(self.refined_dir.glob("*.md")):
            if p.name.startswith("."):
                continue
            task = parse_task_file(p)
            if task.status == TaskStatus.IN_PROGRESS or task.claimed_by:
                self.release_task(task)
                recovered.append(task)
        return recovered

    def mark_review(self, task: Task, pr_url: str) -> None:
        """Marks a task as under review with an active PR."""
        task.status = TaskStatus.REVIEW
        task.pr_url = pr_url
        write_task_file(task)

    def complete_task(self, task: Task) -> Path:
        """Marks task complete, moves file to complete/, and updates PRIORITY.md."""
        task.status = TaskStatus.COMPLETE
        task.claimed_by = None

        dest_file = self.complete_dir / task.file_path.name
        self.complete_dir.mkdir(parents=True, exist_ok=True)

        # Move file if not already in complete
        if task.file_path != dest_file:
            task.file_path.rename(dest_file)
            task.file_path = dest_file

        write_task_file(task)
        self._sync_priority_file(task)
        return dest_file

    def _sync_priority_file(self, task: Task) -> None:
        """Updates PRIORITY.md marking the task as (Complete)."""
        priority_file = self.backlog_dir / "PRIORITY.md"
        if not priority_file.exists():
            return

        content = priority_file.read_text(encoding="utf-8")
        clean_id = task.id.replace("TASK-", "").lstrip("0")
        pattern = re.compile(
            rf"(\*\*TASK-0*{clean_id}\s*\()(?:Refined|Proposed|In-Progress)(\)\*\*:\s*\[`?[^`\]]+`?\])\((?:refined|proposed)/([^)]+)\)",
            re.IGNORECASE,
        )

        def repl(m: re.Match) -> str:
            return f"{m.group(1)}Complete{m.group(2)}(complete/{m.group(3)})"

        new_content, count = pattern.subn(repl, content)
        if count > 0:
            priority_file.write_text(new_content, encoding="utf-8")
