"""Parser for extracting structured documentation from docs/project."""

from __future__ import annotations

import glob
import re
from datetime import datetime
from pathlib import Path
from typing import Any

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


def parse_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    """Extract YAML frontmatter and body from markdown content."""
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
    if not match:
        return {}, content

    fm_raw = match.group(1)
    body = match.group(2)
    meta: dict[str, Any] = {}

    for line in fm_raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            key, val = line.split(":", 1)
            key = key.strip()
            val = val.strip().strip("'\"")
            if val.startswith("[") and val.endswith("]"):
                items = [
                    x.strip().strip("'\"")
                    for x in val[1:-1].split(",")
                    if x.strip().strip("'\"")
                ]
                meta[key] = items
            else:
                meta[key] = val
    return meta, body


def extract_section(markdown: str, header: str) -> str:
    """Extract markdown content under a specific ## header."""
    pattern = rf"##\s+{re.escape(header)}.*?\n(.*?)(?=\n##|\Z)"
    match = re.search(pattern, markdown, re.DOTALL | re.IGNORECASE)
    return match.group(1).strip() if match else ""


def extract_list_items(section_text: str) -> list[str]:
    """Extract bulleted or numbered items from a markdown snippet."""
    items: list[str] = []
    for line in section_text.splitlines():
        line = line.strip()
        if re.match(r"^[-*]\s+|\d+\.\s+", line):
            cleaned = re.sub(r"^[-*]\s+|\d+\.\s+", "", line).strip()
            if cleaned:
                items.append(cleaned)
    return items


