---
id: '0656'
title: User Story Traceability Tags on Gherkin Scenarios and a Coverage Ratchet Gate
status: Refined
created: 2026-11-17
dependencies:
- TASK-0654
- TASK-0655
governing_adrs:
- ADR-0014
- ADR-0010
governing_prds: []
governing_stories: []
target_release: 0.9.0
severity: high
source_audits:
- w2-e2e-bdd.md
---

# TASK-0656: User Story Traceability Tags on Gherkin Scenarios and a Coverage Ratchet Gate

## Status
Refined

## Summary
Feature files do not name the user stories they prove, so no tool can check coverage. Of 76 accepted user stories, 37 have no Gherkin, 39 have Gherkin, and only 2 are covered end to end. Add a story tag to every scenario. Add a gate that fails when a newly accepted user-facing story has no tagged scenario. Existing gaps are recorded in a baseline file that can only shrink.

## Problem Statement
- `w2-e2e-bdd.md` F12: of 76 accepted stories, 37 have no Gherkin block (for example US-0001 to US-0004, US-0011 to US-0015, US-0017 to US-0040). Two have full end-to-end coverage (US-0063, US-0065). Seven are partly covered. Thirty have no e2e scenario.
- The feature files do not cite story ids, so the mapping cannot be checked by tooling.
- DoR 8 and DoD 6 require Gherkin and a Playwright BDD suite for user-facing features.

## Documentation & Architecture Review
- ADR-0014 defines the BDD and Playwright rules. Add the tag rule to it as a note, or to `docs/how-to/test-user-flows-with-playwright-bdd.md`.
- ADR-0010: the gate runs in the CI pipeline and in `make test-bdd`.
- `docs/project/user_stories/REGISTRY.md` is the list of stories. The gate reads it.

## Product & User Story References
- All 76 stories in `docs/project/user_stories/accepted/` are in scope for the gate. The gate applies to user-facing stories only; the list of user-facing stories is the `persona` field plus a `ui: true` marker added by this task.

## Detailed Specification & Implementation Plan
1. Define the tag format `@US-0063` (one tag per story per scenario). Document it.
2. Tag every existing scenario in `e2e/features/*.feature` with the story id it proves. Remove scenarios that prove no story and record why.
3. Add `e2e/coverage/baseline.json`: the list of user-facing accepted stories that have no tagged scenario today. The gate fails when a story is missing from the baseline and has no tag, or when a baseline entry gains a tag and is still listed (the baseline must shrink).
4. Add `scripts/check_story_coverage.py` (run with `uv run`). It parses the registry, the story frontmatter (`persona`, `ui` marker), and the feature tags. Wire it into `make test-bdd`.
5. Add the same check to the CI pipeline job that already runs `make test-bdd` (ADR-0010).
6. Document how to update the baseline when a story is retired.

## Frontdoor Blackbox Test Plan
This is a tooling gate. Verification:
- Adding a new accepted user-facing story with no tag fails `make test-bdd` (checked locally with a temporary story file, not committed).
- Tagging a baseline story removes it from the baseline and the gate passes.
- Removing a tag from a covered story makes the gate fail.
- The check reads only repository files. No network calls and no database.

## Definition of Done
1. Every scenario in `e2e/features` has at least one story tag.
2. `e2e/coverage/baseline.json` lists the remaining uncovered user-facing stories, and its size is recorded in the task file.
3. `scripts/check_story_coverage.py` passes in `make test-bdd` and in CI.
4. `docs/how-to/test-user-flows-with-playwright-bdd.md` explains the tag rule and the baseline rule.
5. The script and the baseline are each under 500 lines.
