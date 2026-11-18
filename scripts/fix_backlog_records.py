"""Repair backlog record links, references, body status, governance keys, and paths (TASK-0666).

Every step is idempotent. Re-run the script after a merge to repair records that drifted
again. Steps:
  links       retarget or unlink dead local links in refined and proposed tasks (LINK_MAP)
  references  correct frontmatter references (REFERENCE_MAP)
  status      set the complete-record `## Status` body to the frontmatter status
  governance  add missing governing keys; values come only from IDs named in the body
  paths       retarget cited repository paths in complete records to a unique moved file,
              or mark them `(removed)` when no unique file exists

Usage: uv run python scripts/fix_backlog_records.py [--step NAME ...]
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

from backlog_link_map import LINK_MAP, PATH_OVERRIDES, REFERENCE_MAP
from backlog_records import (
    ADR_DIR,
    PRODUCT_DIR,
    REMOVED_MARKS,
    STORIES_DIR,
    active_records,
    complete_records,
    frontmatter_bounds,
    iter_markdown_links,
    path_exists,
    registry_ids,
    repo_path_tokens,
    split_record,
    status_section_index,
    task_id_of,
    tracked_files,
)

STEPS = ("links", "references", "status", "governance", "paths")
ID_PATTERNS = {
    "governing_prds": (re.compile(r"PRD-\d{4}", re.IGNORECASE), PRODUCT_DIR, "prd"),
    "governing_stories": (re.compile(r"US-\d{4}", re.IGNORECASE), STORIES_DIR, "us"),
    "governing_adrs": (re.compile(r"ADR-\d{4}", re.IGNORECASE), ADR_DIR, "adr"),
}


def write_if_changed(path: Path, original: str, updated: str) -> bool:
    if updated == original:
        return False
    path.write_text(updated, encoding="utf-8")
    return True


def fix_links() -> tuple[int, list[str]]:
    changed, errors = 0, []
    for record in active_records():
        original = record.read_text(encoding="utf-8")
        updated = original
        task = task_id_of(record)
        for target in set(iter_markdown_links(original)):
            if (record.parent / target).resolve().exists():
                continue
            key = (task, Path(target).name)
            if key not in LINK_MAP:
                errors.append(f"{record.name}: no LINK_MAP entry for {target}")
                continue
            replacement = LINK_MAP[key]
            if replacement is None:
                updated = re.sub(rf"\[([^\]]*)\]\({re.escape(target)}\)", r"\1", updated)
                continue
            new_target = str(Path(target).with_name(replacement))
            if not (record.parent / new_target).resolve().exists():
                errors.append(f"{record.name}: LINK_MAP target missing: {new_target}")
                continue
            updated = updated.replace(f"({target})", f"({new_target})")
        if write_if_changed(record, original, updated):
            changed += 1
    return changed, errors


def fix_references() -> int:
    changed = 0
    for record in active_records():
        task = task_id_of(record)
        original = record.read_text(encoding="utf-8")
        updated = original
        for (ref_task, old_id), new_id in REFERENCE_MAP.items():
            if ref_task == task:
                updated = updated.replace(f"\n- {old_id}\n", f"\n- {new_id}\n")
        if write_if_changed(record, original, updated):
            changed += 1
    return changed


def fix_status() -> int:
    changed = 0
    for record in complete_records():
        original = record.read_text(encoding="utf-8")
        front, _ = split_record(original)
        lines = original.split("\n")
        index = status_section_index(lines)
        if index is None or lines[index].strip() == str(front.get("status")):
            continue
        lines[index] = str(front.get("status"))
        if write_if_changed(record, original, "\n".join(lines)):
            changed += 1
    return changed


def governance_lines(key: str, body: str, known: set[str]) -> list[str]:
    """Return YAML lines for a missing governance key, or `key: []` when the body names none."""
    if key == "dependencies":
        return ["dependencies: []"]
    pattern = ID_PATTERNS[key][0]
    named = sorted({match.group(0).upper() for match in pattern.finditer(body)} & known)
    if not named:
        return [f"{key}: []"]
    return [f"{key}:"] + [f"- {ident}" for ident in named]


def fix_governance() -> int:
    known = {
        key: registry_ids(directory, prefix) for key, (_, directory, prefix) in ID_PATTERNS.items()
    }
    changed = 0
    for record in complete_records():
        original = record.read_text(encoding="utf-8")
        front, body = split_record(original)
        missing = [
            key
            for key in ("governing_prds", "governing_stories", "governing_adrs", "dependencies")
            if key not in front
        ]
        if not missing:
            continue
        lines = original.split("\n")
        _, close = frontmatter_bounds(lines)
        additions: list[str] = []
        for key in missing:
            additions.extend(governance_lines(key, body, known.get(key, set())))
        lines[close:close] = additions
        if write_if_changed(record, original, "\n".join(lines)):
            changed += 1
    return changed


def resolve_moved(path: str, dirs: set[str], by_name: dict[str, list[str]]) -> str | None:
    """Return a unique repository location for a missing path, or None when none is unique."""
    name = path.rstrip("/").rsplit("/", 1)[-1]
    if "." in name:
        candidates = by_name.get(name.lower(), [])
        if len(candidates) == 1:
            return candidates[0]
    parent = path.rstrip("/").rsplit("/", 1)[0] + "/"
    stem = name.split(".", 1)[0].lower().replace("-", "_")
    matches = [
        candidate
        for candidate in dirs
        if candidate.rstrip("/").rsplit("/", 1)[0] + "/" == parent
        and (
            stem == candidate.rstrip("/").rsplit("/", 1)[-1].lower().replace("-", "_")
            or stem.startswith(
                candidate.rstrip("/").rsplit("/", 1)[-1].lower().replace("-", "_") + "_"
            )
        )
    ]
    return matches[0] if len(matches) == 1 else None


def fix_paths(report: list[str]) -> int:
    tracked = tracked_files()
    by_name: dict[str, list[str]] = defaultdict(list)
    dirs: set[str] = set()
    for item in tracked:
        by_name[item.rsplit("/", 1)[-1].lower()].append(item)
        parts = item.split("/")[:-1]
        dirs.update("/".join(parts[:depth]) + "/" for depth in range(1, len(parts) + 1))
    changed = 0
    for record in complete_records():
        original = record.read_text(encoding="utf-8")
        edits: list[tuple[int, int, str]] = []
        for match, path, removed in repo_path_tokens(original):
            if removed or path_exists(path):
                continue
            task = task_id_of(record)
            if (task, path) in PATH_OVERRIDES:
                moved = PATH_OVERRIDES[(task, path)]
            else:
                moved = resolve_moved(path, dirs, by_name)
            if moved:
                raw = match.group(1)
                edits.append((match.start(1), match.end(1), raw.replace(path, moved, 1)))
                report.append(f"moved  {record.name}: {path} -> {moved}")
            else:
                edits.append((match.end(), match.end(), REMOVED_MARKS[0]))
                report.append(f"removed {record.name}: {path}")
        if not edits:
            continue
        updated = original
        for start, end, text in sorted(edits, reverse=True):
            updated = updated[:start] + text + updated[end:]
        if write_if_changed(record, original, updated):
            changed += 1
    return changed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument(
        "--step", action="append", choices=STEPS, help="run only this step (repeatable)"
    )
    args = parser.parse_args(argv)
    selected = args.step or list(STEPS)
    failed = False

    if "links" in selected:
        changed, errors = fix_links()
        print(f"links: {changed} file(s) changed")
        for error in errors:
            print(f"  ERROR {error}")
        failed = failed or bool(errors)
    if "references" in selected:
        print(f"references: {fix_references()} file(s) changed")
    if "status" in selected:
        print(f"status: {fix_status()} file(s) changed")
    if "governance" in selected:
        print(f"governance: {fix_governance()} file(s) changed")
    if "paths" in selected:
        report: list[str] = []
        changed = fix_paths(report)
        print(f"paths: {changed} file(s) changed, {len(report)} path(s) handled")
        for line in report:
            print(f"  {line}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
