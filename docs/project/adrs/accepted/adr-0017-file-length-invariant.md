# ADR-0017: File Length Limit of 500 Lines

## Status
Accepted

## Context
Large source files hide responsibilities and slow review. AGENTS.md Hard Invariant 6 sets a file length limit of 500 lines. Before this ADR, only AGENTS.md stated the limit. The spec-ops baseline states it as spec-ops ADR-0002.

## Decision
1. No source file may exceed 500 lines. This applies to Python, TypeScript, and Lit component files.
2. Files at or above 400 lines produce a proactive refactoring warning.
3. `specops.toml` sets `architecture.file_length_limit = 500` and `buffer_warning_threshold = 6`. `spec-ops health` enforces the limit.
4. The gate covers every source root in `specops.toml`. A new source root must be added to the gate before it receives code.

## Consequences
- Files that exceed the limit must be split into focused modules before merge.
- Two existing files (`scripts/dev_server.py`, `e2e/steps/campaign_hub_steps.ts`) are above the warning level. Their decomposition tasks remain in the backlog.
