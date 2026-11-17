---
id: '0661'
title: AGENTS.md Documentation Index and Repository Layout Match the Repository
status: Refined
created: 2026-11-17
dependencies: []
governing_adrs:
- ADR-0003
- ADR-0007
governing_prds: []
governing_stories: []
target_release: 0.9.0
severity: medium
source_audits:
- w3-docs-integrity.md
---

# TASK-0661: AGENTS.md Documentation Index and Repository Layout Match the Repository

## Status
Refined

## Summary
The AGENTS.md documentation index omits five how-to and reference files. Several index descriptions promise content the target files do not contain. The repository layout table omits `services/inference_worker/`, `tools/`, `scripts/`, and `tests/`. AGENTS.md is the agent entry point, so each agent reads these lines first. Make every index entry accurate, and add the missing entries.

## Problem Statement
- A1 (medium): these files are not indexed: `docs/how-to/authoring-service-microfrontends.md`, `docs/how-to/run-autonomous-backlog-engine.md`, `docs/reference/microfrontend-architecture.md`, `docs/reference/spicedb-zitadel-identity-sync.md`, and `docs/explanation/microfrontends-in-rpg-domains.md`.
- A2 (low): the index line for tutorial 01 (line 73) says it covers Storybook. The tutorial has no Storybook section.
- A3 (low): line 134 says `ports-and-endpoints.md` covers "infrastructure ports". That table is in `platform-services.md`. Line 142 says `cli-interfaces.md` covers uv and Antigravity commands, and it does not (see TASK-0663).
- A4 (low): the repository layout table omits `services/inference_worker/`, `tools/`, `scripts/`, and `tests/`.
- Checked and healthy: 73 footnote references and 26 definitions, none missing; no dead links in the index.

## Documentation & Architecture Review
- AGENTS.md is the agent index (DoR 9 and the Documentation Directory section). Entries must describe the target file's real contents.
- The footnote numbering must stay complete. Run the footnote check after editing.
- ADR-0003: the Python workspace members are listed in the layout (`services/inference_worker`, `tools`, `tests`).

## Product & User Story References
Developer documentation. Not user-facing.

## Detailed Specification & Implementation Plan
1. Add the five missing entries under the correct Diataxis heading, with a one-line description each.
2. Fix the tutorial 01 description to the real content, or add a Storybook step to tutorial 01 (TASK-0657 owns the tutorial, so correct the index description here and let TASK-0657 decide).
3. Correct the `ports-and-endpoints.md` and `cli-interfaces.md` descriptions to match their content.
4. Add the four layout rows with their real paths.
5. Run the footnote check script that already exists in `scripts/` (or add one under `scripts/`, run with `uv run`) and confirm 0 missing and 0 unused footnotes.
6. Do not add new footnotes that point at files that do not exist.

## Frontdoor Blackbox Test Plan
- A link and index check (`scripts/check_agents_index.py`, run with `uv run`) parses every `docs/**/*.md` file, compares it with the AGENTS.md index, and fails on any file that is not indexed or any index line that links to a missing file.
- Before the edit the check reports the five unindexed files. After the edit it passes.
- The footnote check passes: 0 undefined, 0 unused.

## Definition of Done
1. Every how-to, reference, and explanation file is listed in the AGENTS.md index (the check passes).
2. Every index description matches its target file (checked by hand and recorded in the task file).
3. The repository layout table lists all top-level source directories.
4. The footnote check passes.
5. The index check runs in `make health-check` or `spec-ops health` (decision in TASK-0668).

## Orchestrator Addenda (2026-11-17)

Source: `.audit/synth/discovered-round1.md`.

- `docs/reference/inference-worker-response-contract.md` exists on main but is not in the AGENTS.md reference index.
