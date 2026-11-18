---
id: '0665'
title: Frontmatter Conforms to spec-ops Schema v2.0 for Stories, PRDs, and Backlog Tasks, With Personas Defined
status: Refined
created: 2026-11-17
dependencies:
- TASK-0664
governing_adrs:
- ADR-0007
- ADR-0014
governing_prds: []
governing_stories: []
target_release: 0.9.0
---

# TASK-0665: Frontmatter Conforms to spec-ops Schema v2.0 for Stories, PRDs, and Backlog Tasks, With Personas Defined

## Status
Refined

## Summary
`spec-ops schema check` exits 1 with 86 errors. 44 PRDs in `product/accepted/` lack `target_persona` or `component`. 33 user stories lack `persona`. 8 complete backlog records have a missing or forbidden frontmatter key. Four personas used by the story registry (Sam, Mayor Theron, Lady Nicole, Kip) are not defined in `PERSONAS.md`. Backlog tasks also have no `target_bc`. Fix the frontmatter and personas so that the schema check exits 0. Decide whether `target_bc` is required, and set it on every refined and proposed task if so.

## Problem Statement
- Item 3 (audit): no backlog task has `target_bc`. The schema v2.0 validator lists it as required with default `core`. Whether a missing value fails the check is not confirmed by the 86-error run, so verify it first.
- Item 4a: 33 story files lack `persona:` (for example `us-0001-player-commands-board-via-voice.md`, `us-0004-developer-tests-component-in-storybook.md`, `us-0011-...`). The registry lists a persona for them anyway.
- Item 4b: 44 PRD errors (`product/accepted/`). Each lacks `target_persona` or `component`.
- Item 4c: 8 backlog errors in `backlog/complete/`. Six files (`0000`, `0001`, `0002`, `0003`, `0007`, `0008`) have no YAML frontmatter, and their first line is `# TASK-0000: ...`. `prd_url` (in `0100`) and `user_story` (one file) are forbidden keys.
- Item 8: `docs/project/user_stories/PERSONAS.md` defines 8 personas (Evelyn, Marcus, Sarah, Devon, Alex, Rowan, Bram, Nadia). The story registry uses Sam (US-0076), Mayor Theron (US-0072), Lady Nicole (US-0075), and Kip (US-0074). Add these four.

## Documentation & Architecture Review
- ADR-0014 and `docs/project/user_stories/REGISTRY.md`: the persona field is the link between a story and its persona. The registry value is the source. The file value must match it.
- `docs/project/backlog/README.md` describes the task frontmatter. Update it with the `target_bc` rule.
- ADR-0007: `target_bc` names the bounded context (`services/<bc>`). Use the bounded-context name from the task body.

## Product & User Story References
Traceability of personas and stories. Governing records are the stories and PRDs this task edits; they do not need new links.

## Detailed Specification & Implementation Plan
1. Run `spec-ops schema check` and save its output to the task log. Confirm the 86 errors are still present, and confirm whether a missing `target_bc` is an error.
2. Personas: add Sam, Mayor Theron, Lady Nicole, and Kip to `PERSONAS.md` in the `## N. Name — Role` format, with the description already used in the registry.
3. Stories: add `persona:` to the 33 files, using the registry value. Do not change any other key.
4. PRDs: add `target_persona:` and `component:` to the 44 PRDs. Use the persona in the PRD body and the UI component named in the PRD. If a PRD has no UI component, write `component: none` and say why in the body.
5. Complete backlog records: add frontmatter to `0000`, `0001`, `0002`, `0003`, `0007`, and `0008` with the real `id`, `title`, `status: Complete`, and `created`. Remove `prd_url` from `0100` and the forbidden `user_story` key from its file. Do not change the body or the status of the task.
6. `target_bc`: if the validator requires it, add it to every refined and proposed task (228 files), and to complete tasks only if the validator requires it there. Use the bounded-context name from the task body. Record the rule in the backlog README.
7. Run `spec-ops schema check` and confirm exit 0.

## Frontdoor Blackbox Test Plan
- `spec-ops schema check` exits 0. Before the change it exits 1 with 86 errors. After the change it exits 0.
- A pytest test (`tests/test_blackbox_backlog_frontmatter.py`) parses the frontmatter of every story, PRD, and task, and asserts the required keys. It fails on the same 86 cases before the change.
- Each story's `persona` value appears in `PERSONAS.md`. The test asserts this for all 76 stories.

## Definition of Done
1. `spec-ops schema check` exits 0.
2. `PERSONAS.md` defines all 12 personas used by the registry.
3. Every accepted story has `persona:` matching the registry.
4. Every accepted PRD has `target_persona` and `component`.
5. The six legacy complete records have frontmatter, and the forbidden keys are gone.
6. The `target_bc` rule is recorded in the backlog README, and applied as the rule requires.
7. The frontmatter test passes in `uv run pytest`.
8. This change is made on a feature branch and merged, and the complete-record edits are applied by the integration orchestrator at merge to `main` (backlog records are not edited directly on feature branches, per DoD 9).

## Audit Provenance

- Severity: medium
- Source audits: `w3-backlog-specops.md`
