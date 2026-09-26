---
id: 0024
title: Update Definition of Ready and Definition of Done for Microfrontends
status: Complete
created: 2026-09-25
completed: 2026-09-26
dependencies: []
governing_adrs: [ADR-0004, ADR-0012, ADR-0013]
target_release: 0.1.0
---

# TASK-0024: Update Definition of Ready and Definition of Done for Microfrontends

## Status
Complete

## Summary
Updated repository-wide quality standards—specifically the **Definition of Ready (DoR)** and **Definition of Done (DoD)**—across `AGENTS.md`, `docs/project/backlog/README.md`, and `docs/how-to/curate-backlog-and-roadmap.md` to reflect the microfrontend architecture. Any user-facing feature in a service bounded context must specify its vertical slice microfrontend (`services/<bc>/ui/`) and visual Storybook acceptance criteria before being pulled, and must vendor its Lit Web Components, storybook stories, and HTTP discovery endpoints before being considered done.

## Key Changes
- `AGENTS.md`:
  - Added dedicated `## Definition of Ready` section specifying bounded context ownership, microfrontend slice declaration, Storybook mock criteria, and blackbox frontdoor expectations.
  - Enhanced `## Definition of Done` to require service microfrontend vendoring (`services/<bc>/ui/`), Storybook verification with zero console errors, App Shell decoupling, `/ui/manifest` frontdoor registration, and Diataxis documentation.
- `docs/project/backlog/README.md`:
  - Formalized the Definition of Ready checklist for refining backlog items.
- `docs/how-to/curate-backlog-and-roadmap.md`:
  - Updated JIT refinement steps to verify microfrontend ownership and Storybook testability.

## Verification
- Verified against `AGENTS.md` and repository backlog guidelines.
- Clean health check run with zero drift.
