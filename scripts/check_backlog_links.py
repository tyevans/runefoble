"""Check backlog links, body status, cited paths, and governance keys (TASK-0666).

Categories (each must be zero):
- dead_links: local markdown links in refined and proposed tasks that do not resolve.
- stale_prd_links: links from PRDs to backlog tasks that are not in the cited folder.
- body_status_mismatch: complete records whose `## Status` body differs from frontmatter.
- unresolved_paths: repository paths cited in complete records that do not exist and are
  not marked `(removed)`.
- missing_governance: complete records without governing_prds, governing_stories,
  governing_adrs, or dependencies.

Usage: uv run python scripts/check_backlog_links.py [--json]
Exit status is 1 when any category is non-zero. The check only reads repository files.
"""

from __future__ import annotations

import argparse
import json
import sys

from backlog_records import (
    BACKLOG_DIR,
    GOVERNANCE_KEYS,
    PRODUCT_DIR,
    active_records,
    complete_records,
    iter_markdown_links,
    path_exists,
    repo_path_tokens,
    split_record,
    status_section_index,
)

SAMPLE_SIZE = 5


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
            if removed or path_exists(path):
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
    return 1 if any(results.values()) else 0


if __name__ == "__main__":
    sys.exit(main())
