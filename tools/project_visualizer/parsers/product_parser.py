"""Product artifacts parser (PRDs and user stories)."""

from __future__ import annotations

import glob
import re
from pathlib import Path

from tools.project_visualizer.models import FeatureItem, PersonaItem, PRDItem, UserStoryItem
from tools.project_visualizer.parsers.markdown_utils import (
    extract_list_items,
    extract_prefixed_ids,
    extract_section,
    parse_frontmatter,
)
from tools.project_visualizer.parsers.persona_parser import (
    parse_feature_files,
    parse_persona_files,
)


def parse_prd_files(project_dir: Path, root_dir: Path) -> list[PRDItem]:
    """Scan and parse accepted PRDs from docs/project/product/accepted/."""
    prd_dir = project_dir / "product" / "accepted"
    prds: list[PRDItem] = []

    for file in sorted(glob.glob(str(prd_dir / "*.md"))):
        content = Path(file).read_text(encoding="utf-8")
        meta, body = parse_frontmatter(content)
        h1 = re.search(r"^#\s+(PRD-\d+)\s*[—:-]\s*(.*)", body, re.MULTILINE)

        p_id = (
            f"PRD-{str(meta.get('id', '')).zfill(4)}"
            if meta.get("id")
            else (h1.group(1) if h1 else Path(file).stem.upper())
        )
        title = meta.get("title") or (h1.group(2) if h1 else Path(file).stem)
        who_for = extract_section(body, "Who this is for")
        problem = extract_section(body, "What the person cannot do today")
        personas = [
            p
            for p in ["Evelyn", "Marcus", "Sarah", "Devon", "Alex"]
            if p.lower() in f"{who_for} {problem}".lower()
        ] or ["All Personas"]

        prds.append(
            PRDItem(
                id=p_id,
                title=title,
                status=meta.get("status", "Accepted"),
                created=meta.get("created", "2026-09-25"),
                file_path=str(Path(file).relative_to(root_dir)),
                target_personas=personas,
                problem_statement=problem or who_for,
                outcomes=extract_list_items(extract_section(body, "Checkable Outcomes")),
                raw_markdown=content,
                linked_stories=extract_prefixed_ids(
                    "US", content, meta.get("linked_stories") or meta.get("stories")
                ),
                implementing_tasks=extract_prefixed_ids(
                    "TASK", content, meta.get("implementing_tasks") or meta.get("tasks")
                ),
            )
        )
    return prds


def parse_user_story_files(
    project_dir: Path, root_dir: Path, personas: list[PersonaItem] | None = None
) -> list[UserStoryItem]:
    """Scan and parse accepted user stories from docs/project/user_stories/accepted/."""
    stories_dir = project_dir / "user_stories" / "accepted"
    registry_file = project_dir / "user_stories" / "REGISTRY.md"
    persona_map: dict[str, str] = {}
    prd_map: dict[str, str] = {}
    if registry_file.exists():
        for line in registry_file.read_text(encoding="utf-8").splitlines():
            cols = [c.strip() for c in line.split("|") if c.strip()]
            if len(cols) >= 3 and cols[0].startswith("US-"):
                persona_map[cols[0]] = cols[2]
            if len(cols) >= 4 and cols[0].startswith("US-") and cols[3].startswith("PRD-"):
                prd_map[cols[0]] = cols[3]

    stories: list[UserStoryItem] = []
    for file in sorted(glob.glob(str(stories_dir / "*.md"))):
        content = Path(file).read_text(encoding="utf-8")
        meta, body = parse_frontmatter(content)
        h1 = re.search(r"^#\s+(US-\d+)\s*[—:-]\s*(.*)", body, re.MULTILINE)
        s_id = (
            f"US-{str(meta.get('id', '')).zfill(4)}"
            if meta.get("id")
            else (h1.group(1) if h1 else Path(file).stem.upper())
        )
        as_a_m = re.search(r"\*\*As an?\*\*\s+(.*?)(?=,\s*\n|\n\*\*I want)", body, re.IGNORECASE)
        want_m = re.search(
            r"\*\*I want to\*\*\s+(.*?)(?=,\s*\n|\n\*\*So that)", body, re.DOTALL | re.IGNORECASE
        )
        so_m = re.search(r"\*\*So that\*\*\s+(.*?)(?=\n##|\Z)", body, re.DOTALL | re.IGNORECASE)
        as_a = as_a_m.group(1).strip() if as_a_m else ""

        persona_name = persona_map.get(s_id, "")
        if not persona_name:
            persona_name = next(
                (
                    p
                    for p in ["Evelyn", "Marcus", "Sarah", "Devon", "Alex"]
                    if p.lower() in as_a.lower()
                ),
                "Player",
            )

        gov_prd = meta.get("governing_prd") or meta.get("prd") or prd_map.get(s_id, "")
        if gov_prd:
            gov_prd = f"PRD-{str(gov_prd).split('-')[-1].zfill(4)}"
        elif m_prd := re.search(r"PRD-\d+", content, re.IGNORECASE):
            gov_prd = f"PRD-{m_prd.group(0).split('-')[-1].zfill(4)}"

        stories.append(
            UserStoryItem(
                id=s_id,
                title=meta.get("title") or (h1.group(2) if h1 else Path(file).stem),
                persona=persona_name,
                status=meta.get("status", "Accepted"),
                file_path=str(Path(file).relative_to(root_dir)),
                as_a=as_a,
                i_want=want_m.group(1).strip() if want_m else "",
                so_that=so_m.group(1).strip() if so_m else "",
                acceptance_criteria=extract_list_items(
                    extract_section(body, "Acceptance Criteria")
                ),
                raw_markdown=content,
                governing_prd=gov_prd,
            )
        )
    return stories


class ProductParser:
    """Parser helper class for product-domain documentation."""

    def __init__(self, project_dir: Path, root_dir: Path):
        self.project_dir = project_dir
        self.root_dir = root_dir

    def parse_prds(self) -> list[PRDItem]:
        return parse_prd_files(self.project_dir, self.root_dir)

    def parse_user_stories(self, personas: list[PersonaItem] | None = None) -> list[UserStoryItem]:
        return parse_user_story_files(self.project_dir, self.root_dir, personas)

    def parse_personas(self) -> list[PersonaItem]:
        return parse_persona_files(self.project_dir, self.root_dir)

    def parse_features(self) -> list[FeatureItem]:
        return parse_feature_files(self.project_dir)


__all__ = [
    "ProductParser",
    "parse_feature_files",
    "parse_persona_files",
    "parse_prd_files",
    "parse_user_story_files",
]
