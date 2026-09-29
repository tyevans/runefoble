# Backlog Management Guide

This directory holds the engineering task queue for Runefoble.
Tasks move through three lifecycle stages:
- `proposed/`: Unrefined ideas, feature proposals, and discovered refactoring candidates.
- `refined/`: Architectural impact review completed, governing ADRs/PRDs cited, and testable blackbox definition of done established.
- `complete/`: Verified against tests, linted, committed, and integrated into the codebase.

## Core Principles

### 1. Just-In-Time (JIT) Refinement
To avoid specification drift and inventory waste, maintain a lean ready buffer of **~10 tasks** in `refined/`. Unrefined items remain lightweight problem statements in `proposed/` until they approach the top of the queue.

### 2. Roadmap & Enabler Alignment
Priority ordering in [`PRIORITY.md`](PRIORITY.md) is derived from:
1. **Foundational Enablers**: Horizontal architecture, database/event schemas, or authorization capabilities that unblock downstream features.
2. **Current Milestone Goals**: Active deliverables defined in [`ROADMAP.md`](ROADMAP.md).
3. **Refactoring & Technical Debt**: Proactive modularization to preserve repository invariants (e.g. file size <500 lines per [AGENTS.md](../../operating-manual.md)).

### 3. INVEST Criteria for Backlog Items
Every task—from initial submission in `proposed/` to formal qualification in `refined/`—must satisfy the **INVEST** criteria:
- **Independent (I)**: The task is decoupled from concurrent streams where feasible. Dependencies are explicitly declared in frontmatter (`dependencies: [...]`) and avoid cyclic or entangled delivery paths.
- **Negotiable (N)**: The specification states the problem, governing architectural ADRs, and observable outcomes without dictating rigid private implementation details, leaving room for technical trade-offs.
- **Valuable (V)**: The task delivers tangible value to players, DMs, operators, or developers (e.g. auditable security, operational visibility, or gameplay features).
- **Estimable (E)**: Scope and technical boundaries are well-understood. Governing ADRs and PRDs are cited, preventing unbounded research spikes.
- **Small (S)**: The item represents a focused unit of work achievable within a single workstream session. File changes conform strictly to the repository file length limit (<500 lines per Hard Invariant 6). Monolithic features must be split into incremental enablers.
- **Testable (T)**: Complies with Hard Invariant 7 (Blackbox TDD with frontdoor setup). The Definition of Done establishes verifiable acceptance criteria through public frontdoors (HTTP endpoints, WebSockets, or published CloudEvents), verified by automated pytest/Playwright test suites.

## Definition of Ready (DoR)

Before any task moves from `proposed/` to `refined/`, it must satisfy the Definition of Ready in [`AGENTS.md`](../../operating-manual.md):
1. **Bounded Context Identified**: Target service bounded context (`services/<bc>`) explicitly designated.
2. **Microfrontend Slice Declared**: For user-facing features, the owning UI package (`services/<bc>/ui/`) and Custom Element tag (`<runefoble-...>`) are defined per [ADR-0013](../adrs/accepted/adr-0013-microfrontend-architecture-and-service-component-vendoring.md).
3. **Storybook Isolation Planned**: Mock property states and visual acceptance criteria specified for Storybook isolation testing prior to App Shell composition.
4. **Governing ADRs & PRDs Cited**: Architectural impacts reviewed against governing ADRs (e.g. ADR-0004, ADR-0012, ADR-0013) and accepted PRDs.
5. **Frontdoor Blackbox Acceptance Criteria**: Testable scenarios specified strictly through public APIs, `/ui/manifest`, WebSockets, or published standard events (Hard Invariant 7).
6. **File Length Pre-check**: Target module decompositions planned to remain strictly within the <500 lines invariant.

## Definition of Done (DoD)

A task moves from `refined/` to `complete/` only when:
1. **Architectural Review**: Conformant with governing ADRs (including ADR-0013 for microfrontends).
2. **Microfrontend Vendoring**: User-facing components built and vendored within their owning service bounded context (`services/<bc>/ui/`), exposed via `/ui/manifest`, with the App Shell (`frontend/`) remaining strictly decoupled.
3. **Storybook Verification**: Interactive stories created and verified with zero console errors in Storybook.
4. **Documentation**: All public APIs, events, and microfrontend custom elements documented in `docs/reference/` and Diataxis guides.
5. **Automated Testing & Builds**: Python tests pass (`uv run pytest`), frontend builds pass (`pnpm run build`), and `make build` completes cleanly.
6. **Helm & Kubernetes Verification**: Helm charts lint and template without error (`helm lint`, `helm template`).
7. **Frontdoor Blackbox Suite**: End-to-end blackbox tests verify behavior exclusively through public entrypoints.
8. **File Length Invariant**: All modified and created source files strictly under 500 lines.
9. **Registry & Backlog Synchronization**: Status updated in `PRIORITY.md` and relevant PRD/ADR registries.
10. **Changelog Maintenance**: User-facing capabilities, architectural shifts, and public API/schema changes recorded in `CHANGELOG.md` under `[Unreleased]` following Keep a Changelog.
11. **Platform Showcase Maintenance**: Public Platform Showcase marketing page (`docs/marketing.md`) maintained as capabilities progress, keeping live core capabilities and roadmap milestones synchronized with current platform deliverables.

## Picking Work
Always pick the highest-priority item from [`docs/project/backlog/PRIORITY.md`](PRIORITY.md) that is currently marked `(Refined)`.

## Curation & Health Checking
Run the health scanner to inspect file length invariants and buffer readiness:
```bash
make health-check
# or: python3 .agents/skills/backlog-curator/scripts/health_check.py
```
To run the automated triage and JIT refinement cycle, trigger the `backlog-curator` skill in Antigravity or execute `./scripts/curate-backlog.sh`.
