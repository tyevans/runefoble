# How-To: Curate the Backlog and Align with the Roadmap

## Overview
Backlog curation in Runefoble uses lean Just-In-Time (JIT) refinement, continuous refactoring scanning, and roadmap dependency alignment. Rather than bulk-refining work far in advance, the team maintains a lean ready buffer of ~10 tasks in `docs/project/backlog/refined/`.

## Running the Health Check
Inspect the repository for file length invariant violations (<500 lines) and review buffer status:
```bash
make health-check
```
Or run the Python script directly:
```bash
python3 .agents/skills/backlog-curator/scripts/health_check.py
```

## Running the Backlog Curator
To run the automated triage, refactoring scan, and JIT refinement cycle:

### Method 1: Developer Runner Script
```bash
./scripts/curate-backlog.sh
```

### Method 2: Antigravity Interactive / Slash Command
Within an active `agy` or IDE session, ask the agent:
```text
Curate the backlog using the backlog-curator skill.
```
Or schedule it to run daily at 9:00 AM:
```text
/schedule 0 9 * * * Curate the backlog using the backlog-curator skill.
```

## How Curation Operates
1. **Health & Invariants**: Identifies files approaching or exceeding 500 lines per `AGENTS.md` Rule 6, filing refactoring proposals in `docs/project/backlog/proposed/`.
2. **Roadmap Alignment**: Reads `docs/project/backlog/ROADMAP.md` (e.g. Milestone 2: Live Collaborative Alpha) to ensure foundational architectural enablers precede dependent feature epics.
3. **JIT Refinement**: Checks `docs/project/backlog/refined/`. If the ready buffer falls below ~10 items, it refines the top proposed enabler/task against the Definition of Ready in `AGENTS.md`—including INVEST criteria (Independent, Negotiable, Valuable, Estimable, Small, Testable), bounded context isolation, microfrontend UI slice declaration (`services/<bc>/ui/`) per [ADR-0013](../project/adrs/accepted/adr-0013-microfrontend-architecture-and-service-component-vendoring.md), Storybook isolation planning, and a frontdoor blackbox TDD Definition of Done.
4. **PRIORITY Index Sync**: Reconciles `docs/project/backlog/PRIORITY.md` with filesystem state.

## Backlog Isolation and Conflict-Free Concurrent Execution

When multiple tasks are executed concurrently via `./scripts/run-backlog-engine.sh` (`make backlog-worker`):
1. **Feature Branch Backlog Isolation**: Worker agents running in git worktrees focus strictly on service code, microfrontend components, tests, and Diataxis guides. Feature branches must never modify `docs/project/backlog/` (including `PRIORITY.md`, `refined/`, or `complete/`).
2. **Merge Conflict Prevention**: Because adjacent items in `PRIORITY.md` are executed in parallel, having feature branches touch `PRIORITY.md` would cause guaranteed git merge conflicts upon PR integration. By enforcing zero diffs in `docs/project/backlog/` on feature branches, parallel PRs merge cleanly.
3. **Atomic Main Integration**: Backlog state transitions (moving the task from `refined/` to `complete/` and updating `PRIORITY.md` to `(Complete)`) are performed exclusively by the integration orchestrator under `MERGE_LOCK` directly on `main` upon successful PR merge.
4. **Non-Blocking CI Dispatch**: PR creation and CI check polling (`wait_for_ci_checks`) run concurrently outside the merge lock, preventing stream worker starvation during GitHub Actions execution.
5. **Pre-flight Base Sync & Conflict Resolution**: Before running pre-flight verification or opening a pull request, the worker automatically synchronizes the feature branch with `origin/main`. If merge conflicts are detected, the agent is invoked in the worktree to resolve them cleanly and verify preflight checks locally.
6. **In-Worktree CI Failure & Conflict Healing**: If GitHub Actions CI checks fail or the pull request goes out of mergability due to concurrent merges into `main`, the orchestrator does not dump the task back into the ready queue. Instead, it captures the failed CI job logs via `gh run view --log-failed` (or merge conflict diffs) and prompts the agent in the worktree to repair the failure, re-verifies preflight locally, and pushes the fix to update the open PR.
