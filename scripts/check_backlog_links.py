"""Check backlog links, body status, cited paths, and governance keys (TASK-0666).

Categories (each must be zero):
- dead_links: local markdown links in refined and proposed tasks that do not resolve.
- stale_prd_links: links from PRDs to backlog tasks that are not in the cited folder.
- body_status_mismatch: complete records whose `## Status` body differs from frontmatter.
- unresolved_paths: repository paths cited in complete records that do not exist, hold only
  `__pycache__` folders, and are not marked `(removed)`.
- missing_governance: complete records without governing_prds, governing_stories,
  governing_adrs, or dependencies.

Curation warnings (never change the exit status): the refined buffer falls outside the
6 to 12 band, and a refined task depends on a task that is not complete. The orchestrator
reads these warnings and demotes tasks by judgement. There is no hard gate for them.

Usage: uv run python scripts/check_backlog_links.py [--json]
Exit status is 1 when any category is non-zero. The check only reads repository files.
"""

from __future__ import annotations

import argparse
import json
import re
import sys

from backlog_records import (
    BACKLOG_DIR,
    GOVERNANCE_KEYS,
    PRODUCT_DIR,
    REPO_ROOT,
    active_records,
    complete_records,
    iter_markdown_links,
    repo_path_tokens,
    split_record,
    status_section_index,
    task_id_of,
)

SAMPLE_SIZE = 5
CACHE_DIR_NAME = "__pycache__"
BUFFER_MIN = 6
BUFFER_MAX = 12
TASK_ID = re.compile(r"(\d{4})")


def cited_path_exists(path: str) -> bool:
    """Return True when a cited path exists and is not only interpreter cache.

    A folder whose only content is `__pycache__` folders (at any depth) counts as missing.
    An empty folder with no cache folders still counts as present.
    """
    target = REPO_ROOT / path.rstrip("/")
    if not target.exists():
        return False
    if target.is_file():
        return True
    for entry in target.rglob("*"):
        if CACHE_DIR_NAME in entry.relative_to(target).parts:
            continue
        if entry.is_file():
            return True
    return not any(target.rglob(CACHE_DIR_NAME))


def dead_links() -> list[str]:
    found: list[str] = []
    for record in active_records():
        for target in iter_markdown_links(record.read_text(encoding="utf-8")):
            if not (record.parent / target).resolve().exists():
                found.append(f"{record.parent.name}/{record.name}: {target}")
    return found


def stale_prd_links() -> list[str]:
    found: list[str] = []
    for prd in sorted(PRODUCT_DIR.rglob("prd-*.md")):
        for target in iter_markdown_links(prd.read_text(encoding="utf-8")):
            if "backlog/" not in target:
                continue
            relative = target.split("backlog/", 1)[1]
            if not (BACKLOG_DIR / relative).exists():
                found.append(f"{prd.name}: {target}")
    return found


def body_status_mismatches() -> list[str]:
    found: list[str] = []
    for record in complete_records():
        text = record.read_text(encoding="utf-8")
        front, body = split_record(text)
        lines = body.split("\n")
        index = status_section_index(lines)
        if index is None:
            continue
        if lines[index].strip() != str(front.get("status")):
            found.append(
                f"{record.name}: body '{lines[index].strip()}' vs frontmatter '{front.get('status')}'"
            )
    return found


def unresolved_paths() -> list[str]:
    found: list[str] = []
    for record in complete_records():
        text = record.read_text(encoding="utf-8")
        for _, path, removed in repo_path_tokens(text):
            if removed or cited_path_exists(path):
                continue
            found.append(f"{record.name}: {path}")
    return found


def missing_governance() -> list[str]:
    found: list[str] = []
    for record in complete_records():
        front, _ = split_record(record.read_text(encoding="utf-8"))
        missing = [key for key in GOVERNANCE_KEYS if key not in front]
        if missing:
            found.append(f"{record.name}: {', '.join(missing)}")
    return found


def _refined_records() -> list:
    folder = BACKLOG_DIR / "refined"
    return sorted(folder.glob("*.md")) if folder.is_dir() else []


def _stage_by_task_id() -> dict[str, str]:
    stages: dict[str, str] = {}
    for stage in ("complete", "refined", "proposed"):
        folder = BACKLOG_DIR / stage
        if folder.is_dir():
            for path in folder.glob("*.md"):
                stages[task_id_of(path)] = stage
    return stages


def buffer_warnings() -> list[str]:
    count = len(_refined_records())
    if count < BUFFER_MIN:
        return [f"refined buffer holds {count} tasks; below {BUFFER_MIN}"]
    if count > BUFFER_MAX:
        return [f"refined buffer holds {count} tasks; above {BUFFER_MAX}"]
    return []


def dependency_gap_warnings() -> list[str]:
    stages = _stage_by_task_id()
    found: list[str] = []
    for record in _refined_records():
        front, _ = split_record(record.read_text(encoding="utf-8"))
        for dep in front.get("dependencies") or []:
            match = TASK_ID.search(str(dep))
            dep_id = match.group(1) if match else str(dep)
            stage = stages.get(dep_id, "missing")
            if stage != "complete":
                found.append(f"{record.name}: depends on TASK-{dep_id} ({stage})")
    return found


def curation_warnings() -> dict[str, list[str]]:
    return {
        "refined_buffer": buffer_warnings(),
        "dependency_gap": dependency_gap_warnings(),
    }


def run_checks() -> dict[str, list[str]]:
    return {
        "dead_links": dead_links(),
        "stale_prd_links": stale_prd_links(),
        "body_status_mismatch": body_status_mismatches(),
        "unresolved_paths": unresolved_paths(),
        "missing_governance": missing_governance(),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--json", action="store_true", help="print counts and findings as JSON")
    args = parser.parse_args(argv)

    results = run_checks()
    if args.json:
        payload = {name: {"count": len(items), "items": items} for name, items in results.items()}
        print(json.dumps(payload, indent=2))
    else:
        for name, items in results.items():
            print(f"{name}: {len(items)}")
            for item in items[:SAMPLE_SIZE]:
                print(f"    {item}")
        for name, items in curation_warnings().items():
            for item in items:
                print(f"warning {name}: {item}")
    return 1 if any(results.values()) else 0


if __name__ == "__main__":
    sys.exit(main())
