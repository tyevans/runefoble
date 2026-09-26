"""Parser for extracting structured documentation from docs/project."""

from __future__ import annotations

import glob
import hashlib
import re
from datetime import datetime
from pathlib import Path

from tools.project_visualizer.git_metadata import GitMetadataHarvester
from tools.project_visualizer.markdown_utils import (
    detect_target_bc,
    extract_list_items,
    extract_prefixed_ids,
    extract_section,
    parse_frontmatter,
)
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
        if max_mtime > 0:
            data.last_updated = datetime.fromtimestamp(max_mtime).strftime("%Y-%m-%d %H:%M:%S")
        else:
            data.last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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

        for s in re.split(r"\n##\s+\d+\.\s+", content)[1:]:
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
            quote_match = re.search(r"-\s+\*\*Role\*\*:\s*(.*)", body)
            quote = quote_match.group(1).strip() if quote_match else role

            personas.append(
                PersonaItem(
                    id=p_id,
                    name=name,
                    role=role,
                    avatar_color=palette.get(p_id, "#6366F1"),
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
            reg_info = registry_map.get(adr_id, (title, "Accepted", "2026-09-25"))

            domain_map = [
                (["auth", "zanzibar", "spicedb", "zitadel"], "Security & Auth"),
                (["stream", "event", "eventsource"], "Event Sourcing"),
                (["lit", "theme", "frontend", "microfrontend"], "Frontend & UI"),
                (["helm", "kind", "kubernetes", "ci"], "Infrastructure"),
                (["test", "hypothesis", "mutmut"], "Quality & Verification"),
            ]
            domain = next(
                (d for keys, d in domain_map if any(k in title.lower() for k in keys)),
                "Architecture",
            )

            adrs.append(
                ADRItem(
                    id=adr_id,
                    title=reg_info[0] if reg_info else title,
                    status=reg_info[1] if reg_info else "Accepted",
                    date=reg_info[2] if reg_info else "2026-09-25",
                    file_path=str(Path(file).relative_to(self.root_dir)),
                    context=extract_section(content, "Context"),
                    decision=extract_section(content, "Decision"),
                    consequences=extract_section(content, "Consequences"),
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

            linked_stories = extract_prefixed_ids(
                "US", content, meta.get("linked_stories") or meta.get("stories")
            )
            impl_tasks = extract_prefixed_ids(
                "TASK", content, meta.get("implementing_tasks") or meta.get("tasks")
            )

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
                    linked_stories=linked_stories,
                    implementing_tasks=impl_tasks,
                )
            )
        return prds

    def parse_user_stories(self, personas: list[PersonaItem]) -> list[UserStoryItem]:
        stories_dir = self.project_dir / "user_stories" / "accepted"
        stories: list[UserStoryItem] = []

        registry_file = self.project_dir / "user_stories" / "REGISTRY.md"
        persona_map: dict[str, str] = {}
        prd_map: dict[str, str] = {}
        if registry_file.exists():
            for line in registry_file.read_text(encoding="utf-8").splitlines():
                cols = [c.strip() for c in line.split("|") if c.strip()]
                if len(cols) >= 3 and cols[0].startswith("US-"):
                    persona_map[cols[0]] = cols[2]
                if len(cols) >= 4 and cols[0].startswith("US-") and cols[3].startswith("PRD-"):
                    prd_map[cols[0]] = cols[3]

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

            as_a_m = re.search(
                r"\*\*As an?\*\*\s+(.*?)(?=,\s*\n|\n\*\*I want)", body, re.IGNORECASE
            )
            want_m = re.search(
                r"\*\*I want to\*\*\s+(.*?)(?=,\s*\n|\n\*\*So that)",
                body,
                re.DOTALL | re.IGNORECASE,
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

            gov_prd = meta.get("governing_prd") or meta.get("prd") or prd_map.get(s_id, "")
            if gov_prd:
                gov_prd = f"PRD-{str(gov_prd).split('-')[-1].zfill(4)}"
            if not gov_prd:
                m_prd = re.search(r"PRD-\d+", content, re.IGNORECASE)
                if m_prd:
                    gov_prd = f"PRD-{m_prd.group(0).split('-')[-1].zfill(4)}"

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
                    governing_prd=gov_prd,
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
        git_metadata = GitMetadataHarvester(self.root_dir).harvest()

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

                summary = extract_section(body, "Summary")
                target_rel = meta.get("target_release", "")
                target_bc = detect_target_bc(content)

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
                        file_path=str(Path(file).relative_to(self.root_dir)),
                        target_bc=target_bc,
                        target_release=target_rel,
                        dependencies=list(set(deps)),
                        governing_adrs=list(set(adrs)),
                        governing_prds=list(set(prds)),
                        governing_stories=list(set(stories)),
                        microfrontends=list(set(mf_elements)),
                        commits=task_commits,
                        prs=merged_prs,
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
