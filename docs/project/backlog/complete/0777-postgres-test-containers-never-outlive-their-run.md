---
id: '0777'
title: PostgreSQL Test Containers Never Outlive Their Run
status: Complete
created: 2026-11-17
dependencies: []
governing_adrs:
- ADR-0005
- ADR-0011
governing_prds: []
governing_stories: []
target_bc: core
target_release: 0.9.0
---

# TASK-0777: PostgreSQL Test Containers Never Outlive Their Run

## Status
Complete

## Summary
The `postgres_service` fixture starts a Docker container and stops it in its teardown. When a pytest run is killed (a timeout, an interrupt, a stopped agent), the teardown does not run. The container stays up until someone removes it by hand. Seven such containers were running on 2026-11-17, the oldest for seven hours.

## Problem Statement
- `tests/helpers/postgres.py:36` names the container `runefoble-pg-test-<port>` and starts it with `--rm -d`. Only the fixture teardown stops it.
- Parallel runs from several worktrees share the host. A cleanup must not stop a container that a live run still uses.

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0005, ADR-0011.
- `docs/how-to/test-cross-service-calls-with-live-upstreams.md` and the testing reference, where they describe Docker-backed fixtures.

## Product & User Story References
None. Platform quality work.

## Detailed Specification & Implementation Plan
1. Label each container with the owner process id and host name (`--label runefoble.test.owner-pid=<pid>`).
2. Before the fixture starts a container, remove the labelled containers whose owner process is no longer alive on this host. Do not touch containers whose owner is alive.
3. Apply the same rule to the SpiceDB container of the `authz_live` suite, if it has the same lifetime.
4. Document the rule where the Docker-backed fixtures are described.

## Frontdoor Blackbox Test Plan
- Start a container through the fixture in a child pytest process, kill that process with SIGKILL, then run the fixture again: the orphan is gone, and a container owned by a live process stays.

## Definition of Done
- A killed run leaves no container behind after the next run starts.
- `uv run pytest`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: medium
- Source audits: `drafts/round3-notes.md`
