"""Autonomous orchestrator loop for executing unblocked backlog tasks."""

import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from .agent_worker import (
    build_ci_repair_prompt,
    build_conflict_repair_prompt,
    run_agent_in_worktree,
)
from .ci_watcher import (
    CIPipelineError,
    close_pull_request,
    commit_and_push,
    create_pull_request,
    get_ci_failure_diagnostics,
    merge_local_branch,
    merge_pull_request,
    sync_branch_with_base,
    wait_for_ci_checks,
)
from .models import Task
from .queue import BacklogQueue, finalize_backlog_completion
from .worktree import (
    cleanup_worktree,
    create_worktree,
    enforce_backlog_isolation,
    run_git,
    run_preflight_checks,
)

MERGE_LOCK = threading.Lock()


class TaskExecutionResult:
    def __init__(self, task: Task, success: bool, message: str = ""):
        self.task = task
        self.success = success
        self.message = message


def sync_and_resolve_base_ref(
    worktree_dir: Path,
    task: Task,
    base_ref: str = "origin/main",
    skip_agent: bool = False,
) -> tuple[bool, str]:
    """Syncs worktree branch with base_ref and invokes agent to resolve conflicts if needed."""
    sync_ok, sync_msg = sync_branch_with_base(worktree_dir, base_ref=base_ref)
    if sync_ok:
        return True, sync_msg

    # Merge conflict occurred
    if skip_agent:
        run_git(["merge", "--abort"], cwd=worktree_dir)
        return False, f"Merge conflicts detected against {base_ref} (skip_agent=True): {sync_msg}"

    worker_id = f"worker-{task.id}"
    print(
        f"⚠️ [Stream {worker_id}] Merge conflicts detected when syncing with {base_ref}.\n"
        f"🤖 [Stream {worker_id}] Invoking agent in worktree to resolve merge conflicts..."
    )
    prompt = build_conflict_repair_prompt(task, sync_msg)
    agent_ok, agent_log = run_agent_in_worktree(worktree_dir, task, custom_prompt=prompt)
    if not agent_ok:
        run_git(["merge", "--abort"], cwd=worktree_dir)
        return False, f"Agent failed to resolve merge conflicts: {agent_log}"

    # Check if any unresolved conflict markers remain
    status_res = run_git(["status", "--porcelain"], cwd=worktree_dir)
    unmerged = [
        line[3:].strip()
        for line in status_res.stdout.splitlines()
        if any(line.startswith(p) for p in ("UU", "AA", "DD", "DU", "UD"))
    ]
    if unmerged:
        run_git(["merge", "--abort"], cwd=worktree_dir)
        return False, f"Unmerged conflict files remained after agent repair: {', '.join(unmerged)}"

    # Enforce backlog isolation before committing merge resolution
    enforce_backlog_isolation(worktree_dir)

    # Stage all resolved files and commit the merge
    run_git(["add", "-A"], cwd=worktree_dir)
    commit_res = run_git(
        ["commit", "-m", f"chore: resolve merge conflicts with {base_ref}"],
        cwd=worktree_dir,
    )
    if commit_res.returncode != 0:
        merge_head = run_git(["rev-parse", "-q", "--verify", "MERGE_HEAD"], cwd=worktree_dir)
        if merge_head.returncode == 0:
            run_git(["merge", "--abort"], cwd=worktree_dir)
            return False, f"Failed to commit merge resolution: {commit_res.stderr.strip()}"

    print(f"✅ [Stream {worker_id}] Merge conflicts with {base_ref} successfully resolved.")
    return True, "Merge conflicts resolved."


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
    ci_repair_attempt = 0

    while ci_repair_attempt <= max_ci_repairs:
        ci_ok = wait_for_ci_checks(worktree_dir, pr_url)
        if ci_ok:
            return True

        ci_repair_attempt += 1
        if ci_repair_attempt > max_ci_repairs or skip_agent:
            break

        category, failure_details = get_ci_failure_diagnostics(worktree_dir, pr_url)
        print(
            f"\n⚠️ [Stream {worker_id}] CI check failure or conflict detected on PR (repair attempt {ci_repair_attempt}/{max_ci_repairs}):\n"
            f"Category: {category}\n{failure_details}\n"
        )

        # 1. Sync with latest origin/main
        print(f"🔄 [Stream {worker_id}] Syncing branch with latest origin/main...")
        sync_ok, sync_msg = sync_and_resolve_base_ref(
            worktree_dir, task, base_ref="origin/main", skip_agent=skip_agent
        )
        if not sync_ok:
            print(f"⚠️ [Stream {worker_id}] Merge conflict resolution failed: {sync_msg}")

        # 2. If CI checks failed, invoke agent to repair the failure
        if category == "ci_failed" or not sync_ok:
            print(f"🤖 [Stream {worker_id}] Invoking agent to repair CI failure...")
            ci_prompt = build_ci_repair_prompt(task, pr_url, failure_details)
            agent_ok, agent_log = run_agent_in_worktree(worktree_dir, task, custom_prompt=ci_prompt)
            if not agent_ok:
                print(f"⚠️ [Stream {worker_id}] Agent repair attempt failed: {agent_log}")
                continue

        # 3. Re-run pre-flight verification locally
        print(f"🔍 [Stream {worker_id}] Running pre-flight verification after CI repair...")
        preflight_ok, preflight_log = run_preflight_checks(worktree_dir)
        if not preflight_ok:
            print(f"⚠️ [Stream {worker_id}] Pre-flight verification failed, running repair loop...")
            agent_ok, agent_log = run_agent_in_worktree(worktree_dir, task, feedback=preflight_log)
            preflight_ok, preflight_log = run_preflight_checks(worktree_dir)
            if not preflight_ok:
                print(f"⚠️ [Stream {worker_id}] Pre-flight verification still failing.")
                continue

        # 4. Commit and push the fix to remote to update the PR!
        print(f"🌐 [Stream {worker_id}] Pushing CI fixes to origin/{branch}...")
        try:
            commit_and_push(worktree_dir, task, branch)
            print(f"⏳ [Stream {worker_id}] Pushed update to {pr_url}. Waiting for CI checks...")
        except Exception as e:
            print(f"⚠️ [Stream {worker_id}] Failed to push fix: {e}")
            continue

    return False


