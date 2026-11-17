---
id: '0627'
title: Add pytest-timeout to the Workspace Dev Group and Gate the Timeout Flag
status: Complete
created: 2026-11-17
dependencies: []
governing_adrs:
- ADR-0003
- ADR-0010
governing_prds: []
governing_stories: []
target_release: 0.9.0
severity: low
source_audits:
- w1-gates-python.md
---

# TASK-0627: Add pytest-timeout to the Workspace Dev Group and Gate the Timeout Flag

## Status
Complete

## Summary
The gate command `uv run pytest -q --timeout=300` fails with "unrecognized arguments" because `pytest-timeout` is not installed. The suite therefore has no hang protection. Add the plugin to the root dev dependency group through uv and make the gate command in the Makefile use it.

## Problem Statement
- `uv run pytest -q -p no:randomly --timeout=300` exits with a usage error; nothing runs (`.audit/reports/w1-gates-python.md` F1).
- No backlog task mentions `pytest-timeout` (grep of `proposed/` and `refined/`).
- Root `pyproject.toml` `[dependency-group] dev` lacks it.

## Documentation & Architecture Review
- ADR-0003: dependencies change only through uv (`uv add --group dev pytest-timeout`), and `uv.lock` is updated in the same change.
- ADR-0010 (CI pipeline): the test command in CI must match the documented gate.
- `docs/reference/cli-interfaces.md` documents `make test`; keep it accurate.

## Product & User Story References
- None; quality gate hygiene.

## Detailed Specification & Implementation Plan
1. Run `uv add --group dev pytest-timeout` at repo root. Commit `pyproject.toml` and `uv.lock`.
2. Set a default timeout in `[tool.pytest.ini_options]` (`timeout = 300`, `timeout_method = "thread"`), so `uv run pytest` is protected without a flag.
3. Keep `make test` as `uv run pytest`. Document that a timed-out test fails with a timeout error.
4. Check that no test relies on a longer runtime; if one does, mark it explicitly with `@pytest.mark.timeout(<n>)` and record why.

## Frontdoor Blackbox Test Plan
- Before fix: `uv run pytest --timeout=300 tests/test_entrypoints.py` exits 4 (usage error).
- After fix: the same command exits 0. A throwaway fixture test that sleeps 2 seconds with `timeout(1)` fails with a timeout, proving the plugin is active (check run locally, not committed).

## Definition of Done
1. `pytest-timeout` in the dev group and `uv.lock`.
2. `uv run pytest` full suite passes with the default timeout.
3. The command documented in `docs/reference/cli-interfaces.md` matches.
4. No file above 500 lines.
