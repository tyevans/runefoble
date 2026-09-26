"""Backlog task and roadmap milestone parser."""

from __future__ import annotations

import glob
import re
from pathlib import Path

from tools.project_visualizer.git_metadata import GitMetadataHarvester
from tools.project_visualizer.models import BacklogTaskItem, MilestoneItem
from tools.project_visualizer.parsers.markdown_utils import (
    detect_target_bc,
    extract_prefixed_ids,
    extract_section,
    parse_frontmatter,
)


def parse_backlog_files(project_dir: Path, root_dir: Path) -> list[BacklogTaskItem]:
    """Scan and parse tasks across complete, refined, and proposed backlog directories."""
    task_dirs = [
        ("Complete", project_dir / "backlog" / "complete"),
        ("Refined", project_dir / "backlog" / "refined"),
        ("Proposed", project_dir / "backlog" / "proposed"),
    ]
    tasks: list[BacklogTaskItem] = []
    git_metadata = GitMetadataHarvester(root_dir).harvest()

    for status_label, b_dir in task_dirs:
        if not b_dir.exists():
            continue
        for file in sorted(glob.glob(str(b_dir / "*.md"))):
            content = Path(file).read_text(encoding="utf-8")
            meta, body = parse_frontmatter(content)
            h1 = re.search(r"^#\s+(TASK-\d+):\s*(.*)", body, re.MULTILINE)

            stem_id = Path(file).stem.split("-")[0]
            t_num = str(meta.get("id", stem_id)).zfill(4)
            t_id = f"TASK-{t_num}"
            title = meta.get("title") or (h1.group(2) if h1 else Path(file).stem)

            deps = meta.get("dependencies", [])
            if isinstance(deps, str):
                deps = [deps]
            adrs = extract_prefixed_ids("ADR", content, meta.get("governing_adrs"))
            prds = extract_prefixed_ids(
                "PRD", content, meta.get("governing_prds") or meta.get("prds")
            )
            stories = extract_prefixed_ids(
                "US", content, meta.get("governing_stories") or meta.get("stories")
            )

            # Detect microfrontends
            mf_elements = re.findall(r"<runefoble-[a-z0-9-]+>", content)

            # Collect Git commits and PRs
            task_commits, task_prs = git_metadata.get(t_id, ([], []))
            merged_prs = list(task_prs)

            fm_prs = meta.get("prs", [])
            if isinstance(fm_prs, str):
                fm_prs = [fm_prs]
            for p in fm_prs:
                p_clean = f"#{str(p).lstrip('#')}"
                if p_clean not in merged_prs:
                    merged_prs.append(p_clean)

            pr_section = extract_section(body, "Pull Requests")
            if pr_section:
                for p in re.findall(r"#(\d+)", pr_section):
                    p_clean = f"#{p}"
                    if p_clean not in merged_prs:
                        merged_prs.append(p_clean)

            tasks.append(
                BacklogTaskItem(
                    id=t_id,
                    title=title,
                    status=meta.get("status", status_label),
                    created=meta.get("created", ""),
                    completed=meta.get("completed", ""),
                    file_path=str(Path(file).relative_to(root_dir)),
                    target_bc=detect_target_bc(content),
                    target_release=meta.get("target_release", ""),
                    dependencies=list(set(deps)),
                    governing_adrs=list(set(adrs)),
                    governing_prds=list(set(prds)),
                    governing_stories=list(set(stories)),
                    microfrontends=list(set(mf_elements)),
                    commits=task_commits,
                    prs=merged_prs,
                    summary=extract_section(body, "Summary"),
                    raw_markdown=content,
                )
            )
    return tasks


def parse_roadmap_file(project_dir: Path) -> list[MilestoneItem]:
    """Scan and parse roadmap milestones from docs/project/backlog/ROADMAP.md."""
    roadmap_file = project_dir / "backlog" / "ROADMAP.md"
    if not roadmap_file.exists():
        return []
    content = roadmap_file.read_text(encoding="utf-8")
    milestones: list[MilestoneItem] = []

    m_sections = re.split(r"\n##\s+Milestone\s+", content)
    for s in m_sections[1:]:
        lines = s.strip().splitlines()
        if not lines:
            continue
        header = lines[0]
        m_id = "M" + header.split(":")[0].strip()
        name = header.split(":", 1)[1].strip() if ":" in header else header
        status = (
            "Complete"
            if "Complete" in header
            else ("Current" if "Current" in header else "Planned")
        )

        body = "\n".join(lines[1:])
        tasks_found = re.findall(r"TASK-\d+", body)
        checks = re.findall(r"-\s*\[([ xX])\]", body)
        done_count = sum(1 for c in checks if c.lower() == "x")
        total_checks = len(checks) if checks else 1
        pct = int((done_count / total_checks) * 100) if total_checks else 0

        milestones.append(
            MilestoneItem(
                id=m_id,
                name=name,
                status=status,
                task_ids=list(set(tasks_found)),
                completion_pct=100 if "Complete" in status else pct,
            )
        )
    return milestones


class BacklogParser:
    """Parser helper class for engineering backlog items and roadmap milestones."""

    def __init__(self, project_dir: Path, root_dir: Path):
        self.project_dir = project_dir
        self.root_dir = root_dir

    def parse_tasks(self) -> list[BacklogTaskItem]:
        return parse_backlog_files(self.project_dir, self.root_dir)

    def parse_milestones(self) -> list[MilestoneItem]:
        return parse_roadmap_file(self.project_dir)


__all__ = [
    "BacklogParser",
    "parse_backlog_files",
    "parse_roadmap_file",
]
