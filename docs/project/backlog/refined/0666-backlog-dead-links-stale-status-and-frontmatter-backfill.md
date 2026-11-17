---
id: '0666'
title: Backlog Task Links, Body Status, Complete-Record Paths, and Missing Governance Keys Are Repaired
status: Refined
created: 2026-11-17
dependencies:
- TASK-0665
governing_adrs:
- ADR-0007
- ADR-0014
governing_prds: []
governing_stories: []
target_release: 0.9.0
severity: high
source_audits:
- w3-backlog-specops.md
---

# TASK-0666: Backlog Task Links, Body Status, Complete-Record Paths, and Missing Governance Keys Are Repaired

## Status
Refined

## Summary
The backlog has dead links, stale status text, and cited paths that no longer exist. Seventy-three story and PRD links in refined and proposed tasks point at files that do not exist. Eight PRD-to-task links point at proposed tasks that are now refined. 242 complete tasks say "Refined" in the body and "Complete" in the frontmatter. 45 cited paths in complete records do not resolve, and 104 resolve only in a new location. 56 complete tasks lack `governing_prds` and `governing_stories`. Repair each group with a script, and add a check so that the drift does not return.

## Problem Statement
- Item 6 and F1 (high): 54 dead links in 24 refined files and 19 in 12 proposed files. Example: `refined/0485-remove-backward-compatibility-shims-runefoble-platform.md` cites `../../product/accepted/prd-0001-runefoble-platform-foundations.md`, which does not exist. PRD-0001 is `prd-0001-the-watcher-ai-dm-and-board-animator.md`. The same task cites `us-0010-developer-local-infrastructure-and-test-tooling.md`, but US-0010 is the Redis Streams story. `refined/0444` cites `us-0064-character-roster-and-party-assignment.md` (real slug `us-0064-character-roster-management-and-party-assignment.md`). Other dead targets: `prd-0024-settlement-haven-builder-and-establishment-ecosystem.md` and `us-0076-town-bulletin-board-and-civic-proclamations.md`.
- Item 6 and F2 (medium): `make prd-audit` reports 8 stale links. PRD-0010 links TASK-0437 and TASK-0438. PRD-0011 links TASK-0439, TASK-0440, and TASK-0441. PRD-0016 links TASK-0444, TASK-0445, and TASK-0446. All point at `proposed/`, but the files are in `refined/`.
- Item 6 and F7 (low): `proposed/0367-bulletin-board-playwright-bdd-component-coverage.md` cites PRD-0025, which does not exist. PRD-0024 covers bulletin boards and minigames.
- Item 7 and F3 (medium): 242 of 287 files in `complete/` have `status: Complete` in the frontmatter and `Refined` under `## Status` in the body. Example: `complete/0364-github-actions-ci-playwright-bdd-quality-gate.md`.
- Item 7 and F4 (medium): 56 complete tasks lack `governing_prds` and `governing_stories`. 11 (`0000` to `0010`) lack `dependencies` and `governing_adrs`. The 6 files from TASK-0665 are handled there.
- Item 7 and F5 (medium): 45 of 1,655 cited repository paths in complete records do not resolve, and 104 resolve only by name in a new location. Examples: `complete/0260` cites `tests/test_blackbox_npc_worker_engine.py` (now `tests/test_blackbox_npc_worker/`), `complete/0172` cites `services/gateway_mcp/` (real `gateway/mcp/`), and `complete/0258`, `0287`, `0288`, `0355` to `0358` cite `frontend/test/app-shell.test.ts` (now `frontend/test/app_shell/`).

## Documentation & Architecture Review
- DoR 3 and 4: stories and PRDs must be linked from tasks, and the links must resolve. The link check is part of the DoR.
- `docs/project/backlog/README.md`: lifecycle rules. Complete records are not reopened for path fixes (the audit says do not reopen unless behaviour fails).
- DoD 9 of `backlog/README.md`: backlog updates to `complete/` and `PRIORITY.md` are applied atomically by the integration orchestrator at merge to `main`. Never on a feature branch or a worktree. This task's complete-record edits follow that rule.

## Product & User Story References
Backlog governance. No product record applies.

## Detailed Specification & Implementation Plan
1. Link fixer (`scripts/fix_backlog_links.py`, run with `uv run`): for each dead link in refined and proposed tasks, retarget to the registry file for the same ID, or to the correct ID named in the task text. Log each change. Do not guess when the ID is ambiguous; list those for manual review in the task file.
2. Run `make prd-sync` (Makefile line 30), then confirm `make prd-audit` reports 0 stale links. Fix TASK-0367's PRD reference to PRD-0024.
3. Body status: for each complete record, set the `## Status` body text to `Complete` to match the frontmatter. Do this by script and verify the diff is one line per file.
4. Governance keys: add `governing_prds` and `governing_stories` with `[]` only where the task truly has none. Where the task names a PRD or story in its body, link that one.
5. Paths: for each unresolved path in a complete record, find the moved file by name and update the path. Where no file exists, mark the path as removed in that record's body. Do not reopen the task.
6. Add a link and status check to `make health-check` (or to `spec-ops health`, see TASK-0668): dead links, body-status mismatch, and unresolved cited paths in complete records all fail the check.
7. Apply the complete-record and PRIORITY changes through the integration orchestrator at merge.

## Frontdoor Blackbox Test Plan
- `scripts/check_backlog_links.py` (run with `uv run`) reports zero dead links in refined and proposed, zero stale PRD links (`make prd-audit`), zero body-status mismatches, and zero unresolved paths in complete records. Before the change it reports 73 dead links, 8 stale links, 242 mismatches, and 45 unresolved paths. After the change it reports zero.
- A test (`tests/test_blackbox_backlog_links.py`) runs the check and fails on any non-zero count.
- The check reads repository files only.

## Definition of Done
1. `scripts/check_backlog_links.py` reports zero for each category.
2. `make prd-audit` reports 0 stale links.
3. Every complete record's body status matches its frontmatter.
4. The 56 records have the governance keys, and the 11 legacy records have `dependencies` and `governing_adrs`.
5. The check runs in `make health-check` or `spec-ops health`.
6. The changes are merged and the complete-record and PRIORITY edits are applied by the integration orchestrator.
7. Each script is under 500 lines.
