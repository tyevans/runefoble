"""Worker interface to invoke Antigravity agy inside isolated worktrees."""

import subprocess
import time
from pathlib import Path

from .models import Task


class AgentWorkerError(RuntimeError):
    pass


def build_worker_prompt(task: Task) -> str:
    """Builds a comprehensive, invariant-enforcing prompt for the task worker."""
    prompt = f"""You are executing {task.canonical_id} in an isolated git worktree branch.

Task Title: {task.title}
Governing ADRs: {", ".join(task.governing_adrs) if task.governing_adrs else "None specified"}
Dependencies: {", ".join(task.dependencies) if task.dependencies else "None"}

Task Specification:
{task.body}

CRITICAL RULES & HARD INVARIANTS (From AGENTS.md):
1. Object-level authorization runs through SpiceDB Zanzibar schema (libs/runefoble_auth/schema/runefoble.zed). Never hardcode role checks.
2. Domain state transitions flow strictly through DeclarativeAggregate subclasses with @handles methods, saved/loaded via AggregateRepository.
3. Frontend UI components must be Lit Web Components in frontend/src/components/ with Storybook stories.
4. File length limit (<500 lines): Source files over ~450 lines must be decomposed.
5. Blackbox TDD with frontdoor setup: Drive all development through public entrypoints (HTTP routes, WebSockets, CloudEvents). Do NOT use backdoor internal manipulation.
6. Documentation integrity: Update docs/reference/ or docs/how-to/ if introducing new public APIs or generic patterns.
7. Verification: Run 'uv run ruff check .', 'uv run ruff format .', and 'uv run pytest' to ensure clean passing tests.
8. Backlog Isolation: DO NOT edit, rename, or move any files under docs/project/backlog/ (including PRIORITY.md, refined/, or complete/). Task completion and PRIORITY.md updates are handled exclusively by the integration orchestrator upon merge to main.

Implement the full feature, frontdoor blackbox tests, and any required documentation updates now.
"""
    return prompt.strip()


def build_repair_prompt(task: Task, preflight_log: str) -> str:
    """Builds a diagnostic and repair prompt when pre-flight checks fail."""
    prompt = f"""Pre-flight automated verification failed for {task.canonical_id}: '{task.title}'.

================ PRE-FLIGHT VERIFICATION LOG ================
{preflight_log.strip()}
=============================================================

Your task is to inspect the above failure(s), understand the problem, and fix it directly in the worktree.

Common failure types and how to resolve them:
1. 'Ruff Format' failed:
   Run `uv run ruff format .` to reformat all files, including Python code snippets in markdown files.
2. 'Ruff Lint' failed:
   Inspect the linter violations and fix them (or run `uv run ruff check --fix .` if safe).
3. 'Pytest Suite' failed:
   Examine the test traceback, identify the regression or broken assumption, and fix the code or test.
4. 'Health Check' failed:
   Inspect file length violations (>500 lines) and decompose oversized files into modular components.

Before reporting done, verify locally in the worktree by running:
  uv run ruff check .
  uv run ruff format --check .
  uv run pytest

Fix all failures now so that pre-flight verification passes.
"""
    return prompt.strip()


def build_ci_repair_prompt(task: Task, pr_url: str, ci_log: str) -> str:
    """Builds a diagnostic and repair prompt when GitHub Actions CI checks fail for a PR."""
    prompt = f"""Remote CI verification failed on GitHub Actions for {task.canonical_id}: '{task.title}'.
Pull Request: {pr_url}

================ GITHUB ACTIONS CI FAILURE LOG ================
{ci_log.strip()}
==============================================================

Your task is to inspect the above CI check failure(s), diagnose the root cause, and fix it directly in the worktree.

Common CI failure patterns and how to resolve them:
1. Linter / Formatter failures ('Ruff Lint', 'Ruff Format'):
   Run `uv run ruff format .` and `uv run ruff check --fix .`.
2. Test failures in CI ('Python Lint, Tests & Properties'):
   Inspect the test tracebacks above, identify why the test failed in the CI environment (e.g. environment assumptions, missing mocks, shallow git clone, or regressions), and fix the code or tests.
3. Frontend TypeScript or Build failures ('Frontend TypeScript, Build & Storybook'):
   Run `cd frontend && pnpm exec tsc --noEmit` and `cd frontend && pnpm run build` locally to diagnose and fix TypeScript and bundling errors.
4. Helm linting failures ('Helm Lint & Manifest Validation'):
   Run `helm lint deployments/helm/runefoble` and fix Helm chart syntax or template errors.

Before reporting done:
1. Verify locally in the worktree by running:
   uv run ruff check .
   uv run ruff format --check .
   uv run pytest
2. If frontend changes were made:
   cd frontend && pnpm run build
3. Do NOT edit files in docs/project/backlog/.

Fix all issues now so that when the branch is pushed, all GitHub CI checks will pass.
"""
    return prompt.strip()


