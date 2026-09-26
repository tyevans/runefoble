"""Autonomous orchestrator loop for executing unblocked backlog tasks."""

import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from .agent_worker import run_agent_in_worktree
from .ci_watcher import (
    close_pull_request,
    commit_and_push,
    create_pull_request,
    merge_local_branch,
    merge_pull_request,
    wait_for_ci_checks,
)
from .models import Task
from .queue import BacklogQueue
from .worktree import cleanup_worktree, create_worktree, run_git, run_preflight_checks

MERGE_LOCK = threading.Lock()


class TaskExecutionResult:
    def __init__(self, task: Task, success: bool, message: str = ""):
        self.task = task
        self.success = success
        self.message = message


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

                dest_file = queue.complete_task(task)

                # Stage and commit the backlog completion locally
                run_git(["add", "docs/project/backlog/PRIORITY.md", str(dest_file)], cwd=repo_root)
                for folder in ["refined", "proposed"]:
                    old_candidate = (
                        repo_root / "docs" / "project" / "backlog" / folder / task.file_path.name
                    )
                    if not old_candidate.exists():
                        run_git(
                            ["rm", "--cached", "--ignore-unmatch", str(old_candidate)],
                            cwd=repo_root,
                        )

                status = run_git(["status", "--porcelain", "docs/project/backlog"], cwd=repo_root)
                if status.stdout.strip():
                    run_git(
                        ["commit", "-m", f"chore(backlog): complete {task.canonical_id}"],
                        cwd=repo_root,
                    )
                completed = True
                print(f"🎉 [Stream {worker_id}] {task.canonical_id} completed and merged locally")
        else:
            print(f"🌐 [Stream {worker_id}] Committing and pushing to origin...")
            commit_and_push(worktree_dir, task, branch)

            pr_url = create_pull_request(worktree_dir, task, branch)
            queue.mark_review(task, pr_url)
            print(f"📋 [Stream {worker_id}] Pull Request created: {pr_url}")

            ci_ok = wait_for_ci_checks(worktree_dir, pr_url)
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
                pull_res = run_git(["pull", "--ff-only", "origin", "main"], cwd=repo_root)
                if pull_res.returncode != 0:
                    run_git(["fetch", "origin", "main"], cwd=repo_root)
                    run_git(["reset", "--hard", "origin/main"], cwd=repo_root)

                # Finalize in Backlog Queue on repo_root
                dest_file = queue.complete_task(task)

                # Stage and commit the backlog completion to origin/main
                run_git(["add", "docs/project/backlog/PRIORITY.md", str(dest_file)], cwd=repo_root)
                for folder in ["refined", "proposed"]:
                    old_candidate = (
                        repo_root / "docs" / "project" / "backlog" / folder / task.file_path.name
                    )
                    if not old_candidate.exists():
                        run_git(
                            ["rm", "--cached", "--ignore-unmatch", str(old_candidate)],
                            cwd=repo_root,
                        )

                status = run_git(["status", "--porcelain", "docs/project/backlog"], cwd=repo_root)
                if status.stdout.strip():
                    run_git(
                        ["commit", "-m", f"chore(backlog): complete {task.canonical_id}"],
                        cwd=repo_root,
                    )
                    push_res = run_git(["push", "origin", "main"], cwd=repo_root)
                    if push_res.returncode != 0:
                        print(f"⚠️ Failed to push backlog completion: {push_res.stderr.strip()}")

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

    try:
        while True:
            ready_tasks = queue.get_ready_unblocked_tasks()

            if not ready_tasks:
                print("💤 No ready unblocked tasks found in queue.")
                if not drain:
                    break
                time.sleep(poll_idle_seconds)
                continue

            print(f"📋 Found {len(ready_tasks)} ready unblocked task(s):")
            for t in ready_tasks:
                print(f"  - [{t.canonical_id}] {t.title} (Priority: {t.priority_rank})")

            if dry_run:
                print("\nDry-run complete. Exiting without execution.")
                return 0

            # Batch up to concurrency tasks
            batch = ready_tasks[:concurrency]

            if len(batch) == 1 or concurrency == 1:
                task = batch[0]
                try:
                    res = execute_task_pipeline(task, repo_root, queue, local_mode=local_mode)
                    if res.success:
                        completed_count += 1
                    else:
                        print(f"❌ Pipeline failed for {task.canonical_id}: {res.message}")
                        break
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
                            else:
                                print(
                                    f"❌ Stream failed for {res.task.canonical_id}: {res.message}"
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
