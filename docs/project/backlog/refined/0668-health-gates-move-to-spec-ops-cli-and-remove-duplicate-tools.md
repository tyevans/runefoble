---
id: '0668'
title: Health and Backlog Gates Move to the spec-ops CLI and Duplicate Local Tooling Is Retired
status: Refined
created: 2026-11-17
dependencies:
- TASK-0664
governing_adrs:
- ADR-0003
- ADR-0007
- ADR-0010
governing_prds: []
governing_stories: []
target_release: 0.9.0
---

# TASK-0668: Health and Backlog Gates Move to the spec-ops CLI and Duplicate Local Tooling Is Retired

## Status
Refined

## Summary
Runefoble keeps local copies of tools that the spec-ops CLI provides: `scripts/health_check.py` (`make health-check`), `tools/prd_pipeline` (`make prd-*`), `tools/backlog_engine` (`make backlog-worker`), and `tools/project_visualizer` (`make visualizer*`). Two local facades (`tools/prd_pipeline/prd_manager.py:1` and `decomposer.py:70`) keep backward-compatibility layers, which DoR 9 forbids. The health scanner also misses `scripts/`, `e2e/`, and `tools/`. Move the gates to `spec-ops health` and `spec-ops schema check`, keep them in CI, delete the facades, and move the other tools one at a time, each after a parity check against the spec-ops command. Parity is verified before any removal.

## Problem Statement
- Item 9 (audit): for each local tool, the spec-ops equivalent must be verified with `--help` or `--dry-run` before removal. The audit's parity table: `tools/prd_pipeline` maps to `spec-ops prd` (decompose, audit, create, sync); `tools/backlog_engine` maps to `spec-ops worker`, `queue`, `cycle`, `orchestrate`, `worktree`, `task`, `backlog`, with `backlog doctor` not run because it writes; `tools/project_visualizer` maps to `spec-ops visualizer --serve` and `--build`; `scripts/health_check.py` maps to `spec-ops health` (with `--architecture`, `--numbering`, `--modularity`).
- Item 9 and F11 (medium): `tools/prd_pipeline/prd_manager.py:1` ("PRD pipeline manager facade maintaining backwards compatibility") and `tools/prd_pipeline/decomposer.py:70` ("Backward compatibility delegates").
- Item 14 and F10 (medium): `scripts/health_check.py:inspect_file_lengths` scans `libs`, `services`, `gateway`, `frontend/src`, `frontend/test`, and `tests`. It misses `scripts/`, `e2e/`, and `tools/`. `scripts/dev_server.py` (418 lines) and `e2e/steps/campaign_hub_steps.ts` (445 lines) are above the 400-line warning, but `make health-check` does not list them. `spec-ops health` does.
- F16 (low): `Makefile:21,24,27,30,33` run `python3 -m tools.prd_pipeline.cli` and `python3 -m tools.backlog_engine.cli` without `uv run`. AGENTS.md Hard Invariant 4 says Python runs through `uv` or the Makefile, so this is allowed but not uv-managed.
- F18 (low): `tools/project_visualizer` (about 1,435 lines) duplicates `spec-ops visualizer`. Proposed tasks 0235, 0291, 0328, 0335, and 0346 decompose the local visualizer. They become moot if the local tool is removed.
- Item 14 (audit): the spec-ops gates must stay in CI, and `docs/reference/cli-interfaces.md` must name the gate and its commands.

## Documentation & Architecture Review
- ADR-0010 (continuous integration): the CI job runs the gates. Update the job to call `spec-ops health` and `spec-ops schema check`.
- ADR-0003 (uv workspace): Python runs through uv. A `uv tool install` or workspace dev dependency is chosen in TASK-0664.
- `docs/reference/cli-interfaces.md`: update the gate rows. This file is also edited by TASK-0663. Sequence TASK-0663 first, or merge the two edits in one change.
- The backlog-worker and the visualizer are documented in `docs/how-to/run-autonomous-backlog-engine.md` and the visualizer how-to. Update them when the target changes.

## Product & User Story References
Project management tooling. No product record applies.

## Detailed Specification & Implementation Plan
1. Gate first: replace `make health-check` with a target that runs `spec-ops health` and `spec-ops schema check`. Keep the existing target name so that CI and docs still work. Delete `scripts/health_check.py` once the new target passes. Keep the file-length rule (Hard Invariant 6) enforced by `spec-ops health --modularity`, and confirm that it covers `scripts/`, `e2e/`, and `tools/`.
2. Facades: delete `tools/prd_pipeline/prd_manager.py` and the compatibility delegates at `tools/prd_pipeline/decomposer.py:70`. Update every call site to the real module in `tools/prd_pipeline/manager/`. Do not keep a re-export.
3. PRD gate: run `spec-ops prd audit` and `spec-ops prd --help`. Map each `make prd-*` target to its spec-ops command in `docs/reference/cli-interfaces.md`. Move the targets one at a time. Each move has its tests (`tests/test_prd_pipeline_*.py`) rewritten to call the public CLI.
4. Backlog worker: map `make backlog-worker` to the spec-ops worker and queue commands. Run `--dry-run` for each. Move the target only after the dry-run output matches the local engine on a sample task. Do not run `spec-ops backlog doctor` (it writes repairs).
5. Visualizer: replace `make visualizer*` with `spec-ops visualizer --serve` and `--build` after a side-by-side render check. Delete `tools/project_visualizer` only after the check passes. The proposed tasks 0235, 0291, 0328, 0335, and 0346 are then closed as moot by their owners at the orchestrator's merge.
6. Makefile: any remaining Python target runs through `uv run`.
7. Record each parity result in the task file. A tool that has no spec-ops equivalent stays, and the task names it.

## Frontdoor Blackbox Test Plan
- `make health-check` runs `spec-ops health` and `spec-ops schema check` and exits 0. It fails when a deliberately oversized file is added to `e2e/` or `scripts/` (checked locally, not committed).
- `make prd-audit` and the backlog worker dry-run produce the same counts as before the move (recorded).
- A test (`tests/test_blackbox_gate_targets.py`) runs `make -n health-check` and asserts it invokes spec-ops, not `scripts/health_check.py`.
- Before the change the file-length gate misses an oversized file under `e2e/`. After the change it reports it.

## Definition of Done
1. `make health-check` uses spec-ops and covers `scripts`, `e2e`, and `tools`.
2. `scripts/health_check.py` and the two compatibility facades are deleted, with call sites updated.
3. Each moved `make` target has a recorded parity check and a passing public-CLI test.
4. `docs/reference/cli-interfaces.md` lists the gate and each target's spec-ops command.
5. CI runs `spec-ops health` and `spec-ops schema check`.
6. Local tools that remain have a recorded reason.
7. Files stay under 500 lines. Changes are merged, and the orchestrator closes the moot visualizer tasks.

## Audit Provenance

- Severity: medium
- Source audits: `w3-backlog-specops.md`, `w3-docs-integrity.md`
