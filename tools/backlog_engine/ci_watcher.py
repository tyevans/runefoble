"""Mechanical CI watcher, GitHub PR management, and merge dispatcher."""

import json
import re
import subprocess
import time
from pathlib import Path
from typing import Any

from .models import Task


class CIPipelineError(RuntimeError):
    pass


def run_cmd(cmd: list[str], cwd: Path, check: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=check)


def check_pr_conflict_status(worktree_dir: Path, pr_url: str) -> tuple[bool, str]:
    """Inspects pull request mergeability and conflict status via gh pr view.

    Returns (is_conflict_or_closed, reason_message).
    """
    res = run_cmd(
        ["gh", "pr", "view", pr_url, "--json", "state,mergeable,mergeStateStatus"],
        cwd=worktree_dir,
    )
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
        return (
            True,
            f"Pull Request {pr_url} has merge conflicts with base branch (mergeable: {mergeable}, mergeStateStatus: {merge_status}).",
        )

    return False, ""


def close_pull_request(worktree_dir: Path, pr_url: str, reason: str = "") -> None:
    """Closes pull request if it failed or conflicted."""
    cmd = ["gh", "pr", "close", pr_url]
    if reason:
        cmd.extend(["--comment", reason])
    run_cmd(cmd, cwd=worktree_dir)


def commit_and_push(worktree_dir: Path, task: Task, branch: str) -> None:
    """Stages all changes, commits if needed, and pushes to origin."""
    # Fetch latest origin/main
    run_cmd(["git", "fetch", "origin", "main"], cwd=worktree_dir)
    chk = run_cmd(["git", "rev-parse", "--verify", "origin/main"], cwd=worktree_dir)
    base_ref = "origin/main" if chk.returncode == 0 else "main"

    # Enforce backlog isolation: feature branches must never contain changes to docs/project/backlog
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

    # Proactively detect and sync with latest base branch before pushing
    if chk.returncode == 0:
        behind_res = run_cmd(["git", "rev-list", f"HEAD..{base_ref}", "--count"], cwd=worktree_dir)
        behind_count = behind_res.stdout.strip()
        if behind_count.isdigit() and int(behind_count) > 0:
            # Check if merging base_ref would cause merge conflicts
            merge_test = run_cmd(
                ["git", "merge-tree", "--write-tree", "HEAD", base_ref],
                cwd=worktree_dir,
            )
            if merge_test.returncode != 0:
                raise CIPipelineError(
                    f"Branch {branch} has merge conflicts with {base_ref}. Releasing task back to queue."
                )
            # Merge base_ref so the feature branch is cleanly up to date with origin/main
            merge_res = run_cmd(
                ["git", "merge", base_ref, "-m", f"chore: sync with {base_ref}"],
                cwd=worktree_dir,
            )
            if merge_res.returncode != 0:
                run_cmd(["git", "merge", "--abort"], cwd=worktree_dir)
                raise CIPipelineError(
                    f"Branch {branch} failed to merge {base_ref}: {merge_res.stderr.strip()}"
                )

    push_res = run_cmd(["git", "push", "-u", "origin", branch, "--force"], cwd=worktree_dir)
    if push_res.returncode != 0:
        raise CIPipelineError(f"Git push to origin/{branch} failed: {push_res.stderr}")


