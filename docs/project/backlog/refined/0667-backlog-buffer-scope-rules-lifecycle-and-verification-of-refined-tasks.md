---
id: '0667'
title: Backlog Ready Buffer, Epic Scope Rule, Lifecycle Folders, and Stale Refined Tasks Are Corrected
status: Refined
created: 2026-11-17
dependencies:
- TASK-0666
governing_adrs:
- ADR-0007
- ADR-0014
governing_prds:
- PRD-0014
governing_stories: []
target_release: 0.9.0
---

# TASK-0667: Backlog Ready Buffer, Epic Scope Rule, Lifecycle Folders, and Stale Refined Tasks Are Corrected

## Status
Refined

## Summary
The ready buffer holds 28 refined tasks against a target of about 10. `make prd-audit` flags all 200 proposed tasks as oversized, so the proposed list cannot tell an epic from a task. PRD-0014 is under-decomposed. Three refined tasks are not started or are stale: TASK-0436 is implemented in code, TASK-0437 and TASK-0438 need verification, and TASK-0434 has the wrong line count. The status and folder layout for user stories and PRDs disagrees with AGENTS.md. Fix each of these, in an order that keeps the buffer near target.

## Problem Statement
- Item 11 and F14 (low): 28 refined tasks against `buffer_target` 10 (warning at 6). Demote about 18 to proposed, or pull them into work.
- Item 12 and F15 (low): `make prd-audit` marks every one of the 200 proposed tasks as "Oversized / Epic" (8 to 17 scope items each). PRD-0014 is flagged as under-decomposed.
- Item 13 and F8 (medium): TASK-0436 (Gateway Soundscape API routing) is refined, but `gateway/api/src/gateway_api/routers/soundscape.py` exists, has Zanzibar checks at lines 50-65, and is mounted at `gateway/api/src/gateway_api/main.py:82`. Compare its acceptance criteria with the router and its tests. Close it or re-scope the missing parts.
- Item 13 and F9 (low): TASK-0438 is partly done (`services/soundscape/src/soundscape/event_handlers.py` handles combat, speech, and leitmotif events, not board or token events). TASK-0437 (`frontend/src/runefoble-app.ts` imports `@runefoble/soundscape-ui`) is unverified for WebSocket audio sync.
- F17 (low): TASK-0434 says `scripts/dev_server.py` is 411 lines. The file is 418 lines.
- Item 10 and F13 (low): US-0045 and US-0049 are `Shipped` in `user_stories/REGISTRY.md` but `status: Accepted` in their files. PRD-0008 and PRD-0009 are `Shipped` in `product/REGISTRY.md` but still in `product/accepted/`. AGENTS.md says PRDs move through `idea/`, `shaped/`, `accepted/`, and `shipped/`. Only `accepted/` exists.
- F6 (low): refined tasks 0437, 0440, 0445, 0446, 0498, and 0499 depend on refined tasks (0436, 0439, 0444). 0495, 0496, and 0501 depend on proposed tasks (0349, 0350, 0448).

## Documentation & Architecture Review
- `docs/project/backlog/README.md`: the buffer target is about 10 (JIT refinement). Keep it.
- `docs/how-to/curate-backlog-and-roadmap.md` and `docs/how-to/decompose-prds-into-vertical-slices.md` describe the buffer and the decomposition rules. Update them with the scope rule.
- AGENTS.md defines the `product/` lifecycle. Either create the folders and move the shipped PRDs, or change AGENTS.md to match. Choose one and record it.
- DoD 9: the PRIORITY.md changes and the folder moves are applied by the integration orchestrator at merge.

## Product & User Story References
- [`prd-0014-downtime-crafting-and-stronghold-engine.md`](../../product/accepted/prd-0014-downtime-crafting-and-stronghold-engine.md) is the PRD to decompose in item 6.

## Detailed Specification & Implementation Plan
1. Verify TASK-0436 against its acceptance criteria. Run the router's blackbox tests. If they pass and cover the criteria, close it as complete. If not, re-scope it to the missing parts in its body.
2. Verify TASK-0437 and TASK-0438 the same way. Record for each: done, partly done, or not started, with the file evidence.
3. Correct the line count in TASK-0434.
4. Buffer: demote about 18 refined tasks to proposed, starting with those that depend on proposed tasks (item F6). Keep the ones with a passing dependency chain. Record each demotion and its reason. Demotion changes the status line in each file and its PRIORITY entry (applied at merge).
5. Scope rule: define in the decomposition how-to when a proposed task is an epic (for example, more than one bounded context or more than 8 scope items). Re-label or split the 200 flagged items accordingly. Record the count before and after.
6. Decompose PRD-0014 into vertical slices with `make prd-decompose ARGS="--prd PRD-0014"`, and review the output.
7. Lifecycle: choose one of the two options from the summary, and apply it. Align the US-0045 and US-0049 status with the registry (or the reverse, with the reason).
8. Dependencies: sequence the six refined tasks behind their dependencies in PRIORITY.md, or demote them until the dependency is refined.

## Frontdoor Blackbox Test Plan
- `make prd-audit` and `make health-check` report a refined count of 10 (within the warning band of 6 to 10) and show the scope rule's flag count.
- A test (`tests/test_blackbox_backlog_buffer.py`) reads the backlog folders and asserts the refined count is between 6 and 12, that no refined task depends on a non-refined or non-complete task, and that the two registries agree on status for every US and PRD.
- Before the change the test FAILS (28 refined, dependency gaps, and the US and PRD mismatches). After the change it PASSES.

## Definition of Done
1. Refined count is between 6 and 12. Demotions are recorded.
2. TASK-0436, TASK-0437, and TASK-0438 each have a recorded verdict with evidence.
3. TASK-0434 has the correct line count.
4. The scope rule is documented, and the proposed-epic flags are reduced to the rule's output.
5. PRD-0014 is decomposed into vertical slices.
6. The lifecycle folders and the registries agree, and AGENTS.md matches the real layout.
7. The test passes in `uv run pytest`. The PRIORITY.md changes are applied by the integration orchestrator at merge.

## Audit Provenance

- Severity: medium
- Source audits: `w3-backlog-specops.md`
