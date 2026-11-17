# ADR-0018: Worktree Isolation for Backlog Work

## Status
Accepted

## Context
Several agents can work on backlog tasks at the same time. Concurrent edits in one checkout cause conflicts and lost work. The spec-ops baseline states this as spec-ops ADR-0005 (worktree concurrency and backlog isolation). Runefoble documents the rule only in the AGENTS.md dispatch section.

## Decision
1. Each backlog task runs in its own git worktree under `.worktrees/<name>` on its own branch. The branch name is `task/<id>`.
2. Only the orchestrator edits `main` and the `docs/project/backlog/` records. Workers do not edit those records.
3. Backlog moves (`refined/`, `complete/`) and `PRIORITY.md` updates happen after merge to `main`.
4. `specops.toml` sets `execution.backlog_isolation = true` and `execution.git_branch_prefix = "task/"`.

## Consequences
- Parallel workers do not conflict on backlog files.
- The branch prefix matches the branches that the team already uses (`task/0620`, `task/0664`). The spec-ops default (`feat/`) is not used.
