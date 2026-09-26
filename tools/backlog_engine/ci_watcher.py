"""Mechanical CI watcher, status checks, error diagnostics, and repair dispatcher."""

import json
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .agent_worker import build_ci_repair_prompt, run_agent_in_worktree
from .git_ops import (
    CIPipelineError,
    commit_and_push,
    merge_local_branch,
    run_cmd,
    sync_and_resolve_base_ref,
    sync_branch_with_base,
)
from .github_client import (
    check_pr_conflict_status,
    close_pull_request,
    create_pull_request,
    fetch_failed_ci_logs,
    merge_pull_request,
)
from .models import Task
from .worktree import run_preflight_checks

__all__ = [
    "CIPipelineError",
    "check_pr_conflict_status",
    "close_pull_request",
    "commit_and_push",
    "create_pull_request",
    "fetch_failed_ci_logs",
    "get_ci_failure_diagnostics",
    "merge_local_branch",
    "merge_pull_request",
    "run_cmd",
    "sync_and_resolve_base_ref",
    "sync_branch_with_base",
    "wait_for_ci_checks",
    "watch_and_repair_pull_request",
]

PENDING_STATES = {"PENDING", "QUEUED", "IN_PROGRESS", "WAITING", "REQUESTED"}
FAILED_STATES = {"FAILURE", "CANCELLED", "TIMED_OUT", "STARTUP_FAILURE"}


def _check_conflict_or_delay(worktree_dir: Path, pr_url: str, poll_interval: int) -> bool:
    """Checks for conflict/closed status or sleeps if checks are pending registration."""
    is_bad, reason = check_pr_conflict_status(worktree_dir, pr_url)
    if is_bad:
        print(f"❌ {reason}")
        return False
    print("⏳ Waiting for CI checks to be registered by GitHub Actions...")
    time.sleep(poll_interval)
    return True


def wait_for_ci_checks(
    worktree_dir: Path,
    pr_url: str,
    timeout_seconds: int = 1200,
    poll_interval: int = 10,
) -> bool:
    """Mechanically watches GitHub CI checks using gh until pass or fail."""
    print(f"⏳ Watching CI checks for PR: {pr_url}...")
    start_time = time.time()

    while time.time() - start_time < timeout_seconds:
        is_bad, reason = check_pr_conflict_status(worktree_dir, pr_url)
        if is_bad:
            print(f"❌ {reason}")
            return False

        res = run_cmd(
            ["gh", "pr", "checks", pr_url, "--json", "name,state,bucket,link"],
            cwd=worktree_dir,
        )
        output, combined = res.stdout.strip(), f"{res.stdout}\n{res.stderr}".lower()
        if "no checks reported" in combined or not output:
            if not _check_conflict_or_delay(worktree_dir, pr_url, poll_interval):
                return False
            continue

        try:
            checks = json.loads(output)
        except json.JSONDecodeError:
            checks = None

        if not isinstance(checks, list):
            if "no checks reported" in combined:
                if not _check_conflict_or_delay(worktree_dir, pr_url, poll_interval):
                    return False
            else:
                print(f"⚠️ Unexpected output while polling checks: {res.stderr or res.stdout}")
                time.sleep(poll_interval)
            continue

        pending = [
            c for c in checks if c.get("bucket") == "pending" or c.get("state") in PENDING_STATES
        ]
        failed = [c for c in checks if c.get("bucket") == "fail" or c.get("state") in FAILED_STATES]

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

        print("✅ All CI checks passed successfully.")
        return True

    print(f"⚠️ CI check timeout after {timeout_seconds}s.")
    return False


def get_ci_failure_diagnostics(worktree_dir: Path, pr_url: str) -> tuple[str, str]:
    """Inspects why CI or mergeability failed and returns (category, details)."""
    is_conflict_or_closed, reason = check_pr_conflict_status(worktree_dir, pr_url)
    if is_conflict_or_closed:
        return ("closed", reason) if "closed" in reason.lower() else ("conflict", reason)

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
                    if c.get("bucket") == "fail" or c.get("state") in FAILED_STATES
                ]
                if failed:
                    return "ci_failed", fetch_failed_ci_logs(worktree_dir, failed)
        except json.JSONDecodeError:
            pass

    return "unknown", f"CI checks failed or timed out for {pr_url}."


def _get_orch_dep(name: str, default: Callable[..., Any]) -> Callable[..., Any]:
    orch = sys.modules.get("tools.backlog_engine.orchestrator")
    return getattr(orch, name, default) if orch else default


def watch_and_repair_pull_request(
    worktree_dir: Path,
    task: Task,
    branch: str,
    pr_url: str,
    worker_id: str,
    skip_agent: bool = False,
    max_ci_repairs: int = 3,
) -> bool:
    """Watches CI checks on PR and runs an in-worktree agent repair loop on failure or conflicts."""
    wait_ci = _get_orch_dep("wait_for_ci_checks", wait_for_ci_checks)
    get_diag = _get_orch_dep("get_ci_failure_diagnostics", get_ci_failure_diagnostics)
    sync_base = _get_orch_dep("sync_and_resolve_base_ref", sync_and_resolve_base_ref)
    run_agent = _get_orch_dep("run_agent_in_worktree", run_agent_in_worktree)
    preflight = _get_orch_dep("run_preflight_checks", run_preflight_checks)
    push_fn = _get_orch_dep("commit_and_push", commit_and_push)

    ci_repair_attempt = 0
    while ci_repair_attempt <= max_ci_repairs:
        if wait_ci(worktree_dir, pr_url):
            return True

        ci_repair_attempt += 1
        if ci_repair_attempt > max_ci_repairs or skip_agent:
            break

        category, failure_details = get_diag(worktree_dir, pr_url)
        print(
            f"\n⚠️ [Stream {worker_id}] CI failure ({ci_repair_attempt}/{max_ci_repairs}): {category}\n{failure_details}"
        )

        print(f"🔄 [Stream {worker_id}] Syncing branch with latest origin/main...")
        sync_ok, sync_msg = sync_base(
            worktree_dir, task, base_ref="origin/main", skip_agent=skip_agent
        )
        if not sync_ok:
            print(f"⚠️ [Stream {worker_id}] Merge conflict resolution failed: {sync_msg}")

        if category == "ci_failed" or not sync_ok:
            print(f"🤖 [Stream {worker_id}] Invoking agent to repair CI failure...")
            ci_prompt = build_ci_repair_prompt(task, pr_url, failure_details)
            agent_ok, agent_log = run_agent(worktree_dir, task, custom_prompt=ci_prompt)
            if not agent_ok:
                print(f"⚠️ [Stream {worker_id}] Agent repair attempt failed: {agent_log}")
                continue

        print(f"🔍 [Stream {worker_id}] Running pre-flight verification after CI repair...")
        preflight_ok, preflight_log = preflight(worktree_dir)
        if not preflight_ok:
            agent_ok, agent_log = run_agent(worktree_dir, task, feedback=preflight_log)
            preflight_ok, preflight_log = preflight(worktree_dir)
            if not preflight_ok:
                print(f"⚠️ [Stream {worker_id}] Pre-flight verification still failing.")
                continue

        print(f"🌐 [Stream {worker_id}] Pushing CI fixes to origin/{branch}...")
        try:
            push_fn(worktree_dir, task, branch)
            print(f"⏳ [Stream {worker_id}] Pushed update to {pr_url}. Waiting for CI checks...")
        except Exception as e:
            print(f"⚠️ [Stream {worker_id}] Failed to push fix: {e}")
            continue

    return False