def build_conflict_repair_prompt(task: Task, conflict_info: str) -> str:
    """Builds a repair prompt when git merge conflicts arise against the base branch."""
    prompt = f"""Merge conflicts were detected when synchronizing {task.canonical_id} with the latest base branch (origin/main).

================ MERGE CONFLICT STATUS & DETAILS ================
{conflict_info.strip()}
=================================================================

Your task is to resolve all merge conflicts in the worktree:
1. Inspect the conflicted files containing conflict markers (<<<<<<<, =======, >>>>>>>).
2. Resolve the conflicts by preserving ALL incoming changes from the base branch while retaining your implementation of {task.canonical_id}.
3. Remove all conflict markers.
4. Ensure the resulting code is syntactically valid and passes tests:
   uv run ruff check .
   uv run ruff format --check .
   uv run pytest
5. Stage the resolved files using `git add <file>`. Do not abort the merge.
6. Do NOT touch files in docs/project/backlog/.

Resolve the conflicts and verify the worktree now.
"""
    return prompt.strip()


def run_agent_in_worktree(
    worktree_dir: Path,
    task: Task,
    feedback: str | None = None,
    timeout_seconds: int = 1800,
    custom_prompt: str | None = None,
) -> tuple[bool, str]:
    """Invokes agy CLI non-interactively within the worktree directory.

    If custom_prompt or feedback is provided, sends a repair prompt continuing the session.
    """
    if custom_prompt:
        prompt = custom_prompt
        cmd = ["agy", "--dangerously-skip-permissions", "-c", "-p", prompt]
    elif feedback:
        prompt = build_repair_prompt(task, feedback)
        # Continue previous conversation session
        cmd = [
            "agy",
            "--dangerously-skip-permissions",
            "-c",
            "-p",
            prompt,
        ]
    else:
        prompt = build_worker_prompt(task)
        cmd = [
            "agy",
            "--dangerously-skip-permissions",
            "-p",
            prompt,
        ]

    start_time = time.time()
    proc = None
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=worktree_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        stdout, stderr = proc.communicate(timeout=timeout_seconds)
        elapsed = time.time() - start_time

        # If continuing failed, fallback to fresh prompt invocation
        if proc.returncode != 0 and feedback and "-c" in cmd:
            fallback_cmd = [
                "agy",
                "--dangerously-skip-permissions",
                "-p",
                prompt,
            ]
            fallback_proc = subprocess.Popen(
                fallback_cmd,
                cwd=worktree_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            fallback_stdout, fallback_stderr = fallback_proc.communicate(timeout=timeout_seconds)
            if fallback_proc.returncode == 0:
                elapsed = time.time() - start_time
                return (
                    True,
                    f"Agent repair completed successfully in {elapsed:.1f}s:\n{fallback_stdout}",
                )

        if proc.returncode != 0:
            err = (
                f"Agent run failed (code {proc.returncode}) after {elapsed:.1f}s:\n"
                f"{stdout}\n{stderr}"
            )
            return False, err

        output = f"Agent completed successfully in {elapsed:.1f}s:\n{stdout}"
        return True, output

    except KeyboardInterrupt:
        if proc and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        raise
    except subprocess.TimeoutExpired:
        if proc and proc.poll() is None:
            proc.kill()
        return (
            False,
            f"Agent timed out after {timeout_seconds} seconds in {worktree_dir}",
        )
    except Exception as e:
        return False, f"Failed to execute agent: {e}"
