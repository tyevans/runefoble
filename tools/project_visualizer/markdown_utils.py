"""Markdown extraction and frontmatter parsing utilities for project visualizer."""

from __future__ import annotations

import re
from typing import Any


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
                    x.strip().strip("'\"") for x in val[1:-1].split(",") if x.strip().strip("'\"")
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


KNOWN_BOUNDED_CONTEXTS = [
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
]


def detect_target_bc(content: str) -> str:
    """Detect target bounded context from content strings."""
    for bc in KNOWN_BOUNDED_CONTEXTS:
        if bc in content:
            return bc
    return "platform"


def extract_prefixed_ids(
    prefix: str, content: str, declared_items: list[Any] | None = None
) -> list[str]:
    """Extract and normalize IDs matching a prefix (e.g. 'PRD', 'US', 'TASK', 'ADR')."""
    ids: list[str] = []
    if declared_items:
        if isinstance(declared_items, str):
            declared_items = [declared_items]
        for item in declared_items:
            norm = f"{prefix.upper()}-{str(item).split('-')[-1].zfill(4)}"
            if norm not in ids:
                ids.append(norm)

    for m in re.findall(rf"{re.escape(prefix)}-\d+", content, re.IGNORECASE):
        norm = f"{prefix.upper()}-{m.split('-')[-1].zfill(4)}"
        if norm not in ids:
            ids.append(norm)
    return ids
