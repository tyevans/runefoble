---
id: '0681'
title: Replace Per-Test File Layout and Line-Limit Assertions With the Single Health Gate
status: Complete
created: 2026-11-17
dependencies: []
governing_adrs:
- ADR-0003
- ADR-0014
governing_prds: []
governing_stories: []
target_release: 0.9.0
---

# TASK-0681: Replace Per-Test File Layout and Line-Limit Assertions With the Single Health Gate

## Status
Complete

## Summary
About a dozen test files assert their own line limits (for example 250 or 110 lines) and assert that named source files exist. These are white-box checks of code structure. They fail on correct refactors and they duplicate the 500-line rule that `make health-check` enforces. This task deletes them and keeps one gate.

## Problem Statement
- After TASK-0640, 12 tests failed only because a file grew past a local limit, a fixture module was removed on purpose, or a test folder gained a module. Examples: `tests/test_frontend_spa_router.py:39`, `tests/test_blackbox_app_shell_test_modular_decomposition.py`, `tests/test_blackbox_gateway_decomposition.py`, `tests/test_blackbox_character_roster_binding.py` (asserts a TypeScript method signature as text).
- Hard Invariant 6 sets one limit (~500 lines). Local, stricter limits are not a project rule.
- Hard Invariant 7 asks for tests through public frontdoors. Text matching on source files is not a frontdoor test.

## Documentation & Architecture Review
- `AGENTS.md` Hard Invariants 6 and 7. `make health-check` is the file-length gate.
- `docs/how-to/curate-backlog-and-roadmap.md` describes the file invariant scan.

## Product & User Story References
None. This is engineering hygiene with no user-facing change.

## Detailed Specification & Implementation Plan
1. Find the tests: `grep -rlnE "splitlines\(\)|len\(.*lines|must exist|\.exists\(\)" tests/ | xargs grep -lE "\.ts|\.py\"" `. Review each match.
2. For each test function that only checks line counts, file existence, module counts or source text: delete it. If the file then has no tests, delete the file.
3. Keep tests that run behaviour (HTTP, WebSocket, events, or a real `pnpm test` run).
4. If a deleted check guarded a real rule that health-check does not cover, add that rule to `scripts/health_check.py` (one place) instead.
5. Update `docs/how-to/curate-backlog-and-roadmap.md` if it names these tests.

## Frontdoor Blackbox Test Plan
- `make health-check` fails when a source file exceeds 500 lines (existing behaviour; add a test with a temporary oversized file in a tmp dir if none exists).
- The full suite passes after a refactor that moves code between files without behaviour change.

## Definition of Done
- No test asserts per-file line limits, file existence of source modules, or source text.
- `make health-check` is the only file-length gate. Tests pass. CHANGELOG line given to the orchestrator.

## Audit Provenance

- Severity: medium
- Source audits: `work/0640b.md`
