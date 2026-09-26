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

## Picking Work
Always pick the highest-priority item from [`docs/project/backlog/PRIORITY.md`](PRIORITY.md) that is currently marked `(Refined)`.

## Curation & Health Checking
Run the health scanner to inspect file length invariants and buffer readiness:
```bash
make health-check
# or: python3 .agents/skills/backlog-curator/scripts/health_check.py
```
To run the automated triage and JIT refinement cycle, trigger the `backlog-curator` skill in Antigravity or execute `./scripts/curate-backlog.sh`.
