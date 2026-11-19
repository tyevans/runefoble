---
id: '0726'
title: Build Docs, Worktree Cleanup and Make Targets Fail Loudly
status: Complete
created: 2026-11-17
dependencies: []
governing_adrs:
- ADR-0018
governing_prds: []
governing_stories: []
target_bc: core
target_release: 0.9.0
---
# TASK-0726: Build Docs, Worktree Cleanup and Make Targets Fail Loudly

## Status
Complete

## Summary
Three developer tools hide failures. The inotify shim returns a fake descriptor, worktree cleanup treats an unknown process check as safe, and `make test-mutation` hides its exit code.

## Problem Statement
- `scripts/fake_inotify.c:21`: when the real `inotify_add_watch` fails, the shim returns `1000`. `scripts/build_docs.py:26-49` preloads it into every child process. `build_docs.py:44` continues after a compile failure.
- `scripts/cleanup_worktrees.py:53-72`: `find_active_pids_for_path` returns `[]` when `/proc` is absent, so the active-process guard passes. `:186-267` mixes eligibility, printing and removal.
- `Makefile:198-199`: `test-mutation` uses `|| true`. `Makefile:136` and `:237` run the same `helm lint`. `.PHONY` (line 1) lacks `dev`, `dev-audience-studio`, `visualize-project`, `visualize-project-build`.

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0018.
- `docs/how-to/` and `docs/reference/` pages named in the specification.

## Product & User Story References
None. Platform quality work.

## Detailed Specification & Implementation Plan
1. Remove the shim and document `fs.inotify.max_user_watches` in `docs/tutorials/01-local-development-setup.md`. If the user wants to keep it, return `-1` with `errno` set and fail the build on compile error. Record the choice in the PR.
2. In `cleanup_worktrees.py`, fail closed when `/proc` is absent: report `cannot verify` and skip. Extract a pure `decide(worktree, options)` function.
3. `make lint` depends on `helm-lint`. `test-mutation` reports survivors and exits non-zero by an explicit policy. Add the missing `.PHONY` names.
4. TASK-0434 owns `dev_server.py`. Do not edit it.

## Frontdoor Blackbox Test Plan
- `tests/test_docs_build_and_pages.py`: a build with a failing inotify call exits non-zero.
- `tests/test_cleanup_worktrees.py`: with `/proc` absent, the worktree is skipped and reported.
- `make -n lint` includes `helm-lint`.

## Definition of Done
- The specification steps are done and the tests above pass.
- Docs named in the specification are corrected.
- `uv run pytest`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: medium
- Source audits: `refactor-r1/audience-scripts-helm.md`
