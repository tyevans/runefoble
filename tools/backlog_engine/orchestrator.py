"""Autonomous orchestrator loop for executing unblocked backlog tasks."""

import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from .agent_worker import run_agent_in_worktree
from .ci_watcher import (
    CIPipelineError,
    close_pull_request,
    get_ci_failure_diagnostics,
    wait_for_ci_checks,
    watch_and_repair_pull_request,
)
from .git_ops import commit_and_push, merge_local_branch, sync_and_resolve_base_ref
from .github_client import create_pull_request, merge_pull_request
from .models import Task
from .queue import BacklogQueue, finalize_backlog_completion
from .worktree import cleanup_worktree, create_worktree, run_git, run_preflight_checks

MERGE_LOCK = threading.Lock()

__all__ = [
    "MERGE_LOCK",
    "TaskExecutionResult",
    "execute_task_pipeline",
    "get_ci_failure_diagnostics",
    "run_orchestrator",
    "wait_for_ci_checks",
]


class TaskExecutionResult:
    def __init__(self, task: Task, success: bool, message: str = ""):
        self.task, self.success, self.message = task, success, message


def execute_task_pipeline(
    task: Task,
    repo_root: Path,
    queue: BacklogQueue,
    local_mode: bool = False,
    skip_agent: bool = False,
) -> TaskExecutionResult:
    """Executes a single task through the full delivery lifecycle."""
    worker_id, branch, worktree_name = f"worker-{task.id}", f"feat/{task.slug}", f"task-{task.id}"
    print(f"\n🚀 [Stream {worker_id}] Starting pipeline for {task.canonical_id}: '{task.title}'")
    queue.claim_task(task, worker_id=worker_id, branch=branch)

    worktree_dir, completed = None, False
    try:
        worktree_dir = create_worktree(repo_root, branch, worktree_name)
        print(f"📁 [Stream {worker_id}] Worktree ready at: {worktree_dir}")

        if not skip_agent:
            print(f"🤖 [Stream {worker_id}] Invoking agent in worktree...")
            agent_ok, agent_log = run_agent_in_worktree(worktree_dir, task)
            if not agent_ok:
                return TaskExecutionResult(task, False, f"Agent execution failed: {agent_log}")

        base_ref = "main" if local_mode else "origin/main"
        print(f"🔄 [Stream {worker_id}] Syncing branch with latest {base_ref} before pre-flight...")
        sync_ok, sync_msg = sync_and_resolve_base_ref(
            worktree_dir, task, base_ref=base_ref, skip_agent=skip_agent
        )
        if not sync_ok:
            return TaskExecutionResult(
                task, False, f"Failed to synchronize with {base_ref}: {sync_msg}"
            )

        print(f"🔍 [Stream {worker_id}] Running pre-flight verification...")
        preflight_ok, preflight_log = run_preflight_checks(worktree_dir)
        repair_attempt = 0
        while not preflight_ok and repair_attempt < 3 and not skip_agent:
            repair_attempt += 1
            print(
                f"⚠️ [Stream {worker_id}] Pre-flight failed (attempt {repair_attempt}/3):\n{preflight_log}"
            )
            agent_ok, agent_log = run_agent_in_worktree(worktree_dir, task, feedback=preflight_log)
            if not agent_ok:
                return TaskExecutionResult(
                    task, False, f"Agent repair attempt {repair_attempt} failed: {agent_log}"
                )
            preflight_ok, preflight_log = run_preflight_checks(worktree_dir)

        if not preflight_ok:
            return TaskExecutionResult(
                task,
                False,
                f"Pre-flight checks failed after {repair_attempt} repair attempt(s):\n{preflight_log}",
            )
        print(f"✅ [Stream {worker_id}] Pre-flight verification passed.")

        if local_mode:
            with MERGE_LOCK:
                print(f"🏠 [Stream {worker_id}] Running in local merge mode...")
                merge_local_branch(repo_root, branch, task)
                finalize_backlog_completion(repo_root, queue, task, push=False)
                completed = True
                print(f"🎉 [Stream {worker_id}] {task.canonical_id} completed and merged locally")
        else:
            print(f"🌐 [Stream {worker_id}] Committing and pushing to origin...")
            try:
                commit_and_push(worktree_dir, task, branch)
            except CIPipelineError as e:
                if "merge conflicts" in str(e).lower() and not skip_agent:
                    sync_ok, sync_msg = sync_and_resolve_base_ref(
                        worktree_dir, task, base_ref="origin/main", skip_agent=skip_agent
                    )
                    if not sync_ok:
                        raise
                    commit_and_push(worktree_dir, task, branch)
                else:
                    raise

            pr_url = create_pull_request(worktree_dir, task, branch)
            queue.mark_review(task, pr_url)
            print(f"📋 [Stream {worker_id}] Pull Request created: {pr_url}")

            ci_ok = watch_and_repair_pull_request(
                worktree_dir, task, branch, pr_url, worker_id, skip_agent=skip_agent
            )
            if not ci_ok:
                reason = (
                    f"Task {task.canonical_id} failed CI or conflicted. Releasing back to queue."
                )
                close_pull_request(worktree_dir, pr_url, reason=reason)
                return TaskExecutionResult(
                    task, False, f"CI checks failed or PR conflicted for {pr_url}"
                )

            with MERGE_LOCK:
                print(f"🔀 [Stream {worker_id}] Merging PR {pr_url} into main...")
                merge_pull_request(worktree_dir, pr_url)
                print(f"📥 [Stream {worker_id}] Pulling latest main into repository root...")
                run_git(["fetch", "origin", "main"], cwd=repo_root)
                if run_git(["pull", "--ff-only", "origin", "main"], cwd=repo_root).returncode != 0:
                    run_git(["reset", "--hard", "origin/main"], cwd=repo_root)

                finalize_backlog_completion(repo_root, queue, task, push=True)
                completed = True
                print(f"🎉 [Stream {worker_id}] {task.canonical_id} completed and pushed to main")

        return TaskExecutionResult(task, True, "Task completed and integrated successfully.")
    except (KeyboardInterrupt, SystemExit):
        print(f"\n⚠️ [Stream {worker_id}] Execution interrupted by user for {task.canonical_id}.")
        raise
    except Exception as e:
        return TaskExecutionResult(task, False, f"Unhandled pipeline exception: {e}")
    finally:
        if not completed:
            print(f"🔄 [Stream {worker_id}] Releasing {task.canonical_id} back to ready queue...")
            queue.release_task(task)
        if worktree_dir:
            print(f"🧹 [Stream {worker_id}] Cleaning up worktree {worktree_name}...")
            cleanup_worktree(repo_root, worktree_dir, branch_name=branch, delete_branch=local_mode)


