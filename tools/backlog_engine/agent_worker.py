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


def run_agent_in_worktree(
    worktree_dir: Path,
    task: Task,
    feedback: str | None = None,
    timeout_seconds: int = 1800,
) -> tuple[bool, str]:
    """Invokes agy CLI non-interactively within the worktree directory.

    If feedback is provided, sends a repair prompt continuing the session.
    """
    if feedback:
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
