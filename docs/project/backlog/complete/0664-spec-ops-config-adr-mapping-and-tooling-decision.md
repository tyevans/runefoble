---
id: '0664'
title: Adopt spec-ops Through specops.toml, ADR Mapping, and a Recorded Install and Security Decision
status: Complete
created: 2026-11-17
dependencies: []
governing_adrs:
- ADR-0007
- ADR-0010
- ADR-0014
governing_prds: []
governing_stories: []
target_release: 0.9.0
---

# TASK-0664: Adopt spec-ops Through specops.toml, ADR Mapping, and a Recorded Install and Security Decision

## Status
Complete

## Summary
Runefoble has no `specops.toml`, so `spec-ops health` runs with defaults and prints the project name "MyProject". The spec-ops baseline ADRs (spec as code, file length, worktree isolation, agent constitution) have no Runefoble ADR. Their numbers collide with Runefoble's ADR-0001 to ADR-0007, which the spec-ops layout would overwrite. This task adds the config, records the ADR mapping, adds the new topics as ADR-0015 and later, records how spec-ops is installed (through uv only, Hard Invariant 4), and records the decision on the optional security profile.

## Problem Statement
- `w3-backlog-specops.md` (Part B, gap analysis): `specops.toml` is missing. `spec-ops health` prints "MyProject".
- ADR numbering: Runefoble uses ADR-0001 to ADR-0014 with different topics from spec-ops ADR-0001 to ADR-0007. Running `spec-ops init` would scaffold ADR-0001 to 0007 and collide.
- Mapping (from the audit): spec-ops 0001 spec as code, 0002 file length, 0005 worktree and backlog isolation, and 0008 agent constitution and Diataxis have no Runefoble ADR. spec-ops 0003 (blackbox frontdoor) is partial in ADR-0014. spec-ops 0004 (preflight and self-healing CI) is partial in ADR-0010. spec-ops 0006 (BDD) maps to ADR-0014. spec-ops 0007 (DDD) maps to ADR-0007. spec-ops 0009 (property and mutation testing) maps to ADR-0008.
- Install: spec-ops documents `uv pip install -e .` or `uv run spec-ops`. Hard Invariant 4 forbids pip. The local CLI is at `/home/ty/.local/bin/spec-ops`, installed outside the workspace.
- The optional spec-ops `security` profile (dual-custody signing, secret scanning, lockfile checks, spec-ops ADR-0010 to 0012) is not in use.

## Documentation & Architecture Review
- `docs/project/adrs/REGISTRY.md` is the ADR index. Add each new ADR there.
- `docs/project/README.md` describes Project Management as Code. It must name the spec-ops config and the install path.
- AGENTS.md Hard Invariant 4 governs install. Record the chosen install path there.
- Do not copy spec-ops ADR-0001 to 0007 into `docs/project/adrs/accepted/`. Their filenames collide with Runefoble ADR-0001 to 0007.

## Product & User Story References
Project management tooling. No product PRD or user story applies.

## Detailed Specification & Implementation Plan
1. Create `specops.toml` at the repository root. Set `[project] name = "Runefoble"` and `docs_dir = "docs/project"`. Set `[architecture] file_length_limit = 500`, `buffer_target = 10`, and `buffer_warning_threshold = 6`. List components for `libs/*`, `services/*`, `gateway/api`, `gateway/mcp`, and `frontend`. Set `[quality] testing_style = "blackbox-frontdoor"`, `require_bdd = true`, and `preflight = ["uv run pytest"]`. Set `[execution] git_branch_prefix = "feat/"` and `backlog_isolation = true`. Confirm the field names against the spec-ops schema on the day of the change.
2. Record the ADR mapping table in `docs/project/adrs/REGISTRY.md`, with each spec-ops baseline ADR mapped to a Runefoble ADR or marked "new".
3. Write new ADRs for the uncovered topics as ADR-0015 and later: spec as code, file length, worktree and backlog isolation, and agent constitution with Diataxis. Each ADR follows the format of the existing ones in `docs/project/adrs/accepted/`.
4. Decide the install path: a uv workspace dev dependency, or `uv tool install`. Record the choice and the exact command in AGENTS.md. Pip is not permitted.
5. Decide the security profile: adopt or decline. Record the decision with a date in `docs/project/adrs/REGISTRY.md` (decline is acceptable if justified).
6. Verify with `spec-ops health` that the project name is "Runefoble".

## Frontdoor Blackbox Test Plan
- `spec-ops health` run from the repository root reports the project name Runefoble and no config warning. Before the change it prints "MyProject". After the change it prints "Runefoble".
- A test (`tests/test_blackbox_specops_config.py`) parses `specops.toml` with `tomllib` and asserts the required keys and values (`file_length_limit = 500`, `buffer_target = 10`, `testing_style = "blackbox-frontdoor"`).
- A registry check confirms every ADR file in `docs/project/adrs/accepted/` has a row in `REGISTRY.md`.

## Definition of Done
1. `specops.toml` exists with the values above, and the test passes.
2. `docs/project/adrs/REGISTRY.md` contains the mapping table and the new ADR rows.
3. The new ADR files exist (ADR-0015 and later), and no spec-ops ADR file is copied into the repository.
4. The install path and the security-profile decision are recorded in AGENTS.md and REGISTRY.md.
5. `make health-check` still passes.
6. Files stay under 500 lines.

## Audit Provenance

- Severity: medium
- Source audits: `w3-backlog-specops.md`