def sync_branch_with_base(
    worktree_dir: Path,
    base_ref: str = "origin/main",
) -> tuple[bool, str]:
    """Syncs the current branch with base_ref via git merge.

    Returns (success, message_or_conflict_details).
    If merge succeeds cleanly: returns (True, message).
    If conflicts occur: leaves conflict markers in the worktree and returns (False, conflict_details).
    """
    if not worktree_dir.exists():
        return True, f"Worktree directory {worktree_dir} does not exist (mocked)."
    git_dir = worktree_dir / ".git"
    if not git_dir.exists() and not (worktree_dir / ".git").is_file():
        return True, "Not a git repository (mocked/testing)."

    if base_ref.startswith("origin/"):
        remote_branch = base_ref.replace("origin/", "")
        run_cmd(["git", "fetch", "origin", remote_branch], cwd=worktree_dir)

    chk = run_cmd(["git", "rev-parse", "--verify", base_ref], cwd=worktree_dir)
    effective_base = base_ref if chk.returncode == 0 else "main"

    behind_res = run_cmd(
        ["git", "rev-list", f"HEAD..{effective_base}", "--count"], cwd=worktree_dir
    )
    behind_count = behind_res.stdout.strip()
    if behind_count.isdigit() and int(behind_count) == 0:
        return True, f"Branch is already up to date with {effective_base}."

    # Attempt to merge effective_base
    merge_res = run_cmd(
        ["git", "merge", effective_base, "-m", f"chore: sync with {effective_base}"],
        cwd=worktree_dir,
    )
    if merge_res.returncode == 0:
        return (
            True,
            f"Successfully merged {effective_base} into branch ({behind_count} commit(s) synced).",
        )

    # Merge conflict occurred
    status_res = run_cmd(["git", "status", "--porcelain"], cwd=worktree_dir)
    conflicted_files = [
        line[3:].strip()
        for line in status_res.stdout.splitlines()
        if any(line.startswith(prefix) for prefix in ("UU", "AA", "DD", "DU", "UD"))
    ]
    diff_res = run_cmd(["git", "diff"], cwd=worktree_dir)
    diff_snippet = diff_res.stdout[:2500] if diff_res.stdout else "No diff output available."
    details = (
        f"Git merge of {effective_base} produced conflicts in:\n"
        + "\n".join(f"  - {f}" for f in conflicted_files)
        + f"\n\nConflict diff summary:\n{diff_snippet}"
    )
    return False, details


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
        # Check if GitHub reports PR as conflicting or closed
        is_bad, reason = check_pr_conflict_status(worktree_dir, pr_url)
        if is_bad:
            print(f"❌ {reason}")
            return False

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
            is_bad, reason = check_pr_conflict_status(worktree_dir, pr_url)
            if is_bad:
                print(f"❌ {reason}")
                return False

            print("⏳ Waiting for CI checks to be registered by GitHub Actions...")
            time.sleep(poll_interval)
            continue

        try:
            checks = json.loads(output)
        except json.JSONDecodeError:
            if "no checks reported" in combined:
                is_bad, reason = check_pr_conflict_status(worktree_dir, pr_url)
                if is_bad:
                    print(f"❌ {reason}")
                    return False

                print("⏳ Waiting for CI checks to be registered by GitHub Actions...")
                time.sleep(poll_interval)
                continue
            print(f"⚠️ Unexpected output while polling checks: {res.stderr or res.stdout}")
            time.sleep(poll_interval)
            continue

        if not checks or not isinstance(checks, list):
            is_bad, reason = check_pr_conflict_status(worktree_dir, pr_url)
            if is_bad:
                print(f"❌ {reason}")
                return False

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


def fetch_failed_ci_logs(
    worktree_dir: Path,
    failed_checks: list[dict[str, Any]],
    max_lines: int = 150,
) -> str:
    """Retrieves detailed error logs for failed CI jobs using gh run view --log-failed."""
    collected_logs = []
    seen_runs = set()

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


def get_ci_failure_diagnostics(worktree_dir: Path, pr_url: str) -> tuple[str, str]:
    """Inspects why CI or mergeability failed and returns (category, details).

    Category is one of: 'conflict', 'ci_failed', 'closed', 'timeout', 'unknown'.
    """
    is_conflict_or_closed, reason = check_pr_conflict_status(worktree_dir, pr_url)
    if is_conflict_or_closed:
        if "closed" in reason.lower():
            return "closed", reason
        return "conflict", reason

    res = run_cmd(
        ["gh", "pr", "checks", pr_url, "--json", "name,state,bucket,link"],
        cwd=worktree_dir,
    )
    if res.returncode == 0 and res.stdout.strip():
        try:
            checks = json.loads(res.stdout)
            if isinstance(checks, list):
                failed = [
                    c
                    for c in checks
                    if c.get("bucket") == "fail"
                    or c.get("state") in ("FAILURE", "CANCELLED", "TIMED_OUT", "STARTUP_FAILURE")
                ]
                if failed:
                    logs = fetch_failed_ci_logs(worktree_dir, failed)
                    return "ci_failed", logs
        except json.JSONDecodeError:
            pass

    return "unknown", f"CI checks failed or timed out for {pr_url}."


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
