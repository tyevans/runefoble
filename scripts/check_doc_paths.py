#!/usr/bin/env python3
"""Check that the Diataxis docs cite real paths, use repository-relative links,
and avoid compatibility wording that is not tied to a removal task.

Checks, for docs/reference, docs/how-to and docs/explanation:
- Every backticked repository path (for example `services/x/src/x/y.py`) exists.
- No link uses an absolute `file:///` URL.
- Every line with a compatibility phrase names a removal task (TASK-NNNN)
  or a link to the backlog.

Usage: uv run python scripts/check_doc_paths.py
Exit status is 0 when all checks pass and 1 otherwise.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
QUADRANTS = ("reference", "how-to", "explanation")

TOP_LEVEL = {
    "libs",
    "services",
    "gateway",
    "frontend",
    "deployments",
    "docs",
    "tests",
    "scripts",
    "tools",
    "e2e",
}

CODE_SPAN = re.compile(r"`([^`\n]+)`")
LINE_SUFFIX = re.compile(r"(?::\d+(?:-\d+)?|::.*)$")
PLACEHOLDER = re.compile(r"[<>{}*$()\[\] ]")
FILE_URL = re.compile(r"file:///")
COMPAT = re.compile(
    r"backward|legacy|\bshims?\b|compatibility facade|for compatibility|"
    r"compatibility alias",
    re.IGNORECASE,
)
# A compatibility phrase is allowed only when the line names a removal task,
# or marks the code as a DoR 9 defect so the reader does not take it as design.
TASK_REFERENCE = re.compile(r"TASK-\d{4}|DoR 9")


def doc_files() -> list[Path]:
    files: list[Path] = []
    for quadrant in QUADRANTS:
        files.extend(sorted((REPO_ROOT / "docs" / quadrant).rglob("*.md")))
    return files


def is_repo_path(token: str) -> bool:
    """A repository path starts with a top-level directory of the repository."""
    if "://" in token or PLACEHOLDER.search(token) or "/" not in token:
        return False
    return token.split("/", 1)[0] in TOP_LEVEL


def check_file(path: Path) -> list[str]:
    problems: list[str] = []
    rel = path.relative_to(REPO_ROOT)
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        where = f"{rel}:{number}"
        if FILE_URL.search(line):
            problems.append(f"{where}: absolute file:/// link")
        if COMPAT.search(line) and not TASK_REFERENCE.search(line):
            problems.append(f"{where}: compatibility wording without a removal task")
        for match in CODE_SPAN.finditer(line):
            token = LINE_SUFFIX.sub("", match.group(1).strip())
            if is_repo_path(token) and not (REPO_ROOT / token).exists():
                problems.append(f"{where}: missing path `{token}`")
    return problems


def main() -> int:
    problems: list[str] = []
    for path in doc_files():
        problems.extend(check_file(path))
    for problem in problems:
        print(problem)
    print(f"{len(problems)} problem(s) found")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
