"""GitHub CLI (gh) subprocess wrapper for pull requests, checks, and logs."""

import json
import re
import subprocess
from pathlib import Path
from typing import Any

from .models import Task


def run_cmd(cmd: list[str], cwd: Path, check: bool = False) -> subprocess.CompletedProcess:
    """Executes a subprocess command in the given working directory."""
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=check)


def check_pr_conflict_status(worktree_dir: Path, pr_url: str) -> tuple[bool, str]:
    """Inspects pull request mergeability and conflict status via gh pr view."""
    cmd = ["gh", "pr", "view", pr_url, "--json", "state,mergeable,mergeStateStatus"]
    res = run_cmd(cmd, cwd=worktree_dir)
    if res.returncode != 0:
        return False, ""
    try:
        data = json.loads(res.stdout)
    except json.JSONDecodeError:
        return False, ""
    if not isinstance(data, dict):
        return False, ""

    state = str(data.get("state", "")).upper()
    if state == "CLOSED":
        return True, f"Pull Request {pr_url} was closed."

    mergeable = str(data.get("mergeable", "")).upper()
    merge_status = str(data.get("mergeStateStatus", "")).upper()
    if mergeable == "CONFLICTING" or merge_status == "DIRTY":
        msg = f"Pull Request {pr_url} has merge conflicts with base branch (mergeable: {mergeable}, mergeStateStatus: {merge_status})."
        return True, msg

    return False, ""


def close_pull_request(worktree_dir: Path, pr_url: str, reason: str = "") -> None:
    """Closes pull request if it failed or conflicted."""
    cmd = ["gh", "pr", "close", pr_url]
    if reason:
        cmd.extend(["--comment", reason])
    run_cmd(cmd, cwd=worktree_dir)


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

    list_cmd = ["gh", "pr", "list", "--head", branch, "--json", "url", "-q", ".[0].url"]
    existing_url = run_cmd(list_cmd, cwd=worktree_dir).stdout.strip()
    if existing_url:
        return existing_url

    create_cmd = [
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
    ]
    create_res = run_cmd(create_cmd, cwd=worktree_dir)
    if create_res.returncode != 0:
        from .git_ops import CIPipelineError

        raise CIPipelineError(f"Failed to create PR with gh: {create_res.stderr.strip()}")
    return create_res.stdout.strip()


def fetch_failed_ci_logs(
    worktree_dir: Path,
    failed_checks: list[dict[str, Any]],
    max_lines: int = 150,
) -> str:
    """Retrieves detailed error logs for failed CI jobs using gh run view --log-failed."""
    collected_logs = []
    seen_runs: set[str] = set()

    for check in failed_checks:
        link = str(check.get("link", ""))
        name = str(check.get("name", "Unknown Check"))
        run_match = re.search(r"/actions/runs/(\d+)", link)
        if not run_match:
            collected_logs.append(f"❌ Check '{name}' failed ({link or 'no link'})")
            continue

        run_id = run_match.group(1)
        if run_id in seen_runs:
            continue
        seen_runs.add(run_id)

        job_match = re.search(r"/job/(\d+)", link)
        job_arg = ["--job", job_match.group(1)] if job_match else []
        cmd = ["gh", "run", "view", run_id, "--log-failed"] + job_arg
        res = run_cmd(cmd, cwd=worktree_dir)

        if res.returncode == 0 and res.stdout.strip():
            log_lines = res.stdout.strip().splitlines()
            if len(log_lines) > max_lines:
                tail = "\n".join(log_lines[-max_lines:])
                collected_logs.append(f"❌ Check '{name}' failed (Run {run_id}):\n...\n{tail}")
            else:
                collected_logs.append(
                    f"❌ Check '{name}' failed (Run {run_id}):\n{res.stdout.strip()}"
                )
        else:
            collected_logs.append(f"❌ Check '{name}' failed: {check.get('state')} ({link})")

    return "\n\n".join(collected_logs)


def fetch_pr_checks(worktree_dir: Path, pr_url: str) -> subprocess.CompletedProcess:
    """Queries check runs for a PR via gh pr checks."""
    return run_cmd(
        ["gh", "pr", "checks", pr_url, "--json", "name,state,bucket,link"], cwd=worktree_dir
    )


def merge_pull_request(worktree_dir: Path, pr_url: str) -> None:
    """Merges the pull request using GitHub CLI gh with squash and branch deletion."""
    print(f"🔀 Merging PR {pr_url} via gh pr merge...")
    res = run_cmd(
        ["gh", "pr", "merge", pr_url, "--squash", "--delete-branch", "--auto"], cwd=worktree_dir
    )
    if res.returncode != 0:
        direct_res = run_cmd(
            ["gh", "pr", "merge", pr_url, "--squash", "--delete-branch"], cwd=worktree_dir
        )
        if direct_res.returncode != 0:
            from .git_ops import CIPipelineError

            raise CIPipelineError(f"Failed to merge PR: {direct_res.stderr.strip()}")
    print("🎉 PR successfully merged and remote branch deleted.")