def execute_task_pipeline(
    task: Task,
    repo_root: Path,
    queue: BacklogQueue,
    local_mode: bool = False,
    skip_agent: bool = False,
) -> TaskExecutionResult:
    """Executes a single task through the full delivery lifecycle."""
    worker_id = f"worker-{task.id}"
    branch = f"feat/{task.slug}"
    worktree_name = f"task-{task.id}"

    print(f"\n🚀 [Stream {worker_id}] Starting pipeline for {task.canonical_id}: '{task.title}'")

    # 1. Claim task
    queue.claim_task(task, worker_id=worker_id, branch=branch)

    worktree_dir = None
    completed = False
    try:
        # 2. Create worktree
        worktree_dir = create_worktree(repo_root, branch, worktree_name)
        print(f"📁 [Stream {worker_id}] Worktree ready at: {worktree_dir}")

        # 3. Invoke implementation agent (unless skip_agent flag set for testing)
        if not skip_agent:
            print(f"🤖 [Stream {worker_id}] Invoking agent in worktree...")
            agent_ok, agent_log = run_agent_in_worktree(worktree_dir, task)
            if not agent_ok:
                return TaskExecutionResult(task, False, f"Agent execution failed: {agent_log}")

        # 3.5 Back-merge latest base branch before pre-flight and PR creation
        base_ref = "main" if local_mode else "origin/main"
        print(f"🔄 [Stream {worker_id}] Syncing branch with latest {base_ref} before pre-flight...")
        sync_ok, sync_msg = sync_and_resolve_base_ref(
            worktree_dir,
            task,
            base_ref=base_ref,
            skip_agent=skip_agent,
        )
        if not sync_ok:
            return TaskExecutionResult(
                task,
                False,
                f"Failed to synchronize with {base_ref}: {sync_msg}",
            )

        # 4. Pre-flight verification with agent repair loop
        print(f"🔍 [Stream {worker_id}] Running pre-flight verification...")
        preflight_ok, preflight_log = run_preflight_checks(worktree_dir)

        repair_attempt = 0
        max_repair_attempts = 3
        while not preflight_ok and repair_attempt < max_repair_attempts and not skip_agent:
            repair_attempt += 1
            print(
                f"⚠️ [Stream {worker_id}] Pre-flight verification failed (attempt {repair_attempt}/{max_repair_attempts}):\n"
                f"{preflight_log}"
            )
            print(
                f"🤖 [Stream {worker_id}] Invoking agent in worktree to diagnose and repair pre-flight issues..."
            )
            agent_ok, agent_log = run_agent_in_worktree(worktree_dir, task, feedback=preflight_log)
            if not agent_ok:
                return TaskExecutionResult(
                    task, False, f"Agent repair attempt {repair_attempt} failed: {agent_log}"
                )

            print(
                f"🔍 [Stream {worker_id}] Re-running pre-flight verification after repair attempt {repair_attempt}..."
            )
            preflight_ok, preflight_log = run_preflight_checks(worktree_dir)

        if not preflight_ok:
            return TaskExecutionResult(
                task,
                False,
                f"Pre-flight checks failed after {repair_attempt} repair attempt(s):\n{preflight_log}",
            )
        print(f"✅ [Stream {worker_id}] Pre-flight verification passed.")

        # 5. Delivery & Integration Gate
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
                    print(f"⚠️ [Stream {worker_id}] Late merge conflicts in push: {e}. Resolving...")
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
                close_pull_request(
                    worktree_dir,
                    pr_url,
                    reason=f"Task {task.canonical_id} failed CI checks or encountered merge conflicts. Releasing back to ready queue.",
                )
                return TaskExecutionResult(
                    task, False, f"CI checks failed or PR conflicted for {pr_url}"
                )

            with MERGE_LOCK:
                print(f"🔀 [Stream {worker_id}] Merging PR {pr_url} into main...")
                merge_pull_request(worktree_dir, pr_url)

                print(f"📥 [Stream {worker_id}] Pulling latest main into repository root...")
                run_git(["fetch", "origin", "main"], cwd=repo_root)
                pull_res = run_git(["pull", "--ff-only", "origin", "main"], cwd=repo_root)
                if pull_res.returncode != 0:
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
        # If task was not completed successfully, release it back to the ready queue!
        if not completed:
            print(f"🔄 [Stream {worker_id}] Releasing {task.canonical_id} back to ready queue...")
            queue.release_task(task)

        # 7. Cleanup worktree
        if worktree_dir:
            print(f"🧹 [Stream {worker_id}] Cleaning up worktree {worktree_name}...")
            cleanup_worktree(
                repo_root,
                worktree_dir,
                branch_name=branch,
                delete_branch=local_mode,
            )


