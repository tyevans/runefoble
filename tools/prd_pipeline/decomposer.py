"""PRD decomposition orchestrator facade."""

from __future__ import annotations

import re
from pathlib import Path

from .models import PRD, DecompositionPlan
from .planner import (
    DecompositionPlanner,
    create_api_slice_draft,
    create_domain_slice_draft,
    create_spike_draft,
    create_ui_slice_draft,
    create_worker_slice_draft,
    requires_architectural_spike,
    requires_ui_component,
    requires_worker_slice,
)
from .writer import PlanWriter


class PRDDecomposer:
    """Decomposes PRDs into granular, single-pass vertical slices and architectural spikes."""

    def __init__(self, repo_root: Path | str):
        self.repo_root = Path(repo_root).resolve()
        self.backlog_dir = self.repo_root / "docs" / "project" / "backlog"
        self.stories_dir = self.repo_root / "docs" / "project" / "user_stories" / "accepted"

    def get_max_task_number(self) -> int:
        """Finds the highest existing task number across all backlog folders."""
        max_num = 0
        for subdir in ["complete", "refined", "proposed"]:
            dir_path = self.backlog_dir / subdir
            if dir_path.exists():
                for f in dir_path.glob("*.md"):
                    m = re.search(r"(\d{4})", f.stem)
                    if m:
                        max_num = max(max_num, int(m.group(1)))
        return max_num

    def get_max_story_number(self) -> int:
        """Finds the highest existing user story number."""
        max_num = 0
        if self.stories_dir.exists():
            for f in self.stories_dir.glob("*.md"):
                m = re.search(r"(\d{4})", f.stem)
                if m:
                    max_num = max(max_num, int(m.group(1)))
        return max_num

    def plan_decomposition(self, prd: PRD) -> DecompositionPlan:
        """Analyzes a PRD and formulates a plan of spikes and vertical slices."""
        planner = DecompositionPlanner(
            current_task_num=self.get_max_task_number(),
            current_story_num=self.get_max_story_number(),
        )
        return planner.plan(prd)

    def execute_decomposition(self, plan_or_prd: DecompositionPlan | PRD) -> dict[str, list[Path]]:
        """Persists decomposed tasks and user stories to disk."""
        plan = self.plan_decomposition(plan_or_prd) if isinstance(plan_or_prd, PRD) else plan_or_prd
        writer = PlanWriter(self.repo_root)
        return {
            "tasks": [writer.write_task(t) for t in plan.all_tasks],
            "stories": [writer.write_user_story(s) for s in plan.stories],
        }

    # Backward compatibility delegates
    _requires_architectural_spike = staticmethod(requires_architectural_spike)
    _requires_ui_component = staticmethod(requires_ui_component)
    _requires_worker_slice = staticmethod(requires_worker_slice)
    _create_spike_draft = staticmethod(create_spike_draft)
    _create_domain_slice_draft = staticmethod(create_domain_slice_draft)
    _create_api_slice_draft = staticmethod(create_api_slice_draft)
    _create_ui_slice_draft = staticmethod(create_ui_slice_draft)
    _create_worker_slice_draft = staticmethod(create_worker_slice_draft)
