"""Mechanical CI watcher, GitHub PR management, and merge dispatcher."""

import json
import subprocess
import time
from pathlib import Path

from .models import Task


class CIPipelineError(RuntimeError):
    pass


def run_cmd(cmd: list[str], cwd: Path, check: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=check)


def commit_and_push(worktree_dir: Path, task: Task, branch: str) -> None:
    """Stages all changes, commits if needed, and pushes to origin."""
    # Enforce backlog isolation: feature branches must never contain changes to docs/project/backlog
    chk = run_cmd(["git", "rev-parse", "--verify", "origin/main"], cwd=worktree_dir)
    base_ref = "origin/main" if chk.returncode == 0 else "main"
    run_cmd(["git", "checkout", base_ref, "--", "docs/project/backlog"], cwd=worktree_dir)
    run_cmd(["git", "clean", "-fd", "docs/project/backlog"], cwd=worktree_dir)

    run_cmd(["git", "add", "-A"], cwd=worktree_dir, check=True)

    status = run_cmd(["git", "status", "--porcelain"], cwd=worktree_dir)
    if status.stdout.strip():
        commit_msg = (
            f"feat({task.canonical_id.lower()}): {task.title}\n\n"
            f"Automated execution of {task.canonical_id}.\n"
            f"Governing ADRs: {', '.join(task.governing_adrs) if task.governing_adrs else 'None'}"
        )
        res = run_cmd(["git", "commit", "-m", commit_msg], cwd=worktree_dir)
        if res.returncode != 0:
            raise CIPipelineError(f"Git commit failed: {res.stderr}")

    push_res = run_cmd(["git", "push", "-u", "origin", branch, "--force"], cwd=worktree_dir)
    if push_res.returncode != 0:
        raise CIPipelineError(f"Git push to origin/{branch} failed: {push_res.stderr}")


def create_pull_request(worktree_dir: Path, task: Task, branch: str) -> str:
    """Creates a pull request via GitHub CLI gh and returns the PR URL."""
    pr_title = f"feat({task.canonical_id.lower()}): {task.title}"
    pr_body = (
        f"## {task.canonical_id} — {task.title}\n\n"
        f"Automated delivery pipeline execution.\n\n"
        f"### Governing Records\n"
        f"- Dependencies: `{', '.join(task.dependencies) if task.dependencies else 'None'}`\n"
        f"- ADRs: `{', '.join(task.governing_adrs) if task.governing_adrs else 'None'}`\n\n"
        f"### Specification\n{task.body.strip()}\n"
    )

    # Check if PR already exists for this branch
    list_res = run_cmd(
        ["gh", "pr", "list", "--head", branch, "--json", "url", "-q", ".[0].url"],
        cwd=worktree_dir,
    )
    existing_url = list_res.stdout.strip()
    if existing_url:
        return existing_url

    create_res = run_cmd(
        [
            "gh",
            "pr",
            "create",
            "--base",
            "main",
            "--head",
            branch,
            "--title",
            pr_title,
            "--body",
            pr_body,
        ],
        cwd=worktree_dir,
    )

    if create_res.returncode != 0:
        raise CIPipelineError(f"Failed to create PR with gh: {create_res.stderr.strip()}")

    pr_url = create_res.stdout.strip()
    return pr_url


def wait_for_ci_checks(
    worktree_dir: Path,
    pr_url: str,
    timeout_seconds: int = 1200,
    poll_interval: int = 10,
) -> bool:
    """Mechanically watches GitHub CI checks using gh until pass or fail.

    Zero LLM tokens consumed.
    """
    print(f"⏳ Watching CI checks for PR: {pr_url}...")
    start_time = time.time()

    while time.time() - start_time < timeout_seconds:
        res = run_cmd(
            [
                "gh",
                "pr",
                "checks",
                pr_url,
                "--json",
                "name,state,bucket,link",
            ],
            cwd=worktree_dir,
        )

        output = res.stdout.strip()
        combined = f"{res.stdout}\n{res.stderr}".lower()

        # Check if GitHub Actions hasn't reported/registered any checks yet
        if "no checks reported" in combined or not output:
            print("⏳ Waiting for CI checks to be registered by GitHub Actions...")
            time.sleep(poll_interval)
            continue

        try:
            checks = json.loads(output)
        except json.JSONDecodeError:
            if "no checks reported" in combined:
                print("⏳ Waiting for CI checks to be registered by GitHub Actions...")
                time.sleep(poll_interval)
                continue
            print(f"⚠️ Unexpected output while polling checks: {res.stderr or res.stdout}")
            time.sleep(poll_interval)
            continue

        if not checks or not isinstance(checks, list):
            print("⏳ Waiting for CI checks to be registered by GitHub Actions...")
            time.sleep(poll_interval)
            continue

        pending = [
            c
            for c in checks
            if c.get("bucket") == "pending"
            or c.get("state") in ("PENDING", "QUEUED", "IN_PROGRESS", "WAITING", "REQUESTED")
        ]
        failed = [
            c
            for c in checks
            if c.get("bucket") == "fail"
            or c.get("state") in ("FAILURE", "CANCELLED", "TIMED_OUT", "STARTUP_FAILURE")
        ]

        if pending:
            names = ", ".join(c.get("name", "unknown") for c in pending)
            print(f"⏳ CI checks in progress ({len(pending)} pending): {names}...")
            time.sleep(poll_interval)
            continue

        if failed:
            print("❌ CI checks reported failure:")
            for f in failed:
                print(f"  - {f.get('name')}: {f.get('state')} ({f.get('link', '')})")
            return False

        # If checks list is non-empty, none pending, and none failed
        print("✅ All CI checks passed successfully.")
        return True

    print(f"⚠️ CI check timeout after {timeout_seconds}s.")
    return False


def merge_pull_request(worktree_dir: Path, pr_url: str) -> None:
    """Merges the pull request using GitHub CLI gh with squash and branch deletion."""
    print(f"🔀 Merging PR {pr_url} via gh pr merge...")
    res = run_cmd(
        ["gh", "pr", "merge", pr_url, "--squash", "--delete-branch", "--auto"],
        cwd=worktree_dir,
    )

    if res.returncode != 0:
        # Fallback to direct squash merge if auto-merge is disabled
        direct_res = run_cmd(
            ["gh", "pr", "merge", pr_url, "--squash", "--delete-branch"],
            cwd=worktree_dir,
        )
        if direct_res.returncode != 0:
            raise CIPipelineError(f"Failed to merge PR: {direct_res.stderr.strip()}")

    print("🎉 PR successfully merged and remote branch deleted.")


def merge_local_branch(repo_root: Path, branch: str, task: Task) -> None:
    """Local fallback merge: merges worktree branch into main without pushing."""
    print(f"🔀 Merging {branch} locally into main...")
    run_cmd(["git", "checkout", "main"], cwd=repo_root, check=True)
    msg = f"feat({task.canonical_id.lower()}): {task.title}"
    run_cmd(["git", "merge", "--squash", branch], cwd=repo_root, check=True)
    status = run_cmd(["git", "status", "--porcelain"], cwd=repo_root)
    if status.stdout.strip():
        run_cmd(["git", "commit", "-m", msg], cwd=repo_root, check=True)
    print("🎉 Local branch merged cleanly into main.")
