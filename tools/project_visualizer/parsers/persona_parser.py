"""User personas and feature inventory parser."""

from __future__ import annotations

import re
from pathlib import Path

from tools.project_visualizer.models import FeatureItem, PersonaItem
from tools.project_visualizer.parsers.markdown_utils import (
    extract_list_items,
    extract_section,
)

PERSONA_PALETTE: dict[str, str] = {
    "evelyn": "#F59E0B",
    "marcus": "#10B981",
    "sarah": "#8B5CF6",
    "devon": "#06B6D4",
    "alex": "#EC4899",
}


def parse_persona_files(project_dir: Path, root_dir: Path) -> list[PersonaItem]:
    """Parse user personas from docs/project/user_stories/PERSONAS.md."""
    personas_file = project_dir / "user_stories" / "PERSONAS.md"
    if not personas_file.exists():
        return []

    content = personas_file.read_text(encoding="utf-8")
    personas: list[PersonaItem] = []
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
                avatar_color=PERSONA_PALETTE.get(p_id, "#6366F1"),
                quote=quote,
                pain_points=extract_list_items(pain_text),
                goals=extract_list_items(goals_text),
                key_features=key_feats,
                file_path=str(personas_file.relative_to(root_dir)),
            )
        )
    return personas


def parse_feature_files(project_dir: Path) -> list[FeatureItem]:
    """Parse features from docs/project/product/FEATURE_INVENTORY.md."""
    feat_file = project_dir / "product" / "FEATURE_INVENTORY.md"
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
                features.append(
                    FeatureItem(
                        id=cols[0].strip("` "),
                        name=cols[1].strip("* "),
                        domain=curr_domain,
                        tier=cols[3].strip("* "),
                        description=cols[2],
                        governing_systems=[
                            s.strip(" `") for s in cols[4].split(",") if s.strip(" `")
                        ],
                    )
                )
    return features
