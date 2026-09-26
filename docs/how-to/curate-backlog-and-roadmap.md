# How-To: Curate the Backlog and Align with the Roadmap

## Overview
Backlog curation in Runefoble uses lean Just-In-Time (JIT) refinement, continuous refactoring scanning, and roadmap dependency alignment. Rather than bulk-refining work far in advance, the team maintains a lean ready buffer of 2–3 tasks in `docs/project/backlog/refined/`.

## Running the Health Check
Inspect the repository for file length invariant violations (<500 lines) and review buffer status:
```bash
make health-check
```
Or run the Python script directly:
```bash
python3 .agents/skills/backlog-curator/scripts/health_check.py
```

## Running the Backlog Curator
To run the automated triage, refactoring scan, and JIT refinement cycle:

### Method 1: Developer Runner Script
```bash
./scripts/curate-backlog.sh
```

### Method 2: Antigravity Interactive / Slash Command
Within an active `agy` or IDE session, ask the agent:
```text
Curate the backlog using the backlog-curator skill.
```
Or schedule it to run daily at 9:00 AM:
```text
/schedule 0 9 * * * Curate the backlog using the backlog-curator skill.
```

## How Curation Operates
1. **Health & Invariants**: Identifies files approaching or exceeding 500 lines per `AGENTS.md` Rule 6, filing refactoring proposals in `docs/project/backlog/proposed/`.
2. **Roadmap Alignment**: Reads `docs/project/backlog/ROADMAP.md` (e.g. Milestone 2: Live Collaborative Alpha) to ensure foundational architectural enablers precede dependent feature epics.
3. **JIT Refinement**: Checks `docs/project/backlog/refined/`. If fewer than 2 items are ready, it refines the top proposed enabler/task against the Definition of Ready in `AGENTS.md`—including INVEST criteria (Independent, Negotiable, Valuable, Estimable, Small, Testable), bounded context isolation, microfrontend UI slice declaration (`services/<bc>/ui/`) per [ADR-0013](../project/adrs/accepted/adr-0013-microfrontend-architecture-and-service-component-vendoring.md), Storybook isolation planning, and a frontdoor blackbox TDD Definition of Done.
4. **PRIORITY Index Sync**: Reconciles `docs/project/backlog/PRIORITY.md` with filesystem state.
