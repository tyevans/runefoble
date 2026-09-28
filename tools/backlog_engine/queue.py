"""Backlog queue parsing, dependency resolution, and state transitions."""

import contextlib
import re
from pathlib import Path

from .git_ops import finalize_backlog_completion
from .models import Task, TaskStatus
from .parser import FRONTMATTER_PATTERN, load_priority_map, parse_task_file
from .serializer import write_task_file


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
        tasks: list[Task] = []
        seen: set[str] = set()
        for folder in (self.complete_dir, self.refined_dir, self.proposed_dir):
            if not folder.exists():
                continue
            for p in sorted(folder.glob("*.md")):
                if p.name.startswith(".") or not p.is_file():
                    continue
                try:
                    m = re.match(r"^(\d+)", p.stem)
                    cid = f"TASK-{m.group(1).zfill(4)}" if m else p.stem
                    if cid in seen:
                        continue
                    task = parse_task_file(p, priority_rank=priority_map.get(cid, 999999))
                    tasks.append(task)
                    seen.add(task.canonical_id)
                except (FileNotFoundError, OSError):
                    continue
        return tasks

    def get_completed_task_ids(self) -> set[str]:
        """Returns the set of canonical IDs of all completed tasks."""
        if not self.complete_dir.exists():
            return set()
        completed = set()
        for p in self.complete_dir.glob("*.md"):
            if not p.name.startswith(".") and p.is_file():
                with contextlib.suppress(FileNotFoundError, OSError):
                    completed.add(parse_task_file(p).canonical_id)
        return completed

    def get_ready_unblocked_tasks(self) -> list[Task]:
        """Returns ready tasks whose dependencies are fully satisfied, sorted by priority."""
        completed = self.get_completed_task_ids()
        ready = [
            t
            for t in self.list_all_tasks()
            if t.status == TaskStatus.READY
            and not t.claimed_by
            and all(dep in completed for dep in t.dependencies)
        ]
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
        task.status = (
            TaskStatus.READY
            if parent == "refined"
            else (TaskStatus.COMPLETE if parent == "complete" else TaskStatus.PROPOSED)
        )
        task.claimed_by = task.branch = task.pr_url = None
        if task.file_path.exists():
            write_task_file(task)
            return
        for folder in (self.refined_dir, self.proposed_dir, self.complete_dir):
            candidate = folder / task.file_path.name
            if candidate.is_file():
                task.file_path = candidate
                write_task_file(task)
                break

    def recover_stale_tasks(self) -> list[Task]:
        """Discovers tasks in refined/ marked in-progress/review/claimed and releases them."""
        recovered = []
        if not self.refined_dir.exists():
            return recovered
        for p in sorted(self.refined_dir.glob("*.md")):
            if p.name.startswith(".") or not p.is_file():
                continue
            with contextlib.suppress(FileNotFoundError, OSError):
                task = parse_task_file(p)
                if task.status in (TaskStatus.IN_PROGRESS, TaskStatus.REVIEW) or task.claimed_by:
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
        if task.file_path != dest_file:
            if task.file_path.exists():
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
        new_content, count = pattern.subn(
            lambda m: f"{m.group(1)}Complete{m.group(2)}(complete/{m.group(3)})",
            content,
        )
        if count > 0:
            priority_file.write_text(new_content, encoding="utf-8")


__all__ = [
    "FRONTMATTER_PATTERN",
    "BacklogQueue",
    "finalize_backlog_completion",
    "load_priority_map",
    "parse_task_file",
    "write_task_file",
]
