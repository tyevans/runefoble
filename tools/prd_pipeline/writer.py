"""File writers and formatters for decomposed tasks and user stories."""

from __future__ import annotations

import re
from pathlib import Path

from .models import TaskDraft, UserStoryDraft
from .templates import format_task_markdown, format_user_story_markdown


class PlanWriter:
    """Writes decomposed tasks, spikes, and user stories to docs/project."""

    def __init__(self, repo_root: Path | str):
        self.repo_root = Path(repo_root).resolve()
        self.backlog_dir = self.repo_root / "docs" / "project" / "backlog"
        self.stories_dir = self.repo_root / "docs" / "project" / "user_stories" / "accepted"

    def write_task(self, draft: TaskDraft) -> Path:
        """Formats and writes a TaskDraft to docs/project/backlog/proposed/."""
        slug = re.sub(r"[^a-z0-9]+", "-", draft.title.lower()).strip("-")
        filename = f"{str(draft.number).zfill(4)}-{slug}.md"
        target_dir = self.backlog_dir / "proposed"
        target_dir.mkdir(parents=True, exist_ok=True)
        file_path = target_dir / filename
        content = format_task_markdown(draft)
        file_path.write_text(content, encoding="utf-8")
        return file_path

    def write_user_story(self, draft: UserStoryDraft) -> Path:
        """Formats and writes a UserStoryDraft to docs/project/user_stories/accepted/."""
        slug = re.sub(r"[^a-z0-9]+", "-", draft.title.lower()).strip("-")
        filename = f"us-{str(draft.number).zfill(4)}-{slug}.md"
        self.stories_dir.mkdir(parents=True, exist_ok=True)
        file_path = self.stories_dir / filename
        content = format_user_story_markdown(draft)
        file_path.write_text(content, encoding="utf-8")
        return file_path
