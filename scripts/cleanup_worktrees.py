#!/usr/bin/env python3
"""Runefoble Git Worktree Cleanup Maintenance Tool.

Safely audits and cleans up obsolete, merged, and orphaned git worktrees
across both local .worktrees/ and Antigravity workspace cache directories,
while strictly protecting active processes and uncommitted work.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class WorktreeInfo:
    path: Path
    branch: str | None
    head: str
    is_main: bool = False
    is_dirty: bool = False
    dirty_count: int = 0
    is_merged: bool = False
    # None means the process table could not be read: the guard fails closed.
    active_pids: list[int] | None = None
    pr_state: str | None = None


@dataclass(frozen=True)
class CleanupOptions:
    force: bool = False
    clean_all: bool = False


@dataclass(frozen=True)
class Decision:
    remove: bool
    reason: str


DEFAULT_PROC_DIR = Path("/proc")


def run_cmd(
    cmd: list[str], cwd: Path | None = None, check: bool = False
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=check,
    )


def get_repo_root() -> Path:
    res = run_cmd(["git", "rev-parse", "--show-toplevel"])
    if res.returncode != 0:
        print("Error: not inside a git repository.", file=sys.stderr)
        sys.exit(1)
    return Path(res.stdout.strip()).resolve()


def find_active_pids_for_path(path: Path, proc_dir: Path = DEFAULT_PROC_DIR) -> list[int] | None:
    """Return the PIDs whose working directory is inside path.

    Return None when proc_dir is absent. The caller cannot verify that the
    worktree is idle, so it must not remove the worktree.
    """
    if not proc_dir.is_dir():
        return None

    active_pids: list[int] = []
    resolved = path.resolve()
    for entry in proc_dir.iterdir():
        if not entry.name.isdigit():
            continue
        try:
            cwd_path = Path(os.readlink(entry / "cwd")).resolve()
        except OSError:
            # The process ended, or it belongs to another user.
            continue
        if cwd_path == resolved or resolved in cwd_path.parents:
            active_pids.append(int(entry.name))
    return active_pids


def decide(wt: WorktreeInfo, options: CleanupOptions) -> Decision:
    """Decide if a worktree is safe to remove. Pure: no I/O."""
    if wt.active_pids is None:
        return Decision(False, "cannot verify active processes (no process table)")
    if wt.active_pids:
        return Decision(False, f"Active process detected (PIDs: {wt.active_pids})")
    if not wt.is_merged and not options.clean_all:
        return Decision(False, f"Branch is unmerged ({wt.pr_state}). Use --all to clean.")
    if wt.is_dirty and not options.force:
        return Decision(
            False, f"Uncommitted changes ({wt.dirty_count} files). Use --force to override."
        )
    return Decision(True, wt.pr_state or "eligible")


def parse_worktrees(repo_root: Path) -> list[WorktreeInfo]:
    res = run_cmd(["git", "worktree", "list", "--porcelain"], cwd=repo_root)
    if res.returncode != 0:
        return []

    worktrees: list[WorktreeInfo] = []
    current_path: Path | None = None
    current_head: str = ""
    current_branch: str | None = None

    for line in res.stdout.strip().split("\n"):
        if not line:
            if current_path:
                is_main = current_path.resolve() == repo_root.resolve()
                worktrees.append(
                    WorktreeInfo(
                        path=current_path,
                        branch=current_branch,
                        head=current_head,
                        is_main=is_main,
                    )
                )
                current_path = None
                current_head = ""
                current_branch = None
            continue

        parts = line.split(" ", 1)
        key = parts[0]
        val = parts[1] if len(parts) > 1 else ""

        if key == "worktree":
            current_path = Path(val).resolve()
        elif key == "HEAD":
            current_head = val
        elif key == "branch":
            current_branch = val.replace("refs/heads/", "")

    if current_path:
        is_main = current_path.resolve() == repo_root.resolve()
        worktrees.append(
            WorktreeInfo(
                path=current_path,
                branch=current_branch,
                head=current_head,
                is_main=is_main,
            )
        )

    return worktrees


def is_branch_merged(repo_root: Path, branch: str, head: str) -> tuple[bool, str]:
    """Checks if a commit/branch is merged into origin/main or main."""
    # 1. Direct ancestor check
    for base in ("origin/main", "main"):
        chk = run_cmd(["git", "rev-parse", "--verify", base], cwd=repo_root)
        if chk.returncode == 0:
            anc = run_cmd(
                ["git", "merge-base", "--is-ancestor", head, base],
                cwd=repo_root,
            )
            if anc.returncode == 0:
                return True, f"Ancestor of {base}"

    # 2. Cherry-pick / squash detection via git cherry
    chk_origin = run_cmd(["git", "rev-parse", "--verify", "origin/main"], cwd=repo_root)
    base_ref = "origin/main" if chk_origin.returncode == 0 else "main"
    cherry_res = run_cmd(["git", "cherry", base_ref, head], cwd=repo_root)
    if cherry_res.returncode == 0 and cherry_res.stdout.strip():
        lines = cherry_res.stdout.strip().split("\n")
        if all(line.startswith("-") for line in lines):
            return True, f"Squash-merged into {base_ref}"

    # 3. Check GitHub CLI if available
    gh_path = shutil.which("gh")
    if gh_path and branch:
        pr_res = run_cmd(
            ["gh", "pr", "list", "--state", "all", "--head", branch, "--json", "state"],
            cwd=repo_root,
        )
        if pr_res.returncode == 0 and '"state":"MERGED"' in pr_res.stdout:
            return True, "Merged pull request on GitHub"

    return False, "Unmerged"


def inspect_worktrees(repo_root: Path, proc_dir: Path = DEFAULT_PROC_DIR) -> list[WorktreeInfo]:
    worktrees = parse_worktrees(repo_root)
    for wt in worktrees:
        if wt.is_main:
            continue

        wt.active_pids = find_active_pids_for_path(wt.path, proc_dir)

        if wt.path.exists():
            st = run_cmd(["git", "status", "--porcelain"], cwd=wt.path)
            dirty_files = [line for line in st.stdout.strip().split("\n") if line]
            wt.is_dirty = len(dirty_files) > 0
            wt.dirty_count = len(dirty_files)

        if wt.branch:
            merged, reason = is_branch_merged(repo_root, wt.branch, wt.head)
            wt.is_merged = merged
            wt.pr_state = reason
        else:
            wt.is_merged = False
            wt.pr_state = "Detached HEAD"

    return worktrees


def remove_worktree(repo_root: Path, wt: WorktreeInfo, force: bool, delete_branch: bool) -> bool:
    """Remove one worktree and, if asked, its local branch. Return True on success."""
    rm_args = ["git", "worktree", "remove"]
    if force or wt.is_dirty:
        rm_args.append("--force")
    rm_args.append(str(wt.path))
    res_rm = run_cmd(rm_args, cwd=repo_root)
    if res_rm.returncode != 0:
        print(f"  ERROR: could not remove worktree: {res_rm.stderr.strip()}")
        return False
    print("  Worktree removed.")

    if delete_branch and wt.branch:
        del_res = run_cmd(["git", "branch", "-d", wt.branch], cwd=repo_root)
        if del_res.returncode != 0:
            # A squash-merged branch, or an unmerged branch with --all, needs -D.
            del_res = run_cmd(["git", "branch", "-D", wt.branch], cwd=repo_root)
        if del_res.returncode == 0:
            print(f"  Deleted branch: {wt.branch}")
        else:
            print(f"  WARNING: could not delete branch {wt.branch}: {del_res.stderr.strip()}")

    parent = wt.path.parent
    if parent.is_dir() and not any(parent.iterdir()):
        try:
            parent.rmdir()
        except OSError as error:
            print(f"  WARNING: could not remove empty directory {parent}: {error}")
    return True


def cleanup_worktrees(
    repo_root: Path,
    dry_run: bool = False,
    force: bool = False,
    delete_branches: bool = True,
    clean_all: bool = False,
    proc_dir: Path = DEFAULT_PROC_DIR,
) -> int:
    print(f"==> Inspecting Git worktrees for {repo_root.name}...")
    options = CleanupOptions(force=force, clean_all=clean_all)
    cleaned_count = 0
    failed_count = 0

    for wt in inspect_worktrees(repo_root, proc_dir):
        if wt.is_main:
            continue
        print(f"\nWorktree: {wt.path} [{wt.branch or 'DETACHED'}]")
        decision = decide(wt, options)
        if not decision.remove:
            print(f"  SKIPPED: {decision.reason}")
            continue
        if dry_run:
            print(f"  WOULD REMOVE worktree ({decision.reason})")
            if delete_branches and wt.branch:
                print(f"  WOULD DELETE local branch: {wt.branch}")
            cleaned_count += 1
            continue
        print(f"  Removing worktree ({decision.reason})...")
        if remove_worktree(repo_root, wt, force, delete_branches):
            cleaned_count += 1
        else:
            failed_count += 1

    if not dry_run:
        prune = run_cmd(["git", "worktree", "prune"], cwd=repo_root)
        if prune.returncode != 0:
            print(f"\nERROR: git worktree prune failed: {prune.stderr.strip()}")
            failed_count += 1
        else:
            print("\n==> Pruned git worktree records.")

    action_word = "Would clean" if dry_run else "Cleaned"
    print(f"\n{action_word} {cleaned_count} worktree(s).")
    return 1 if failed_count else 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Clean up merged, stale, and orphaned git worktrees safely."
    )
    parser.add_argument(
        "--dry-run",
        "-n",
        action="store_true",
        help="Preview worktrees to remove without making changes.",
    )
    parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Force removal even if worktree has uncommitted changes.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Clean unmerged worktrees as well (requires confirmation or --force).",
    )
    parser.add_argument(
        "--no-delete-branches",
        action="store_true",
        help="Keep local git branches after removing worktrees.",
    )

    parser.add_argument(
        "--proc-dir",
        type=Path,
        default=DEFAULT_PROC_DIR,
        help="Process table to scan for processes inside a worktree (default: /proc). "
        "When it is absent, no worktree is removed.",
    )

    args = parser.parse_args()
    repo_root = get_repo_root()
    return cleanup_worktrees(
        repo_root=repo_root,
        dry_run=args.dry_run,
        force=args.force,
        delete_branches=not args.no_delete_branches,
        clean_all=args.all,
        proc_dir=args.proc_dir,
    )


if __name__ == "__main__":
    sys.exit(main())
