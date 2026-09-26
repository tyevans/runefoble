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