def run_orchestrator(
    repo_root: Path,
    drain: bool = False,
    concurrency: int = 1,
    local_mode: bool = False,
    dry_run: bool = False,
    poll_idle_seconds: int = 5,
) -> int:
    """Main orchestration entrypoint driving autonomous backlog execution."""
    queue = BacklogQueue(repo_root / "docs" / "project" / "backlog")
    print(
        f"=== Runefoble Backlog Engine ===\nRoot: {repo_root}\nConcurrency: {concurrency} stream(s)\n"
    )

    stale_tasks = queue.recover_stale_tasks()
    if stale_tasks:
        print(f"🔄 Recovered {len(stale_tasks)} stale in-progress task(s) from previous run")

    completed_count, failed_attempts = 0, {}
    try:
        while True:
            ready_tasks = queue.get_ready_unblocked_tasks()
            active_ready_tasks = [t for t in ready_tasks if failed_attempts.get(t.id, 0) < 3]

            if not active_ready_tasks:
                if ready_tasks:
                    print("⚠️ All ready tasks exceeded retry limits (3). Stopping.")
                    break
                print("💤 No ready unblocked tasks found in queue.")
                if not drain:
                    break
                time.sleep(poll_idle_seconds)
                continue

            if dry_run:
                return 0

            batch = active_ready_tasks[:concurrency]
            with ThreadPoolExecutor(max_workers=concurrency) as executor:
                futures = {
                    executor.submit(execute_task_pipeline, t, repo_root, queue, local_mode): t
                    for t in batch
                }
                try:
                    for fut in as_completed(futures):
                        res = fut.result()
                        if res.success:
                            completed_count += 1
                            failed_attempts.pop(res.task.id, None)
                        else:
                            failed_attempts[res.task.id] = failed_attempts.get(res.task.id, 0) + 1
                except KeyboardInterrupt:
                    executor.shutdown(wait=False, cancel_futures=True)
                    for t in batch:
                        queue.release_task(t)
                    raise

            if not drain:
                break

        print(f"\n=== Orchestrator Finished: {completed_count} task(s) delivered ===")
        return 0
    except KeyboardInterrupt:
        queue.recover_stale_tasks()
        print("\n🛑 Orchestrator stopped by user (Ctrl+C).")
        return 130
