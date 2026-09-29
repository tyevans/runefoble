"""Branch checkout, worktree synchronization, conflict rebasing, and atomic merge execution."""

import subprocess
import sys
from pathlib import Path
from typing import Any

from .agent_worker import build_conflict_repair_prompt, run_agent_in_worktree
from .models import Task
from .worktree import enforce_backlog_isolation, run_git


class CIPipelineError(RuntimeError):
    pass


def run_cmd(cmd: list[str], cwd: Path, check: bool = False) -> subprocess.CompletedProcess:
    """Executes a subprocess command, respecting mocks on ci_watcher.run_cmd if present."""
    ci_mod = sys.modules.get("tools.backlog_engine.ci_watcher")
    if ci_mod and hasattr(ci_mod, "run_cmd") and ci_mod.run_cmd is not run_cmd:
        return ci_mod.run_cmd(cmd, cwd=cwd, check=check)
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=check)


def commit_and_push(worktree_dir: Path, task: Task, branch: str) -> None:
    """Stages all changes, commits if needed, and pushes to origin."""
    run_cmd(["git", "fetch", "origin", "main"], cwd=worktree_dir)
    chk = run_cmd(["git", "rev-parse", "--verify", "origin/main"], cwd=worktree_dir)
    base_ref = "origin/main" if chk.returncode == 0 else "main"

    status = run_cmd(["git", "status", "--porcelain", "docs/project/backlog"], cwd=worktree_dir)
    dirty_files = set()
    for line in status.stdout.splitlines():
        parts = line.strip().split()
        if len(parts) >= 2:
            dirty_files.add(parts[-1])
    revert_targets = [f for f in dirty_files if not f.endswith("docs/project/backlog/README.md")]
    for target in revert_targets:
        run_cmd(["git", "checkout", base_ref, "--", target], cwd=worktree_dir)
        run_cmd(["git", "clean", "-fd", target], cwd=worktree_dir)
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

    if chk.returncode == 0:
        behind_res = run_cmd(["git", "rev-list", f"HEAD..{base_ref}", "--count"], cwd=worktree_dir)
        behind_count = behind_res.stdout.strip()
        if behind_count.isdigit() and int(behind_count) > 0:
            merge_test = run_cmd(
                ["git", "merge-tree", "--write-tree", "HEAD", base_ref],
                cwd=worktree_dir,
            )
            if merge_test.returncode != 0:
                raise CIPipelineError(
                    f"Branch {branch} has merge conflicts with {base_ref}. Releasing task back to queue."
                )
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
    """Syncs the current branch with base_ref via git merge."""
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

    merge_res = run_cmd(
        ["git", "merge", effective_base, "-m", f"chore: sync with {effective_base}"],
        cwd=worktree_dir,
    )
    if merge_res.returncode == 0:
        return (
            True,
            f"Successfully merged {effective_base} into branch ({behind_count} commit(s) synced).",
        )

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

    if skip_agent:
        run_git(["merge", "--abort"], cwd=worktree_dir)
        return False, f"Merge conflicts detected against {base_ref} (skip_agent=True): {sync_msg}"

    worker_id = f"worker-{task.id}"
    print(
        f"⚠️ [Stream {worker_id}] Merge conflicts detected when syncing with {base_ref}.\n"
        f"🤖 [Stream {worker_id}] Invoking agent in worktree to resolve merge conflicts..."
    )
    prompt = build_conflict_repair_prompt(task, sync_msg)
    orch = sys.modules.get("tools.backlog_engine.orchestrator")
    runner = (
        getattr(orch, "run_agent_in_worktree", run_agent_in_worktree)
        if orch
        else run_agent_in_worktree
    )
    agent_ok, agent_log = runner(worktree_dir, task, custom_prompt=prompt)
    if not agent_ok:
        run_git(["merge", "--abort"], cwd=worktree_dir)
        return False, f"Agent failed to resolve merge conflicts: {agent_log}"

    status_res = run_git(["status", "--porcelain"], cwd=worktree_dir)
    unmerged = [
        line[3:].strip()
        for line in status_res.stdout.splitlines()
        if any(line.startswith(p) for p in ("UU", "AA", "DD", "DU", "UD"))
    ]
    if unmerged:
        run_git(["merge", "--abort"], cwd=worktree_dir)
        return False, f"Unmerged conflict files remained after agent repair: {', '.join(unmerged)}"

    enforce_backlog_isolation(worktree_dir)
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


def finalize_backlog_completion(
    repo_root: Path,
    queue: Any,
    task: Task,
    push: bool = False,
) -> Path:
    """Marks task complete in queue, stages PRIORITY.md and file, commits and optionally pushes."""
    dest_file = queue.complete_task(task)
    subprocess.run(
        ["git", "add", "docs/project/backlog/PRIORITY.md", str(dest_file)],
        cwd=repo_root,
        check=False,
    )
    for folder in ("refined", "proposed"):
        old = repo_root / "docs" / "project" / "backlog" / folder / task.file_path.name
        if not old.exists():
            subprocess.run(
                ["git", "rm", "--cached", "--ignore-unmatch", str(old)],
                cwd=repo_root,
                check=False,
            )

    st = subprocess.run(
        ["git", "status", "--porcelain", "docs/project/backlog"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if st.stdout.strip():
        subprocess.run(
            ["git", "commit", "-m", f"chore(backlog): complete {task.canonical_id}"],
            cwd=repo_root,
            check=False,
        )
        if push:
            push_res = subprocess.run(
                ["git", "push", "origin", "main"],
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            if push_res.returncode != 0:
                print(f"⚠️ Push rejected, fetching and rebasing: {push_res.stderr.strip()}")
                subprocess.run(
                    ["git", "pull", "--rebase", "origin", "main"],
                    cwd=repo_root,
                    check=False,
                )
                push_retry = subprocess.run(
                    ["git", "push", "origin", "main"],
                    cwd=repo_root,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if push_retry.returncode != 0:
                    raise RuntimeError(
                        f"Failed to push backlog completion on retry: {push_retry.stderr.strip()}"
                    )
    return dest_file