class ProjectParser:
    """Scans and extracts all project records from docs/project."""

    def __init__(self, root_dir: str | Path):
        self.root_dir = Path(root_dir).resolve()
        self.project_dir = self.root_dir / "docs" / "project"

    def parse_all(self) -> ProjectData:
        data = ProjectData()
        data.last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        data.personas = self.parse_personas()
        data.adrs = self.parse_adrs()
        data.prds = self.parse_prds()
        data.stories = self.parse_user_stories(data.personas)
        data.tasks = self.parse_backlog_tasks()
        data.milestones = self.parse_milestones()
        data.features = self.parse_features()

        return data

    def parse_personas(self) -> list[PersonaItem]:
        personas_file = self.project_dir / "user_stories" / "PERSONAS.md"
        if not personas_file.exists():
            return []

        content = personas_file.read_text(encoding="utf-8")
        personas: list[PersonaItem] = []
        palette = {
            "evelyn": "#F59E0B",
            "marcus": "#10B981",
            "sarah": "#8B5CF6",
            "devon": "#06B6D4",
            "alex": "#EC4899",
        }

        sections = re.split(r"\n##\s+\d+\.\s+", content)
        for s in sections[1:]:
            lines = s.strip().splitlines()
            if not lines:
                continue
            title_line = lines[0]
            name = title_line.split("—")[0].strip() if "—" in title_line else title_line
            role = title_line.split("—")[1].strip() if "—" in title_line else ""

            body = "\n".join(lines[1:])
            pain_text = extract_section("## Pain Points\n" + body, "Pain Points")
            goals_text = extract_section("## Goals with Runefoble\n" + body, "Goals with Runefoble")
            feat_match = re.search(r"Key Features Used\*\*:\s*(.*)", body)
            key_feats = (
                [x.strip(" `") for x in feat_match.group(1).split(",") if x.strip(" `")]
                if feat_match
                else []
            )

            p_id = name.lower().split()[0]
            avatar_color = palette.get(p_id, "#6366F1")
            quote_match = re.search(r"-\s+\*\*Role\*\*:\s*(.*)", body)
            quote = quote_match.group(1).strip() if quote_match else role

            personas.append(
                PersonaItem(
                    id=p_id,
                    name=name,
                    role=role,
                    avatar_color=avatar_color,
                    quote=quote,
                    pain_points=extract_list_items(pain_text),
                    goals=extract_list_items(goals_text),
                    key_features=key_feats,
                    file_path=str(personas_file.relative_to(self.root_dir)),
                )
            )
        return personas

    def parse_adrs(self) -> list[ADRItem]:
        adrs_dir = self.project_dir / "adrs" / "accepted"
        registry_file = self.project_dir / "adrs" / "REGISTRY.md"
        registry_map: dict[str, tuple[str, str, str]] = {}

        if registry_file.exists():
            for line in registry_file.read_text(encoding="utf-8").splitlines():
                cols = [c.strip() for c in line.split("|") if c.strip()]
                if len(cols) >= 4 and cols[0].startswith("ADR-"):
                    registry_map[cols[0]] = (cols[1], cols[2], cols[3])

        adrs: list[ADRItem] = []
        for file in sorted(glob.glob(str(adrs_dir / "*.md"))):
            content = Path(file).read_text(encoding="utf-8")
            h1 = re.search(r"^#\s+(ADR-\d+):\s*(.*)", content, re.MULTILINE)
            adr_id = h1.group(1) if h1 else Path(file).stem.split("-")[0].upper()
            title = h1.group(2) if h1 else Path(file).stem

            context = extract_section(content, "Context")
            decision = extract_section(content, "Decision")
            consequences = extract_section(content, "Consequences")

            reg_info = registry_map.get(adr_id, (title, "Accepted", "2026-09-25"))

            domain = "Architecture"
            if any(k in title.lower() for k in ["auth", "zanzibar", "spicedb", "zitadel"]):
                domain = "Security & Auth"
            elif any(k in title.lower() for k in ["stream", "event", "eventsource"]):
                domain = "Event Sourcing"
            elif any(k in title.lower() for k in ["lit", "theme", "frontend", "microfrontend"]):
                domain = "Frontend & UI"
            elif any(k in title.lower() for k in ["helm", "kind", "kubernetes", "ci"]):
                domain = "Infrastructure"
            elif any(k in title.lower() for k in ["test", "hypothesis", "mutmut"]):
                domain = "Quality & Verification"

            adrs.append(
                ADRItem(
                    id=adr_id,
                    title=reg_info[0] if reg_info else title,
                    status=reg_info[1] if reg_info else "Accepted",
                    date=reg_info[2] if reg_info else "2026-09-25",
                    file_path=str(Path(file).relative_to(self.root_dir)),
                    context=context,
                    decision=decision,
                    consequences=consequences,
                    domain=domain,
                    raw_markdown=content,
                )
            )
        return adrs

    def parse_prds(self) -> list[PRDItem]:
        prd_dir = self.project_dir / "product" / "accepted"
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
            status = meta.get("status", "Accepted")
            created = meta.get("created", "2026-09-25")

            who_for = extract_section(body, "Who this is for")
            problem = extract_section(body, "What the person cannot do today")
            outcomes_text = extract_section(body, "Checkable Outcomes")

            personas = []
            for p in ["Evelyn", "Marcus", "Sarah", "Devon", "Alex"]:
                if p.lower() in who_for.lower() or p.lower() in problem.lower():
                    personas.append(p)
            if not personas:
                personas = ["All Personas"]

            prds.append(
                PRDItem(
                    id=p_id,
                    title=title,
                    status=status,
                    created=created,
                    file_path=str(Path(file).relative_to(self.root_dir)),
                    target_personas=personas,
                    problem_statement=problem or who_for,
                    outcomes=extract_list_items(outcomes_text),
                    raw_markdown=content,
                )
            )
        return prds

    def parse_user_stories(self, personas: list[PersonaItem]) -> list[UserStoryItem]:
        stories_dir = self.project_dir / "user_stories" / "accepted"
        stories: list[UserStoryItem] = []

        registry_file = self.project_dir / "user_stories" / "REGISTRY.md"
        persona_map: dict[str, str] = {}
        if registry_file.exists():
            for line in registry_file.read_text(encoding="utf-8").splitlines():
                cols = [c.strip() for c in line.split("|") if c.strip()]
                if len(cols) >= 3 and cols[0].startswith("US-"):
                    persona_map[cols[0]] = cols[2]

        for file in sorted(glob.glob(str(stories_dir / "*.md"))):
            content = Path(file).read_text(encoding="utf-8")
            meta, body = parse_frontmatter(content)
            h1 = re.search(r"^#\s+(US-\d+)\s*[—:-]\s*(.*)", body, re.MULTILINE)

            s_id = (
                f"US-{str(meta.get('id', '')).zfill(4)}"
                if meta.get("id")
                else (h1.group(1) if h1 else Path(file).stem.upper())
            )
            title = meta.get("title") or (h1.group(2) if h1 else Path(file).stem)
            status = meta.get("status", "Accepted")

            as_a_m = re.search(r"\*\*As an?\*\*\s+(.*?)(?=,\s*\n|\n\*\*I want)", body, re.IGNORECASE)
            want_m = re.search(
                r"\*\*I want to\*\*\s+(.*?)(?=,\s*\n|\n\*\*So that)", body, re.DOTALL | re.IGNORECASE
            )
            so_m = re.search(r"\*\*So that\*\*\s+(.*?)(?=\n##|\Z)", body, re.DOTALL | re.IGNORECASE)

            as_a = as_a_m.group(1).strip() if as_a_m else ""
            i_want = want_m.group(1).strip() if want_m else ""
            so_that = so_m.group(1).strip() if so_m else ""

            criteria_text = extract_section(body, "Acceptance Criteria")

            # Determine persona name
            reg_persona = persona_map.get(s_id, "")
            persona_name = reg_persona
            if not persona_name:
                for p in ["Evelyn", "Marcus", "Sarah", "Devon", "Alex"]:
                    if p.lower() in as_a.lower():
                        persona_name = p
                        break
            if not persona_name:
                persona_name = "Player"

            stories.append(
                UserStoryItem(
                    id=s_id,
                    title=title,
                    persona=persona_name,
                    status=status,
                    file_path=str(Path(file).relative_to(self.root_dir)),
                    as_a=as_a,
                    i_want=i_want,
                    so_that=so_that,
                    acceptance_criteria=extract_list_items(criteria_text),
                    raw_markdown=content,
                )
            )
        return stories

    def parse_backlog_tasks(self) -> list[BacklogTaskItem]:
        task_dirs = [
            ("Complete", self.project_dir / "backlog" / "complete"),
            ("Refined", self.project_dir / "backlog" / "refined"),
            ("Proposed", self.project_dir / "backlog" / "proposed"),
        ]
        tasks: list[BacklogTaskItem] = []

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
                adrs = meta.get("governing_adrs", [])
                if isinstance(adrs, str):
                    adrs = [adrs]
                if not adrs:
                    adrs = re.findall(r"ADR-\d+", content)

                summary = extract_section(body, "Summary")
                target_rel = meta.get("target_release", "")

                # Detect target bounded context
                target_bc = "platform"
                for bc in [
                    "the_watcher",
                    "board_state",
                    "game_session",
                    "character_sheet",
                    "voice_agent",
                    "gateway_api",
                    "gateway_mcp",
                    "campaign_lore",
                    "rules_compendium",
                    "battlemap_forge",
                    "soundscape",
                    "audience_studio",
                    "campaign_analytics",
                ]:
                    if bc in content:
                        target_bc = bc
                        break

                # Detect microfrontends
                mf_elements = re.findall(r"<runefoble-[a-z0-9-]+>", content)

                tasks.append(
                    BacklogTaskItem(
                        id=t_id,
                        title=title,
                        status=meta.get("status", status_label),
                        created=meta.get("created", ""),
                        completed=meta.get("completed", ""),
                        file_path=str(Path(file).relative_to(self.root_dir)),
                        target_bc=target_bc,
                        target_release=target_rel,
                        dependencies=list(set(deps)),
                        governing_adrs=list(set(adrs)),
                        microfrontends=list(set(mf_elements)),
                        summary=summary,
                        raw_markdown=content,
                    )
                )
        return tasks

    def parse_milestones(self) -> list[MilestoneItem]:
        roadmap_file = self.project_dir / "backlog" / "ROADMAP.md"
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
            status = "Complete" if "Complete" in header else ("Current" if "Current" in header else "Planned")

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

    def parse_features(self) -> list[FeatureItem]:
        feat_file = self.project_dir / "product" / "FEATURE_INVENTORY.md"
        if not feat_file.exists():
            return []
        content = feat_file.read_text(encoding="utf-8")
        features: list[FeatureItem] = []

        curr_domain = "General"
        for line in content.splitlines():
            line = line.strip()
            if line.startswith("## ") and "Domain" in line:
                curr_domain = re.sub(r"^##\s+\d+\.\s+", "", line).replace(" Domain", "")
            elif line.startswith("| `FEAT-"):
                cols = [c.strip() for c in line.split("|") if c.strip()]
                if len(cols) >= 5:
                    f_id = cols[0].strip("` ")
                    name = cols[1].strip("* ")
                    desc = cols[2]
                    tier = cols[3].strip("* ")
                    systems = [s.strip("` ") for s in cols[4].split(",") if s.strip("` ")]
                    features.append(
                        FeatureItem(
                            id=f_id,
                            name=name,
                            domain=curr_domain,
                            tier=tier,
                            description=desc,
                            governing_systems=systems,
                        )
                    )
        return features
