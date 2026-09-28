"""Command line entrypoint for the autonomous backlog execution engine."""

import argparse
import sys
from pathlib import Path

from .models import Task
from .orchestrator import run_orchestrator
from .queue import BacklogQueue, finalize_backlog_completion


def _find_task(queue: BacklogQueue, raw_id: str) -> Task | None:
    """Finds a task by ID or canonical ID."""
    clean = raw_id.upper().replace("TASK-", "").strip().lstrip("0")
    for task in queue.list_all_tasks():
        task_clean = task.id.upper().replace("TASK-", "").strip().lstrip("0")
        if task_clean == clean or task.canonical_id == raw_id.upper():
            return task
    return None


def cmd_list(queue: BacklogQueue, show_all: bool = False) -> int:
    """Lists unblocked ready tasks or all tasks."""
    if show_all:
        tasks = queue.list_all_tasks()
        print(f"📋 All Backlog Tasks ({len(tasks)} found):")
    else:
        tasks = queue.get_ready_unblocked_tasks()
        print(f"📋 Ready Unblocked Tasks ({len(tasks)} found):")

    for task in tasks:
        claimed = f" [Claimed by: {task.claimed_by}]" if task.claimed_by else ""
        print(f"  - {task.canonical_id} [{task.status.value}] {task.title}{claimed}")
    return 0


def cmd_status(queue: BacklogQueue) -> int:
    """Displays task counts grouped by lifecycle status."""
    all_tasks = queue.list_all_tasks()
    ready = queue.get_ready_unblocked_tasks()
    status_counts: dict[str, int] = {}
    for t in all_tasks:
        status_counts[t.status.value] = status_counts.get(t.status.value, 0) + 1

    print("📊 Backlog Engine Status:")
    print(f"  Total tasks:           {len(all_tasks)}")
    print(f"  Ready (unblocked):     {len(ready)}")
    for status, count in sorted(status_counts.items()):
        print(f"  {status.capitalize():<22} {count}")
    return 0


def cmd_claim(queue: BacklogQueue, raw_id: str, worker_id: str, branch: str | None) -> int:
    """Claims a task for execution."""
    task = _find_task(queue, raw_id)
    if not task:
        print(f"❌ Error: Task {raw_id} not found in backlog.")
        return 1

    target_branch = branch or f"feat/{task.canonical_id.lower()}"
    queue.claim_task(task, worker_id=worker_id, branch=target_branch)
    print(f"✅ Claimed {task.canonical_id} for worker '{worker_id}' on branch '{target_branch}'.")
    return 0


def cmd_complete(repo_dir: Path, queue: BacklogQueue, raw_id: str, push: bool, no_git: bool) -> int:
    """Marks a task as complete and optionally updates git/PRIORITY.md."""
    task = _find_task(queue, raw_id)
    if not task:
        print(f"❌ Error: Task {raw_id} not found in backlog.")
        return 1

    if no_git:
        dest_file = queue.complete_task(task)
    else:
        dest_file = finalize_backlog_completion(repo_dir, queue, task, push=push)

    print(f"✅ Completed {task.canonical_id} -> {dest_file.name}")
    return 0


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Autonomous Backlog Execution Engine")
    parser.add_argument(
        "--drain",
        dest="drain",
        action="store_true",
        default=True,
        help="Continuously drain the queue until no unblocked ready tasks remain (default: True)",
    )
    parser.add_argument(
        "--once",
        dest="drain",
        action="store_false",
        help="Execute only a single batch/pass of tasks without draining",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=1,
        help="Number of concurrent worker streams (default: 1)",
    )
    parser.add_argument(
        "--local",
        action="store_true",
        help="Use local git merge instead of opening and watching GitHub PRs",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Inspect queue and list next unblocked ready tasks without executing",
    )
    parser.add_argument(
        "--repo-dir",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="Repository root directory",
    )

    subparsers = parser.add_subparsers(dest="command")

    list_p = subparsers.add_parser("list", help="List ready unblocked or all tasks")
    list_p.add_argument("--all", action="store_true", help="List all tasks across all statuses")
    list_p.add_argument("--repo-dir", type=Path, default=None)

    status_p = subparsers.add_parser("status", help="Show backlog status counts")
    status_p.add_argument("--repo-dir", type=Path, default=None)

    claim_p = subparsers.add_parser("claim", help="Claim a task for execution")
    claim_p.add_argument("task_id", help="Task ID (e.g. TASK-0002 or 0002)")
    claim_p.add_argument("--worker-id", default="manual-worker", help="Worker identifier")
    claim_p.add_argument("--branch", default=None, help="Feature branch name")
    claim_p.add_argument("--repo-dir", type=Path, default=None)

    complete_p = subparsers.add_parser("complete", help="Mark a task complete")
    complete_p.add_argument("task_id", help="Task ID (e.g. TASK-0002 or 0002)")
    complete_p.add_argument(
        "--push", action="store_true", default=False, help="Push completion to origin"
    )
    complete_p.add_argument(
        "--no-git", action="store_true", default=False, help="Only update markdown files"
    )
    complete_p.add_argument("--repo-dir", type=Path, default=None)

    args = parser.parse_args(argv)
    repo_dir = (
        getattr(args, "repo_dir", None)
        if getattr(args, "repo_dir", None) is not None
        else Path(__file__).resolve().parents[2]
    )
    backlog_dir = repo_dir / "docs" / "project" / "backlog"

    if args.command == "list":
        queue = BacklogQueue(backlog_dir)
        sys.exit(cmd_list(queue, show_all=args.all))
    elif args.command == "status":
        queue = BacklogQueue(backlog_dir)
        sys.exit(cmd_status(queue))
    elif args.command == "claim":
        queue = BacklogQueue(backlog_dir)
        sys.exit(cmd_claim(queue, args.task_id, args.worker_id, args.branch))
    elif args.command == "complete":
        queue = BacklogQueue(backlog_dir)
        sys.exit(cmd_complete(repo_dir, queue, args.task_id, args.push, args.no_git))
    else:
        exit_code = run_orchestrator(
            repo_root=repo_dir,
            drain=args.drain,
            concurrency=args.concurrency,
            local_mode=args.local,
            dry_run=args.dry_run,
        )
        sys.exit(exit_code)


if __name__ == "__main__":
    main()
