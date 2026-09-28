"""Task markdown frontmatter serialization and disk writing."""

import yaml

from .models import Task, TaskStatus


def write_task_file(task: Task) -> None:
    """Writes updated frontmatter and body back to the task file."""
    fm = dict(task.raw_frontmatter)
    fm["id"] = task.id
    fm["title"] = task.title

    status_map = {
        TaskStatus.READY: "Refined",
        TaskStatus.COMPLETE: "Complete",
        TaskStatus.PROPOSED: "Proposed",
    }
    fm["status"] = status_map.get(task.status, task.status.value)

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


__all__ = ["write_task_file"]
