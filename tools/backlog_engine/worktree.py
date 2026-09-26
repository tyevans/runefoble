"""Git worktree lifecycle management and pre-flight verification."""

import subprocess
from pathlib import Path


class WorktreeError(RuntimeError):
    pass


def run_git(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    """Executes a git command in the target directory."""
    return subprocess.run(
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


def create_worktree(
    repo_root: Path,
    branch_name: str,
    worktree_name: str,
    base_ref: str = "main",
) -> Path:
    """Creates an isolated git worktree branch under .worktrees/."""
    worktrees_parent = repo_root / ".worktrees"
    worktrees_parent.mkdir(parents=True, exist_ok=True)
    worktree_path = worktrees_parent / worktree_name

    # Check if worktree or branch already exists
    if worktree_path.exists():
        # Clean up stale worktree
        run_git(["worktree", "remove", "--force", str(worktree_path)], cwd=repo_root)

    # Check if branch exists
    chk = run_git(["rev-parse", "--verify", branch_name], cwd=repo_root)
    if chk.returncode == 0:
        # Use existing branch
        res = run_git(
            ["worktree", "add", str(worktree_path), branch_name],
            cwd=repo_root,
        )
    else:
        # Create new branch from base_ref
        res = run_git(
            ["worktree", "add", "-b", branch_name, str(worktree_path), base_ref],
            cwd=repo_root,
        )

    if res.returncode != 0:
        raise WorktreeError(f"Failed to create worktree: {res.stderr.strip()}")

    return worktree_path


def cleanup_worktree(
    repo_root: Path,
    worktree_path: Path,
    branch_name: str | None = None,
    delete_branch: bool = False,
) -> None:
    """Removes a worktree and optionally deletes the associated branch."""
    if worktree_path.exists():
        run_git(["worktree", "remove", "--force", str(worktree_path)], cwd=repo_root)

    # Prune worktree records
    run_git(["worktree", "prune"], cwd=repo_root)

    if delete_branch and branch_name:
        run_git(["branch", "-D", branch_name], cwd=repo_root)


def run_preflight_checks(worktree_dir: Path) -> tuple[bool, str]:
    """Runs automated verification suite (ruff lint/format, pytest, health check) in the worktree."""
    checks = [
        ("Ruff Lint", ["uv", "run", "ruff", "check", "."]),
        ("Ruff Format", ["uv", "run", "ruff", "format", "--check", "."]),
        ("Pytest Suite", ["uv", "run", "pytest"]),
    ]

    health_check_script = worktree_dir / "scripts" / "health_check.py"
    if health_check_script.exists():
        checks.append(("Health Check", ["python3", str(health_check_script.resolve())]))

    output_log = []
    all_passed = True
    for name, cmd in checks:
        res = subprocess.run(
            cmd,
            cwd=worktree_dir,
            capture_output=True,
            text=True,
        )
        if res.returncode != 0:
            all_passed = False
            err_msg = (
                f"❌ Pre-flight check '{name}' failed (exit code {res.returncode}):\n"
                f"{res.stdout}\n{res.stderr}"
            )
            output_log.append(err_msg)
        else:
            output_log.append(f"✅ {name} passed.")

    return all_passed, "\n".join(output_log)
