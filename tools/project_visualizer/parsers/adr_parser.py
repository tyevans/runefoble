"""Architecture Decision Record (ADR) file parser."""

from __future__ import annotations

import glob
import re
from pathlib import Path

from tools.project_visualizer.models import ADRItem
from tools.project_visualizer.parsers.markdown_utils import extract_section

DOMAIN_MAP: list[tuple[list[str], str]] = [
    (["auth", "zanzibar", "spicedb", "zitadel"], "Security & Auth"),
    (["stream", "event", "eventsource"], "Event Sourcing"),
    (["lit", "theme", "frontend", "microfrontend"], "Frontend & UI"),
    (["helm", "kind", "kubernetes", "ci"], "Infrastructure"),
    (["test", "hypothesis", "mutmut"], "Quality & Verification"),
]


def classify_adr_domain(title: str) -> str:
    """Classify architectural domain based on keywords in title."""
    title_lower = title.lower()
    return next(
        (domain for keys, domain in DOMAIN_MAP if any(k in title_lower for k in keys)),
        "Architecture",
    )


def parse_adr_files(project_dir: Path, root_dir: Path) -> list[ADRItem]:
    """Scan and parse accepted Architecture Decision Records from docs/project/adrs/."""
    adrs_dir = project_dir / "adrs" / "accepted"
    registry_file = project_dir / "adrs" / "REGISTRY.md"
    registry_map: dict[str, tuple[str, str, str]] = {}

    if registry_file.exists():
        for line in registry_file.read_text(encoding="utf-8").splitlines():
            cols = [c.strip() for c in line.split("|") if c.strip()]
            if len(cols) >= 4 and cols[0].startswith("ADR-"):
                registry_map[cols[0]] = (cols[1], cols[2], cols[3])

    adrs: list[ADRItem] = []
    for file in sorted(glob.glob(str(adrs_dir / "*.md"))):
        content = Path(file).read_text(encoding="utf-8")
        h1 = re.search(r"^#\s+ADR[- ]?(\d+):\s*(.*)", content, re.MULTILINE | re.IGNORECASE)
        if h1:
            adr_id = f"ADR-{int(h1.group(1)):04d}"
            title = h1.group(2).strip()
        else:
            stem_m = re.match(r"^adr[-_]?(\d+)", Path(file).stem, re.IGNORECASE)
            adr_id = (
                f"ADR-{int(stem_m.group(1)):04d}"
                if stem_m
                else Path(file).stem.split("-")[0].upper()
            )
            title = Path(file).stem
        reg_info = registry_map.get(adr_id)
        final_title = reg_info[0] if (reg_info and reg_info[0]) else title
        final_status = (
            reg_info[1]
            if (reg_info and reg_info[1])
            else (extract_section(content, "Status") or "Accepted")
        )
        final_date = (
            reg_info[2]
            if (reg_info and reg_info[2])
            else (extract_section(content, "Date") or "2026-09-25")
        )

        adrs.append(
            ADRItem(
                id=adr_id,
                title=final_title,
                status=final_status,
                date=final_date,
                file_path=str(Path(file).relative_to(root_dir)),
                context=extract_section(content, "Context"),
                decision=extract_section(content, "Decision"),
                consequences=extract_section(content, "Consequences"),
                domain=classify_adr_domain(final_title),
                raw_markdown=content,
            )
        )
    return adrs


class ADRParser:
    """Parser helper class for Architecture Decision Records."""

    def __init__(self, project_dir: Path, root_dir: Path):
        self.project_dir = project_dir
        self.root_dir = root_dir

    def parse(self) -> list[ADRItem]:
        return parse_adr_files(self.project_dir, self.root_dir)
