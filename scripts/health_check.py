#!/usr/bin/env python3
"""Runefoble codebase health, invariant, and backlog triage scanner."""

import os
import re
from pathlib import Path

# Repo root is 1 level up from scripts/
REPO_ROOT = Path(__file__).resolve().parents[1]
BACKLOG_DIR = REPO_ROOT / "docs" / "project" / "backlog"


def inspect_file_lengths():
    print("--- 1. File Length Inspection (Hard Invariant: <500 lines) ---")
    scanned_dirs = ["libs", "services", "gateway", "frontend/src", "tests"]
    file_lengths = []

    for d in scanned_dirs:
        target_dir = REPO_ROOT / d
        if not target_dir.exists():
            continue
        for root, dirs, files in os.walk(target_dir):
            dirs[:] = [
                x
                for x in dirs
                if x
                not in {
                    "node_modules",
                    ".venv",
                    "dist",
                    "storybook-static",
                    "__pycache__",
                }
            ]
            for f in files:
                if f.endswith((".py", ".ts", ".js")):
                    fp = Path(root) / f
                    try:
                        with open(fp, encoding="utf-8", errors="ignore") as fh:
                            lines = sum(1 for _ in fh)
                        file_lengths.append((lines, fp.relative_to(REPO_ROOT)))
                    except Exception:
                        pass

    file_lengths.sort(key=lambda x: x[0], reverse=True)

    print("Top 10 Largest Source Files:")
    for lines, rel_path in file_lengths[:10]:
        print(f"  {lines:4d} lines : {rel_path}")
    print()

    violations = [x for x in file_lengths if x[0] > 500]
    warnings = [x for x in file_lengths if 400 < x[0] <= 500]

    if violations:
        print("⚠️ INVARIANT VIOLATIONS (>500 lines):")
        for lines, rel_path in violations:
            print(f"  ❌ {rel_path} ({lines} lines) - MUST BE DECOMPOSED")
    else:
        print("✅ Invariant Met: Zero source files exceed 500 lines.")

    if warnings:
        print("\n⚠️ Refactoring Candidates (>400 lines - approaching limit):")
        for lines, rel_path in warnings:
            print(f"  ⚡ {rel_path} ({lines} lines)")
    print()


def inspect_backlog_state():
    print("--- 2. Backlog State & JIT Buffer ---")
    complete_dir = BACKLOG_DIR / "complete"
    refined_dir = BACKLOG_DIR / "refined"
    proposed_dir = BACKLOG_DIR / "proposed"
    priority_file = BACKLOG_DIR / "PRIORITY.md"

    complete_tasks = list(complete_dir.glob("*.md")) if complete_dir.exists() else []
    refined_tasks = list(refined_dir.glob("*.md")) if refined_dir.exists() else []
    proposed_tasks = list(proposed_dir.glob("*.md")) if proposed_dir.exists() else []

    print(f"Completed Tasks: {len(complete_tasks)}")
    print(f"Refined Buffer (Ready to pull): {len(refined_tasks)}")
    print(f"Proposed Tasks (Unrefined pool): {len(proposed_tasks)}")
    print()

    if len(refined_tasks) < 8:
        print(
            f"👉 Action Needed: Ready buffer is low ({len(refined_tasks)} < 8). JIT refinement recommended."
        )
    elif len(refined_tasks) > 12:
        print(
            f"⚠️ Notice: Ready buffer has {len(refined_tasks)} items. Avoid over-refining to prevent specification drift."
        )
    else:
        print(
            f"✅ Ready buffer is optimal ({len(refined_tasks)} items). Team has immediate work without inventory waste."
        )
    print()

    print("--- 3. Discrepancy & Drift Check ---")
    if not priority_file.exists():
        print("⚠️ PRIORITY.md not found!")
        return

    priority_content = priority_file.read_text(encoding="utf-8")
    drift_found = False

    pattern = re.compile(
        r"\*\*TASK-(\d+)\s*\((Refined|Proposed|Complete)\)\*\*:\s*\[`?([^`\]]+)`?\]\(([^)]+)\)"
    )
    for match in pattern.finditer(priority_content):
        task_num, declared_status, filename, _ = match.groups()
        actual_complete = (complete_dir / filename).exists()
        actual_refined = (refined_dir / filename).exists()
        actual_proposed = (proposed_dir / filename).exists()

        if declared_status == "Refined" and actual_complete:
            print(
                f"⚠️ Status Drift: TASK-{task_num} is marked (Refined) in PRIORITY.md but exists in complete/{filename}"
            )
            drift_found = True
        elif declared_status == "Complete" and not actual_complete:
            print(
                f"⚠️ Status Drift: TASK-{task_num} is marked (Complete) in PRIORITY.md but missing in complete/{filename}"
            )
            drift_found = True
        elif declared_status == "Proposed" and actual_refined:
            print(
                f"⚠️ Status Drift: TASK-{task_num} is marked (Proposed) in PRIORITY.md but exists in refined/{filename}"
            )
            drift_found = True
        elif declared_status == "Proposed" and not actual_proposed:
            print(
                f"⚠️ Status Drift: TASK-{task_num} is marked (Proposed) in PRIORITY.md but missing in proposed/{filename}"
            )
            drift_found = True

    if not drift_found:
        print("✅ PRIORITY.md is synchronized with disk state.")
    print()


def main():
    print("=== Runefoble Codebase & Backlog Health Check ===")
    print(f"Repository Root: {REPO_ROOT}\n")
    inspect_file_lengths()
    inspect_backlog_state()
    print("=== Health Check Complete ===")


if __name__ == "__main__":
    main()
