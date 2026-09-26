"""Parser facade and entrypoint for extracting structured documentation from docs/project."""

from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path

from tools.project_visualizer.models import (
    ADRItem,
    BacklogTaskItem,
    FeatureItem,
    MilestoneItem,
    PersonaItem,
    PRDItem,
    ProjectData,
    UserStoryItem,
)
from tools.project_visualizer.parsers import (
    KNOWN_BOUNDED_CONTEXTS,
    ADRParser,
    BacklogParser,
    GraphBuilder,
    ProductParser,
    build_traceability_graph,
    detect_target_bc,
    extract_list_items,
    extract_prefixed_ids,
    extract_section,
    parse_adr_files,
    parse_backlog_files,
    parse_feature_files,
    parse_frontmatter,
    parse_persona_files,
    parse_prd_files,
    parse_roadmap_file,
    parse_user_story_files,
)


class ProjectParser:
    """Scans and extracts all project records from docs/project."""

    def __init__(self, root_dir: str | Path):
        self.root_dir = Path(root_dir).resolve()
        self.project_dir = self.root_dir / "docs" / "project"
        self._cached_fingerprint: str | None = None
        self._cached_data: ProjectData | None = None

    def compute_fingerprint(self) -> tuple[str, float]:
        """Compute content hash and max mtime across docs/project."""
        hasher = hashlib.sha256()
        max_mtime = 0.0
        if self.project_dir.exists():
            for p in sorted(self.project_dir.rglob("*.md")):
                try:
                    stat = p.stat()
                    hasher.update(str(p.relative_to(self.root_dir)).encode("utf-8"))
                    hasher.update(str(stat.st_mtime_ns).encode("utf-8"))
                    hasher.update(str(stat.st_size).encode("utf-8"))
                    if stat.st_mtime > max_mtime:
                        max_mtime = stat.st_mtime
                except OSError:
                    continue
        return hasher.hexdigest()[:16], max_mtime

    def parse_all(self, force: bool = False) -> ProjectData:
        fingerprint, max_mtime = self.compute_fingerprint()
        if not force and self._cached_fingerprint == fingerprint and self._cached_data is not None:
            return self._cached_data

        data = ProjectData()
        data.data_hash = fingerprint
        data.last_updated = (
            datetime.fromtimestamp(max_mtime).strftime("%Y-%m-%d %H:%M:%S")
            if max_mtime > 0
            else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        data.personas = self.parse_personas()
        data.adrs = self.parse_adrs()
        data.prds = self.parse_prds()
        data.stories = self.parse_user_stories(data.personas)
        data.tasks = self.parse_backlog_tasks()
        data.milestones = self.parse_milestones()
        data.features = self.parse_features()

        self._cached_fingerprint = fingerprint
        self._cached_data = data
        return data

    def parse_personas(self) -> list[PersonaItem]:
        return parse_persona_files(self.project_dir, self.root_dir)

    def parse_adrs(self) -> list[ADRItem]:
        return parse_adr_files(self.project_dir, self.root_dir)

    def parse_prds(self) -> list[PRDItem]:
        return parse_prd_files(self.project_dir, self.root_dir)

    def parse_user_stories(self, personas: list[PersonaItem] | None = None) -> list[UserStoryItem]:
        return parse_user_story_files(self.project_dir, self.root_dir, personas)

    def parse_backlog_tasks(self) -> list[BacklogTaskItem]:
        return parse_backlog_files(self.project_dir, self.root_dir)

    def parse_milestones(self) -> list[MilestoneItem]:
        return parse_roadmap_file(self.project_dir)

    def parse_features(self) -> list[FeatureItem]:
        return parse_feature_files(self.project_dir)


def scan_project(root_dir: str | Path = ".", force: bool = False) -> ProjectData:
    """Facade entrypoint to scan project documentation records."""
    return ProjectParser(root_dir).parse_all(force=force)


__all__ = [
    "ADRParser",
    "BacklogParser",
    "GraphBuilder",
    "KNOWN_BOUNDED_CONTEXTS",
    "ProductParser",
    "ProjectParser",
    "build_traceability_graph",
    "detect_target_bc",
    "extract_list_items",
    "extract_prefixed_ids",
    "extract_section",
    "parse_adr_files",
    "parse_backlog_files",
    "parse_feature_files",
    "parse_frontmatter",
    "parse_persona_files",
    "parse_prd_files",
    "parse_roadmap_file",
    "parse_user_story_files",
    "scan_project",
]
