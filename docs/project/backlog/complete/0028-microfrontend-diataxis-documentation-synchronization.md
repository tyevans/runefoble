---
id: 0028
title: Microfrontend Diataxis Documentation Synchronization
status: Complete
created: 2026-09-25
completed: 2026-09-26
dependencies: [TASK-0027]
governing_adrs: [ADR-0013]
target_release: 0.1.0
---

# TASK-0028: Microfrontend Diataxis Documentation Synchronization

## Status
Complete

## Summary
Documented the microfrontend architecture, service component vendoring pattern, and developer workflows across the Diataxis documentation framework in `docs/`:

1. **Reference (`docs/reference/microfrontend-architecture.md`)**:
   - Detailed monorepo directory layout, service microfrontend catalog, package naming conventions, custom element tags, and HTTP `/ui/manifest` discovery schemas.
   - Updated `docs/reference/architecture-overview.md` to reflect microfrontend bounded contexts.
2. **How-To Guide (`docs/how-to/authoring-service-microfrontends.md`)**:
   - Practical walkthrough on authoring a new Lit component in a service bounded context (`services/<bc>/ui/src/`), creating Storybook stories, and exposing the component via `/ui/manifest`.
3. **Explanation (`docs/explanation/microfrontends-in-rpg-domains.md`)**:
   - Deep architectural rationale on why W3C Web Components and Lit solve domain coupling in collaborative tabletop roleplaying platforms without multi-framework bloat.

## Verification
- Verified Diataxis structure and cross-document links.
- Pre-commit hooks for markdown and formatting pass.
