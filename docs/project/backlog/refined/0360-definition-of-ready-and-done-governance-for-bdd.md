---
id: '0360'
title: Definition of Ready & Done Governance Updates for BDD and Playwright
status: Refined
created: 2026-09-28
dependencies:
- TASK-0024
- TASK-0359
governing_adrs:
- ADR-0010
- ADR-0014
governing_prds:
- PRD-0023
governing_stories:
- US-0065
target_release: 0.9.0
---

# TASK-0360: Definition of Ready & Done Governance Updates for BDD and Playwright

## Status
Refined

## Summary
Formalize repository-wide architectural and quality governance for Behavior-Driven Development (BDD) per ADR-0014. Update the **Definition of Ready (DoR)** to mandate frontdoor BDD Gherkin scenario readiness, update the **Definition of Done (DoD)** to require passing Playwright BDD browser test suites for all user-facing capabilities, update Hard Invariant 7 in `AGENTS.md` and `docs/operating-manual.md`, and author a Diataxis How-To guide (`docs/how-to/test-user-flows-with-playwright-bdd.md`).

## Problem Statement
While Runefoble has rigorous standards for microfrontends, Storybook isolation, file length invariants (<500 lines), and backend blackbox testing, the repository governance does not formally mandate end-to-end browser testing for user journeys. User stories contain Gherkin scenarios, but without contractual governance in the Definition of Ready and Definition of Done, tasks have been refined and completed with stubbed UI tabs, unhandled CustomEvents, and static mock fallbacks.

To prevent future integration regressions and ensure every user journey is verified in real browser environments, the repository's core governance documents (`AGENTS.md`, `docs/operating-manual.md`, `docs/project/backlog/README.md`, and `docs/how-to/curate-backlog-and-roadmap.md`) must be synchronized with ADR-0014.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/operating-manual.md`: Definition of Ready (line 178), Definition of Done (line 189), and Hard Invariants.
  - `docs/project/backlog/README.md`: Backlog lifecycle stages and INVEST evaluation criteria.
  - `docs/how-to/curate-backlog-and-roadmap.md`: JIT refinement criteria and backlog curation standards.
- **Governing Architecture & ADRs**:
  - **ADR-0010: Continuous Integration and Deployment Gates**: Quality gate integration.
  - **ADR-0013: Microfrontend Architecture and Service Component Vendoring**: Microfrontend boundaries.
  - **ADR-0014: Behavior-Driven Development (BDD) with Gherkin User Stories and Playwright End-to-End Validation**: Governing BDD architecture.

## Scope of Work & Implementation Plan
1. **Update Definition of Ready (DoR)**:
   - In `docs/operating-manual.md`, `docs/project/backlog/README.md`, and `AGENTS.md`:
     - Add requirement: **Frontdoor BDD Scenario Specification**: For any user-facing feature or UI view, the governing user story in `docs/project/user_stories/accepted/` must provide executable Gherkin scenarios (`Given ... When ... Then`) whose test setup is achievable strictly through public frontdoors (UI forms, Zitadel OIDC tokens, or public REST endpoints).
2. **Update Definition of Done (DoD)**:
   - In `docs/operating-manual.md`, `docs/project/backlog/README.md`, and `AGENTS.md`:
     - Add requirement: **Playwright BDD End-to-End Verification**: User-facing features must have passing Playwright BDD test suites executing all acceptance criteria scenarios in headless browser automation without backdoor state manipulation.
3. **Update Hard Invariant 7 in `AGENTS.md` and `docs/operating-manual.md`**:
   - Refine Rule 7:
     `7. Blackbox TDD & BDD with frontdoor setup. All feature development must be driven by blackbox tests interacting strictly through public frontdoors (e.g. public HTTP routes, WebSockets, or published standard domain events). All user flows and UI journeys must be expressed as Gherkin scenarios executed through Playwright browser automation without private backdoors or database manipulation.`
4. **Author Diataxis How-To Guide (`docs/how-to/test-user-flows-with-playwright-bdd.md`)**:
   - Provide practical recipes:
     - How to author Gherkin `.feature` files derived from user stories.
     - How to implement TypeScript step definitions with Playwright shadow-piercing locators.
     - How to manage frontdoor test setup and authenticated player/DM sessions.
     - How to run tests locally with `make test-e2e` and debug interactively with `make test-e2e-ui`.
5. **Update Backlog Curation & PRD Decomposition Guides**:
   - Update `docs/how-to/curate-backlog-and-roadmap.md` and `docs/how-to/decompose-prds-into-vertical-slices.md` to guide agents and engineers on auditing BDD readiness during triage.

## INVEST Criteria Evaluation
- **Independent (I)**: Governance documentation update that applies across all future user-facing tasks.
- **Negotiable (N)**: Exact wording of checklist items can be tuned while preserving strict frontdoor principles.
- **Valuable (V)**: Prevents incomplete, mocked, or broken UI interfaces from being considered "ready" or "done".
- **Estimable (E)**: Clearly defined documentation locations and Diataxis conventions.
- **Small (S)**: Confined to markdown documentation updates and a new How-To guide (< 300 lines).
- **Testable (T)**: Verified by running `make health-check` and checking markdown link integrity.

## Definition of Done
1. `AGENTS.md`, `docs/operating-manual.md`, and `docs/project/backlog/README.md` updated with revised DoR and DoD checklists.
2. Hard Invariant 7 updated to explicitly govern Playwright BDD frontdoor testing.
3. `docs/how-to/test-user-flows-with-playwright-bdd.md` authored following Diataxis guidelines.
4. `make health-check` passes with zero invariant violations or status drift.
