#!/usr/bin/env python3
"""Check that AGENTS.md indexes the docs, lists the source directories, and cites footnotes.

Checks:
- Every Diataxis file under docs/tutorials, docs/how-to, docs/reference and
  docs/explanation has exactly one index entry in the matching section.
- Every index entry links to a file that exists.
- Every directory under libs/, services/ and gateway/ has a Repository Layout row.
- Every footnote reference has a definition, and every definition is referenced.

Usage: uv run python scripts/check_agents_index.py
Exit status is 0 when all checks pass and 1 otherwise.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
AGENTS_PATH = REPO_ROOT / "AGENTS.md"

DIATAXIS_DIRS = ("tutorials", "how-to", "reference", "explanation")
SOURCE_PARENTS = ("libs", "services", "gateway")
TOP_LEVEL_DIRS = ("tools/", "scripts/", "tests/")

INDEX_ENTRY = re.compile(r"^- \[`[^`]+`\]\((docs/[^)]+)\):")
SECTION_HEADING = re.compile(r"^### .*\(`docs/([a-z-]+)/`\)")
LAYOUT_ROW = re.compile(r"^\| `([^`]+)` \|")
FOOTNOTE_DEFINITION = re.compile(r"^\[\^(\d+)\]:")
FOOTNOTE_REFERENCE = re.compile(r"\[\^(\d+)\]")


def index_entries(lines: list[str]) -> list[tuple[str, str]]:
    """Return (section, link) pairs for entries in the Diataxis index."""
    entries: list[tuple[str, str]] = []
    section = ""
    in_index = False
    for line in lines:
        if line.startswith("## Repository Layout"):
            break
        if line.startswith("### 1. Tutorials"):
            in_index = True
        if not in_index:
            continue
        heading = SECTION_HEADING.match(line)
        if heading:
            section = heading.group(1)
            continue
        entry = INDEX_ENTRY.match(line)
        if entry:
            entries.append((section, entry.group(1)))
    return entries


def check_index(lines: list[str]) -> list[str]:
    problems: list[str] = []
    entries = index_entries(lines)
    indexed = [link for _, link in entries]

    for section, link in entries:
        target_dir = link.split("/")[1]
        if section != target_dir:
            problems.append(f"index entry under '{section}' links to {link}")
        if not (REPO_ROOT / link).is_file():
            problems.append(f"index links to a missing file: {link}")

    for dir_name in DIATAXIS_DIRS:
        for path in sorted((REPO_ROOT / "docs" / dir_name).glob("*.md")):
            link = path.relative_to(REPO_ROOT).as_posix()
            count = indexed.count(link)
            if count == 0:
                problems.append(f"not indexed in AGENTS.md: {link}")
            elif count > 1:
                problems.append(f"indexed {count} times in AGENTS.md: {link}")
    return problems


def layout_paths(lines: list[str]) -> set[str]:
    paths: set[str] = set()
    in_layout = False
    for line in lines:
        if line.startswith("## Repository Layout"):
            in_layout = True
            continue
        if in_layout and line.startswith("## "):
            break
        if in_layout:
            row = LAYOUT_ROW.match(line)
            if row:
                paths.add(row.group(1))
    return paths


def check_layout(lines: list[str]) -> list[str]:
    problems: list[str] = []
    listed = layout_paths(lines)
    for parent in SOURCE_PARENTS:
        for directory in sorted((REPO_ROOT / parent).iterdir()):
            if not directory.is_dir():
                continue
            path = f"{parent}/{directory.name}/"
            if path not in listed:
                problems.append(f"repository layout omits {path}")
    for path in TOP_LEVEL_DIRS:
        if path not in listed:
            problems.append(f"repository layout omits {path}")
    for path in sorted(listed):
        if path.endswith("/") and not (REPO_ROOT / path).is_dir():
            problems.append(f"repository layout lists a missing directory: {path}")
    return problems


def check_footnotes(lines: list[str]) -> list[str]:
    defined: set[str] = set()
    referenced: set[str] = set()
    for line in lines:
        definition = FOOTNOTE_DEFINITION.match(line)
        if definition:
            defined.add(definition.group(1))
            continue
        referenced.update(FOOTNOTE_REFERENCE.findall(line))
    problems = [
        f"footnote [^{n}] is referenced but not defined"
        for n in sorted(referenced - defined, key=int)
    ]
    problems += [
        f"footnote [^{n}] is defined but not referenced"
        for n in sorted(defined - referenced, key=int)
    ]
    return problems


def main() -> int:
    lines = AGENTS_PATH.read_text(encoding="utf-8").splitlines()
    problems = check_index(lines) + check_layout(lines) + check_footnotes(lines)
    for problem in problems:
        print(f"FAIL: {problem}")
    if problems:
        print(f"{len(problems)} problem(s) found in AGENTS.md")
        return 1
    print("AGENTS.md index, repository layout, and footnotes are consistent")
    return 0


if __name__ == "__main__":
    sys.exit(main())