def run_orchestrator(
    repo_root: Path,
    drain: bool = False,
    concurrency: int = 1,
    local_mode: bool = False,
    dry_run: bool = False,
    poll_idle_seconds: int = 5,
) -> int:
    """Main orchestration entrypoint driving autonomous backlog execution."""
    backlog_dir = repo_root / "docs" / "project" / "backlog"
    queue = BacklogQueue(backlog_dir)

    print("=== Runefoble Autonomous Backlog Engine ===")
    print(f"Repository Root: {repo_root}")
    print(f"Concurrency: {concurrency} stream(s)")
    print(f"Mode: {'Dry-run' if dry_run else ('Local Merge' if local_mode else 'GitHub PR + CI')}")
    print(f"Drain Queue: {drain}\n")

    # 0. Recover any stale in-progress tasks from interrupted previous runs
    stale_tasks = queue.recover_stale_tasks()
    if stale_tasks:
        print(f"🔄 Recovered {len(stale_tasks)} stale in-progress task(s) from previous run:")
        for st in stale_tasks:
            print(f"  - [{st.canonical_id}] {st.title}")
        print()

    completed_count = 0
    failed_attempts: dict[str, int] = {}

    try:
        while True:
            ready_tasks = queue.get_ready_unblocked_tasks()
            active_ready_tasks = [t for t in ready_tasks if failed_attempts.get(t.id, 0) < 3]

            if not active_ready_tasks:
                if ready_tasks:
                    print(
                        f"⚠️ All {len(ready_tasks)} ready unblocked task(s) exceeded maximum retry limits (3). Stopping orchestrator."
                    )
                    break
                else:
                    print("💤 No ready unblocked tasks found in queue.")
                if not drain:
                    break
                time.sleep(poll_idle_seconds)
                continue

            print(f"📋 Found {len(active_ready_tasks)} ready unblocked task(s):")
            for t in active_ready_tasks:
                print(f"  - [{t.canonical_id}] {t.title} (Priority: {t.priority_rank})")

            if dry_run:
                print("\nDry-run complete. Exiting without execution.")
                return 0

            # Batch up to concurrency tasks
            batch = active_ready_tasks[:concurrency]

            if len(batch) == 1 or concurrency == 1:
                task = batch[0]
                try:
                    res = execute_task_pipeline(task, repo_root, queue, local_mode=local_mode)
                    if res.success:
                        completed_count += 1
                        failed_attempts.pop(task.id, None)
                    else:
                        failed_attempts[task.id] = failed_attempts.get(task.id, 0) + 1
                        print(
                            f"❌ Pipeline failed for {task.canonical_id} (attempt {failed_attempts[task.id]}/3): {res.message}"
                        )
                except KeyboardInterrupt:
                    print(f"\n🛑 Interrupted while executing {task.canonical_id}.")
                    queue.release_task(task)
                    raise
            else:
                print(f"\n⚡ Dispatching {len(batch)} parallel task streams...")
                with ThreadPoolExecutor(max_workers=concurrency) as executor:
                    futures = {
                        executor.submit(
                            execute_task_pipeline,
                            task,
                            repo_root,
                            queue,
                            local_mode,
                        ): task
                        for task in batch
                    }
                    try:
                        for fut in as_completed(futures):
                            res = fut.result()
                            if res.success:
                                completed_count += 1
                                failed_attempts.pop(res.task.id, None)
                            else:
                                failed_attempts[res.task.id] = (
                                    failed_attempts.get(res.task.id, 0) + 1
                                )
                                print(
                                    f"❌ Stream failed for {res.task.canonical_id} (attempt {failed_attempts[res.task.id]}/3): {res.message}"
                                )
                    except KeyboardInterrupt:
                        print("\n🛑 Cancelling pending parallel worker streams...")
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
        print(
            "\n🛑 Orchestrator stopped by user (Ctrl+C). All active tasks released back to ready queue."
        )
        return 130
