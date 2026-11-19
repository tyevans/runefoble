# Architectural Decision Record (ADR) Registry

This registry records every architectural decision in Runefoble. Numbers are allocated sequentially.

| ID | Title | Status | Date | File |
|---|---|---|---|---|
| ADR-0001 | Zanzibar-Style Fine-Grained Authorization with SpiceDB | Accepted | 2026-09-25 | [`adr-0001-spicedb-zanzibar-object-authorization.md`](accepted/adr-0001-spicedb-zanzibar-object-authorization.md) |
| ADR-0002 | Event-Driven Gameplay Architecture and The Watcher AI Engine | Accepted | 2026-09-25 | [`adr-0002-event-driven-watcher-gameplay-orchestration.md`](accepted/adr-0002-event-driven-watcher-gameplay-orchestration.md) |
| ADR-0003 | UV Monorepo Workspace for Python Bounded Contexts | Accepted | 2026-09-25 | [`adr-0003-uv-monorepo-workspace-for-python-bcs.md`](accepted/adr-0003-uv-monorepo-workspace-for-python-bcs.md) |
| ADR-0004 | Frontend Component Architecture with Lit, Vite, and Storybook | Accepted | 2026-09-25 | [`adr-0004-lit-web-components-and-storybook-ui.md`](accepted/adr-0004-lit-web-components-and-storybook-ui.md) |
| ADR-0005 | Kubernetes-First Infrastructure with Helm and Kind | Accepted | 2026-09-25 | [`adr-0005-kubernetes-first-infrastructure-with-helm-and-kind.md`](accepted/adr-0005-kubernetes-first-infrastructure-with-helm-and-kind.md) |
| ADR-0006 | Redis Streams as the High-Throughput Event Broker | Accepted | 2026-09-25 | [`adr-0006-redis-streams-event-streaming.md`](accepted/adr-0006-redis-streams-event-streaming.md) |
| ADR-0007 | Domain-Driven Design (DDD) Layering and Ubiquitous Language | Accepted | 2026-09-25 | [`adr-0007-domain-driven-design-architecture.md`](accepted/adr-0007-domain-driven-design-architecture.md) |
| ADR-0008 | Property-Based Testing with Hypothesis and Mutation Testing with Mutmut | Accepted | 2026-09-25 | [`adr-0008-property-and-mutation-testing-with-hypothesis-and-mutmut.md`](accepted/adr-0008-property-and-mutation-testing-with-hypothesis-and-mutmut.md) |
| ADR-0009 | Code Quality, Static Analysis, and Linting via Ruff and Pre-commit | Accepted | 2026-09-25 | [`adr-0009-code-quality-and-linting-with-ruff-and-pre-commit.md`](accepted/adr-0009-code-quality-and-linting-with-ruff-and-pre-commit.md) |
| ADR-0010 | Continuous Integration and Deployment Gates via GitHub Actions | Accepted | 2026-09-25 | [`adr-0010-continuous-integration-pipeline.md`](accepted/adr-0010-continuous-integration-pipeline.md) |
| ADR-0011 | eventsource-py as Core Event Sourcing and Aggregate Engine | Accepted | 2026-09-25 | [`adr-0011-eventsource-py-core-event-sourcing.md`](accepted/adr-0011-eventsource-py-core-event-sourcing.md) |
| ADR-0012 | Design System Theming Tokens and Bauhaus Modernist Aesthetic | Accepted | 2026-09-25 | [`adr-0012-design-system-theming-and-bauhaus-modernism.md`](accepted/adr-0012-design-system-theming-and-bauhaus-modernism.md) |
| ADR-0013 | Microfrontend Architecture and Service Component Vendoring | Accepted | 2026-09-25 | [`adr-0013-microfrontend-architecture-and-service-component-vendoring.md`](accepted/adr-0013-microfrontend-architecture-and-service-component-vendoring.md) |
| ADR-0014 | Behavior-Driven Development (BDD) with Gherkin User Stories and Playwright End-to-End Validation | Accepted | 2026-09-28 | [`adr-0014-bdd-gherkin-user-stories-and-playwright-e2e.md`](accepted/adr-0014-bdd-gherkin-user-stories-and-playwright-e2e.md) |
| ADR-0015 | Audit Remediation Decisions (Campaign Ownership, Thin Gateway, Token Verification, Registration, Service Credentials, Event Store) | Accepted | 2026-11-17 | [`adr-0015-audit-remediation-decisions.md`](accepted/adr-0015-audit-remediation-decisions.md) |
| ADR-0016 | Specifications Are Code in docs/project | Accepted | 2026-11-17 | [`adr-0016-spec-as-code-project-records.md`](accepted/adr-0016-spec-as-code-project-records.md) |
| ADR-0017 | File Length Limit of 500 Lines | Accepted | 2026-11-17 | [`adr-0017-file-length-invariant.md`](accepted/adr-0017-file-length-invariant.md) |
| ADR-0018 | Worktree Isolation for Backlog Work | Accepted | 2026-11-17 | [`adr-0018-worktree-and-backlog-isolation.md`](accepted/adr-0018-worktree-and-backlog-isolation.md) |
| ADR-0019 | Agent Constitution and Diataxis Documentation | Accepted | 2026-11-17 | [`adr-0019-agent-constitution-and-diataxis-documentation.md`](accepted/adr-0019-agent-constitution-and-diataxis-documentation.md) |
| ADR-0020 | Declarative Dynamic Tool Handlers | Accepted | 2026-11-17 | [`adr-0020-declarative-dynamic-tool-handlers.md`](accepted/adr-0020-declarative-dynamic-tool-handlers.md) |
| ADR-0021 | Bounded Context Packages Inside game_session | Accepted | 2026-11-19 | [`adr-0021-game-session-internal-bounded-contexts.md`](accepted/adr-0021-game-session-internal-bounded-contexts.md) |

