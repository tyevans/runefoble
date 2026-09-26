# Backlog Management Guide

This directory holds the engineering task queue for Runefoble.
Tasks move through three lifecycle stages:
- `proposed/`: Unrefined ideas, feature proposals, and discovered refactoring candidates.
- `refined/`: Architectural impact review completed, governing ADRs/PRDs cited, and testable blackbox definition of done established.
- `complete/`: Verified against tests, linted, committed, and integrated into the codebase.

## Core Principles

### 1. Just-In-Time (JIT) Refinement
To avoid specification drift and inventory waste, maintain a lean ready buffer of **2–3 tasks** in `refined/`. Unrefined items remain lightweight problem statements in `proposed/` until they approach the top of the queue.

### 2. Roadmap & Enabler Alignment
Priority ordering in [`PRIORITY.md`](PRIORITY.md) is derived from:
1. **Foundational Enablers**: Horizontal architecture, database/event schemas, or authorization capabilities that unblock downstream features.
2. **Current Milestone Goals**: Active deliverables defined in [`ROADMAP.md`](ROADMAP.md).
3. **Refactoring & Technical Debt**: Proactive modularization to preserve repository invariants (e.g. file size <500 lines per [AGENTS.md](../../AGENTS.md)).

### 3. INVEST Criteria for Backlog Items
Every task—from initial submission in `proposed/` to formal qualification in `refined/`—must satisfy the **INVEST** criteria:
- **Independent (I)**: The task is decoupled from concurrent streams where feasible. Dependencies are explicitly declared in frontmatter (`dependencies: [...]`) and avoid cyclic or entangled delivery paths.
- **Negotiable (N)**: The specification states the problem, governing architectural ADRs, and observable outcomes without dictating rigid private implementation details, leaving room for technical trade-offs.
- **Valuable (V)**: The task delivers tangible value to players, DMs, operators, or developers (e.g. auditable security, operational visibility, or gameplay features).
- **Estimable (E)**: Scope and technical boundaries are well-understood. Governing ADRs and PRDs are cited, preventing unbounded research spikes.
- **Small (S)**: The item represents a focused unit of work achievable within a single workstream session. File changes conform strictly to the repository file length limit (<500 lines per Hard Invariant 6). Monolithic features must be split into incremental enablers.
- **Testable (T)**: Complies with Hard Invariant 7 (Blackbox TDD with frontdoor setup). The Definition of Done establishes verifiable acceptance criteria through public frontdoors (HTTP endpoints, WebSockets, or published CloudEvents), verified by automated pytest/Playwright test suites.

## Picking Work
Always pick the highest-priority item from [`docs/project/backlog/PRIORITY.md`](PRIORITY.md) that is currently marked `(Refined)`.

## Curation & Health Checking
Run the health scanner to inspect file length invariants and buffer readiness:
```bash
make health-check
# or: python3 .agents/skills/backlog-curator/scripts/health_check.py
```
To run the automated triage and JIT refinement cycle, trigger the `backlog-curator` skill in Antigravity or execute `./scripts/curate-backlog.sh`.
