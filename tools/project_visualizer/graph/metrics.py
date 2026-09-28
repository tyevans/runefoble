"""Health metrics computation for project visualizer graph."""

from __future__ import annotations

from tools.project_visualizer.models import ProjectData, ProjectHealthMetrics


def compute_health_metrics(data: ProjectData) -> None:
    """Calculate project health metrics based on tasks, stories, and ADR coverage."""
    tasks = data.tasks
    comp = sum(1 for t in tasks if t.status == "Complete")
    ref = sum(1 for t in tasks if t.status == "Refined")
    prop = sum(1 for t in tasks if t.status == "Proposed")
    ready = "optimal" if 2 <= ref <= 5 else ("under_buffered" if ref < 2 else "over_buffered")
    orphans = [s.id for s in data.stories if not s.governing_prd and not s.implementing_tasks]
    mvp = sum(1 for f in data.features if "P0" in f.tier or "MVP" in f.tier)
    data.metrics = ProjectHealthMetrics(
        len(data.adrs),
        len(data.prds),
        len(data.stories),
        len(tasks),
        comp,
        ref,
        prop,
        len(data.features),
        mvp,
        len(data.personas),
        orphans,
        [t.id for t in tasks if not t.governing_adrs],
        ready,
        ref,
    )