## spec-ops Baseline Mapping

The spec-ops baseline ADRs (spec-ops ADR-0001 to ADR-0009) use the same numbers as Runefoble ADR-0001 to ADR-0009 for different topics. Runefoble does not copy the spec-ops files. Each spec-ops topic maps to a Runefoble ADR below, or to a new ADR that uses the next free number.

| spec-ops baseline | Topic | Runefoble mapping | Status |
|---|---|---|---|
| 0001 | Spec as code | [ADR-0016](accepted/adr-0016-spec-as-code-project-records.md) | New |
| 0002 | File length under 500 lines | [ADR-0017](accepted/adr-0017-file-length-invariant.md) | New |
| 0003 | Blackbox frontdoor testing | ADR-0014 (partial). AGENTS.md Hard Invariant 7 | Partial |
| 0004 | Preflight and self-healing CI | ADR-0010 (partial) | Partial |
| 0005 | Worktree and backlog isolation | [ADR-0018](accepted/adr-0018-worktree-and-backlog-isolation.md) | New |
| 0006 | BDD Gherkin and Playwright | ADR-0014 | Mapped |
| 0007 | DDD and bounded contexts | ADR-0007 | Mapped |
| 0008 | Agent constitution and Diataxis | [ADR-0019](accepted/adr-0019-agent-constitution-and-diataxis-documentation.md) | New |
| 0009 | Property and mutation testing | ADR-0008 | Mapped |

Rule: Runefoble ADR numbers are stable. A spec-ops ADR file is never copied into `accepted/`.

## spec-ops Install and Security Decisions

| Decision | Outcome | Date | Record |
|---|---|---|---|
| spec-ops install path | `uv tool install` pinned to a commit. Pip is not used (Hard Invariant 4). Command in AGENTS.md. | 2026-11-17 | AGENTS.md, Command Reference |
| spec-ops security profile | Declined for now. The profile needs dual-custody signing and signed commits. No signing keys or custody process exist. Revisit when signing is in place. | 2026-11-17 | This registry |
