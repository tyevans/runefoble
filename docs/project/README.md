# Runefoble Project Management System Architecture

## Overview & Core Philosophy

Runefoble employs a fully machine-readable, traceable, and executable **Project Management as Code** system housed under `docs/project/`. Rather than treating planning records as disposable tickets in external proprietary silos, all project management assets—user personas, product requirement records (PRDs), user stories, architectural decision records (ADRs), engineering tasks, and end-to-end acceptance tests—live directly within the git repository as structured Markdown files with YAML frontmatter.

This architecture enforces **unbroken bidirectional traceability**: every merged line of production code links back to a governing engineering task, which links to an architectural decision record and a user story, which realizes a product requirement record designed to resolve a specific user persona's pain point.

```
[Persona] (Pain Point & Goal)
    ↓ desires
[User Story] (Connextra + Executable Gherkin)
    ↓ specifies
[Product Requirement Record (PRD)] (Needs & Checkable Outcomes)
    ↓ decomposed into
[Backlog Task] (INVEST Sized, DoR, Dependencies, Target BC)
    ├── governed by ──→ [Architectural Decision Record (ADR)]
    ├── verified by  ──→ [Playwright BDD & Blackbox Pytest]
    └── delivered in ──→ [Git Commit `feat(task-XXXX)` & GitHub PR]
```

Every document in this system is parsed continuously by automated tooling, audited for structural invariants, visualized in an interactive 2D graph, and synchronized with git commit logs and pull requests.

---

## The Core Entities & Lifecycles

### 1. User Personas ([`user_stories/PERSONAS.md`](user_stories/PERSONAS.md))
Personas represent the archetypes who interact with Runefoble. They anchor every requirement in human emotion and concrete workflow constraints:
- **Evelyn (The Overworked DM)**: Needs AI automation for token bookkeeping, line-of-sight math, and atmospheric sensory prompts.
- **Marcus (The Voice-First Adventurer)**: Needs low-friction natural voice commands ("I charge three squares north") without menu clutter.
- **Sarah (The Absent Player)**: Needs AI stand-ins with playful penalties ("drunk", "foolishness") and recap reels so game night is never canceled.
- **Devon (The Streamer / Spectator)**: Needs transparent OBS HUD overlays, spectator camera tracking, and real-time Watcher chronicles.
- **Alex (The Developer / Modder)**: Needs FastMCP agent tool gateways, OpenAPI specs, and high-throughput Redis Streams event contracts.
- **Rowan, Bram, Nadia, Mayor Theron**: Specialized personas for worldbuilding codices, campfire downtime crafting, kinetic spell VFX, and town governance.

### 2. Product Requirement Records (PRDs) ([`product/`](product/))
PRDs capture problem statements, scope fences, and checkable outcomes. They never dictate private internal code structures:
- **Lifecycle Stages**: `idea/` → `shaped/` → `accepted/` → `shipped/`.
- **Anatomy**:
  - `Who this is for`: Target personas and use cases.
  - `What the person cannot do today`: Existing friction and shortcomings.
  - `What good looks like`: Desired capabilities across macro domains.
  - `What this does not do`: Explicit scope fences to prevent scope creep.
  - `Checkable Outcomes`: Falsifiable, observable criteria verifiable via frontdoors.
  - `Linked User Stories` & `Implementing Backlog Tasks`: Relational references.

### 3. User Stories ([`user_stories/`](user_stories/))
User stories articulate end-to-end user value from the persona perspective, acting as the single source of truth for UI journeys:
- **Directory**: [`user_stories/accepted/`](user_stories/accepted/), indexed in [`user_stories/REGISTRY.md`](user_stories/REGISTRY.md).
- **Anatomy**:
  - **YAML Frontmatter**: `id`, `title`, `status`, `persona`, `feature`, `governing_prd`.
  - **Connextra Framing**: `As a <role>, I want <capability>, So that <benefit>`.
  - **Executable Gherkin Scenarios**: `Given ... When ... Then ... And ...` defining observable user flows without private backdoors.

### 4. Architectural Decision Records (ADRs) ([`adrs/`](adrs/))
ADRs document architecturally significant choices following Michael Nygard's structure (Status, Context, Decision, Consequences):
- **Directory**: [`adrs/accepted/`](adrs/accepted/), indexed in [`adrs/REGISTRY.md`](adrs/REGISTRY.md).
- **Core Guardrails**:
  - **ADR-0001**: Fine-grained authorization via SpiceDB Zanzibar (`runefoble.zed`).
  - **ADR-0002 & ADR-0011**: Event-sourced aggregates via `eventsource-py` on PostgreSQL.
  - **ADR-0004 & ADR-0013**: Microfrontend architecture using Lit Web Components, Storybook isolation, and `/ui/manifest` vendoring.
  - **ADR-0006**: High-throughput distributed event broker via Redis Streams.
  - **ADR-0014**: BDD with Gherkin User Stories and Playwright browser automation.
- **Architectural Spikes**: High-uncertainty features trigger preliminary spike tasks (`TASK-XXXX: SPIKE: ...`) that author and validate ADRs before feature implementation.

### 5. Engineering Tasks & Backlog ([`backlog/`](backlog/))
Engineering work lives in three state directories governed by strict queuing principles:
- **`proposed/`**: Lightweight problem statements, refactoring proposals, and vertical slices from PRD decompositions.
- **`refined/`**: Work qualified against the **Definition of Ready (DoR)**. Maintained as a lean **Just-In-Time (JIT) buffer of ~10 tasks** to prevent specification drift.
- **`complete/`**: Verified against the **Definition of Done (DoD)**, passing all tests, linted, committed, and integrated into `main`.
- **Linear Prioritization**: [`backlog/PRIORITY.md`](backlog/PRIORITY.md) defines the strict sequential order of execution, derived from foundational architecture enablers and milestone deliverables in [`backlog/ROADMAP.md`](backlog/ROADMAP.md).

---

## Definition of Ready (DoR) & Definition of Done (DoD)

### Definition of Ready (DoR)
Before any task transitions from `proposed/` to `refined/`, it must satisfy:
1. **INVEST Criteria**: Independent (explicit `dependencies: [...]`), Negotiable, Valuable, Estimable, Small (single `agy -p` pass, files <500 lines), Testable (public frontdoor verification).
2. **Bounded Context Identified**: Owning service designated (`services/<bc>`).
3. **Microfrontend Slice Declared**: Owning UI package (`services/<bc>/ui/`) and custom element tag (`<runefoble-...>`) designated per ADR-0013.
4. **Storybook Isolation Planned**: Mock property states and visual acceptance criteria specified for isolated Storybook verification prior to App Shell composition.
5. **Governing ADRs & PRDs Cited**: Explicit linkages declared in frontmatter.
6. **BDD Gherkin Readiness**: User-facing flows linked to accepted user stories with frontdoor-only `Given` preconditions (ADR-0014).
7. **File Length Pre-Check**: Target module decompositions planned under 500 lines per file.

### Definition of Done (DoD)
A task transitions from `refined/` to `complete/` only when:
1. **Architectural Conformity**: Adheres to all governing ADRs and Hard Invariants.
2. **Microfrontend Vendoring**: Lit Web Components built in `services/<bc>/ui/`, exposed via `/ui/manifest`, decoupled from App Shell.
3. **Storybook Verification**: Interactive stories verified with zero console errors.
4. **Frontdoor Blackbox & BDD Tests**: Automated pytest suites and Playwright BDD browser scenarios pass cleanly without backdoors.
5. **File Length Invariant**: All modified and created files strictly <500 lines.
6. **Build & Lint Verification**: `uv run pytest`, `pnpm run build`, `make health-check`, and Helm template validation pass.
7. **Documentation Updated**: Diataxis guides authored/updated in `docs/`.
8. **Changelog & Showcase Sync**: Changes recorded in `CHANGELOG.md` under `[Unreleased]` and `docs/marketing.md` updated for public milestones.

---

## Quality Invariants & Blackbox Testing

### Hard Invariant 7: Blackbox TDD & BDD with Frontdoor Setup
Runefoble prohibits reaching into private internals or using backdoor database manipulation in tests:
- **Setup (`Given`)**: Preconditions are prepared exclusively through public frontdoors:
  - Public REST API endpoints (`POST /api/v1/campaigns`, `POST /api/v1/characters`).
  - Zitadel OIDC authentication with synthetic JWT injection into `localStorage` (`auth_fixtures.ts`).
  - Standard CloudEvents published to Redis Streams.
- **Actions (`When`)**: Triggered via realistic browser interactions (Playwright clicking, typing, dragging tokens, keyboard hotkeys) or public HTTP calls.
- **Verification (`Then`)**: Assertions observe public outputs: rendered DOM elements (piercing Lit Shadow DOM via Playwright's native shadow-piercing locators), route hash updates (`#/campaigns`), toast notifications, WebSocket state changes, or emitted CloudEvents.

### Hard Invariant 6: File Length Limit (<500 lines)
Source files over 500 lines are prohibited. The repository enforces proactive modularization:
- Monolithic routers decompose into APIRouter submodules (`docs/how-to/decompose-microservice-routers.md`).
- Large aggregate models decompose into focused domain event and command modules.
- Test suites decompose into single-responsibility test files (<250 lines each).
- Verified continuously via `make health-check` (`scripts/health_check.py`).

---

## Bidirectional Cross-Referencing & Git/PR Tagging

### YAML Frontmatter Contract
Every task file encodes machine-readable linkages:
```yaml
---
id: 0259
title: Settlement Haven Builder and Establishment Aggregate Domain Model
status: Complete
created: 2026-09-27
dependencies:
  - TASK-0164
  - TASK-0208
governing_adrs:
  - ADR-0001
  - ADR-0002
governing_prds:
  - PRD-0024
governing_stories:
  - US-0072
  - US-0073
target_release: 0.8.0
pr_url: https://github.com/tyevans/runefoble/pull/292
---
```

### Git Commit & PR Tagging Conventions
The autonomous delivery engine and developer workflows follow strict tagging conventions:
1. **Feature Commits**:
   ```text
   feat(task-0259): Settlement Haven Builder and Establishment Aggregate Domain Model (#292)

   Automated execution of TASK-0259.
   Governing ADRs: ADR-0001, ADR-0002
   ```
2. **Pull Requests**:
   - **Title**: `feat(task-XXXX): <Task Title>`
   - **Body**: Automatically embeds canonical task ID, governing ADRs, dependencies, and full specification body.
   - **Task Frontmatter**: Updated with `pr_url: https://github.com/.../pull/XXX`.
3. **Atomic Backlog Transition Commits**:
   ```text
   chore(backlog): complete TASK-0259
   ```

### Automated Git Metadata Harvesting
The **GitMetadataHarvester** (`tools/project_visualizer/git_metadata.py`) continuously scans git history:
- Inspects `git log --pretty=format:%h%x09%an%x09%ad%x09%s`.
- Regex-parses task identifiers (`\btask[-_ ]?(\d+)\b`) and PR numbers (`(?:pull request\s*#|PR\s*#|#)(\d+)`).
- Dynamically maps commit hashes, authors, dates, and PR badges directly onto backlog tasks in the visualizer graph, Kanban board, and slide-over drawers without manual bookkeeping.

---

## The Three-Tier Autonomous Engineering Loop

The project management system powers fully autonomous, conflict-free software delivery across three automated tiers:

```
┌─────────────────────────────────────────────────────────────┐
│ Tier 1: PRD Decomposition Pipeline                         │
│ ./scripts/decompose-prds.sh (tools.prd_pipeline)            │
│ PRD → Architectural Spikes + Thin Vertical Slices in proposed│
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ Tier 2: Backlog Curation & Health Scanner                   │
│ ./scripts/curate-backlog.sh (backlog-curator skill)         │
│ Health checks (<500 lines) → JIT refinement → refined/ (~10)│
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ Tier 3: Autonomous Backlog Worker Engine                    │
│ ./scripts/run-backlog-engine.sh (tools.backlog_engine)      │
│ Parallel worktrees → Pre-flight checks → CI Watcher → main   │
└─────────────────────────────────────────────────────────────┘
```

### 1. PRD Pipeline (`tools/prd_pipeline/`, `scripts/decompose-prds.sh`)
- Audits backlog buffer health and detects undecomposed PRDs.
- Scaffolds standardized PRDs in [`product/accepted/`](product/accepted/).
- Decomposes PRDs into thin vertical slices (Domain/Events, API/Zanzibar, Lit Microfrontend, Async Worker) and ADR Spikes, writing tasks to [`backlog/proposed/`](backlog/proposed/) and user stories to [`user_stories/accepted/`](user_stories/accepted/).

### 2. Backlog Curator (`scripts/curate-backlog.sh`, `make health-check`)
- Inspects repository file lengths; files refactoring tasks in [`backlog/proposed/`](backlog/proposed/) for files approaching 500 lines.
- Evaluates top proposed items against INVEST criteria and Definition of Ready.
- Refines items JIT to maintain a ready buffer of ~10 tasks in [`backlog/refined/`](backlog/refined/).
- Reconciles [`backlog/PRIORITY.md`](backlog/PRIORITY.md) with filesystem state.

### 3. Backlog Worker Engine (`tools/backlog_engine/`, `scripts/run-backlog-engine.sh`)
- **Parallel Worktree Execution**: Runs concurrent worker agents in isolated git worktrees (`feat/<task-slug>`).
- **Strict Backlog Isolation**: Feature branches are **strictly forbidden from modifying `docs/project/backlog/`**. This guarantees zero git merge conflicts across parallel PRs.
- **In-Worktree Pre-Flight Verification**: Executes pytest suites, frontend builds, and Helm linting with automatic agent repair loops (up to 3 attempts).
- **Non-Blocking CI Watching & Self-Healing**: Dispatches PRs, monitors GitHub Actions CI (`ci_watcher.py`), diagnoses failures via `gh run view --log-failed`, prompts the agent in the worktree to repair failures, and pushes updates.
- **Atomic Merge & Backlog Transition**: Under `MERGE_LOCK` directly on `main`, the orchestrator merges the PR, moves the task from [`backlog/refined/`](backlog/refined/) to [`backlog/complete/`](backlog/complete/), updates [`backlog/PRIORITY.md`](backlog/PRIORITY.md), commits `chore(backlog): complete TASK-XXXX`, and pushes to `main`.

---

## The Living Project Visualizer (`tools/project_visualizer/`)

The Runefoble Project Content Visualizer provides an interactive, real-time web application to inspect and navigate the entire project management network:

1. **Interactive 2D Traceability Graph**:
   - Renders Personas (Amber), Stories (Cyan), PRDs (Rose), Tasks (Emerald/Amber/Purple), and ADRs (Indigo) with directional energy links (`desires`, `specifies`, `implements`, `governed_by`, `deploys_to`, `depends_on`).
   - Multiple layout engines: Force-Directed Physics (Hooke/Coulomb simulation), Cyber-Flow DAG (hierarchical rank columns), and Concentric Radar.
   - Bidirectional lineage traversal: clicking any entity spotlights its entire upstream and downstream dependency chain.
2. **Roadmap Gantt & Delivery Timeline**:
   - Visualizes delivery horizons from Milestone 1 to Milestone 11+, groupable by milestone or bounded context with dependency indicator chains.
3. **Kanban Backlog Pipeline**:
   - 3-column workflow board (Complete, Refined, Proposed) with Hide Done filtering, bounded context filters, and live PR/commit badges.
4. **Slide-Over Detail Drawer & Omnibar Search**:
   - Global `⌘K` omnibar searching across tasks, PR numbers, commit hashes, stories, PRDs, and ADRs.
   - Full rendered Markdown reader with metadata chips, linked PRs, and commit history.
5. **In-Browser Antigravity (AGY) Agent Launcher**:
   - Spawns background `agy` agent jobs directly from task cards with context-aware prompt templates for specification implementation, backlog curation, and TDD verification.
6. **Static Publishing via Zensical & GitHub Pages**:
   - Compiles a standalone HTML bundle (`dist/project-visualizer.html`) embedded directly into the Zensical documentation portal and deployed to GitHub Pages on every merge.

---

## Operational CLI Cheatsheet

| Purpose | Command | Governing Guide |
|---|---|---|
| **Audit PRD & Buffer Health** | `make prd-audit` or `./scripts/decompose-prds.sh audit` | [`decompose-prds-into-vertical-slices.md`](../how-to/decompose-prds-into-vertical-slices.md) |
| **Scaffold New PRD** | `./scripts/decompose-prds.sh create --title "..." --persona "..." --bc "..."` | [`decompose-prds-into-vertical-slices.md`](../how-to/decompose-prds-into-vertical-slices.md) |
| **Decompose PRD into Slices** | `make prd-decompose ARGS="--prd PRD-XXXX"` | [`decompose-prds-into-vertical-slices.md`](../how-to/decompose-prds-into-vertical-slices.md) |
| **Check File Length Invariants** | `make health-check` | [`curate-backlog-and-roadmap.md`](../how-to/curate-backlog-and-roadmap.md) |
| **Curate Backlog & Refine JIT** | `./scripts/curate-backlog.sh` | [`curate-backlog-and-roadmap.md`](../how-to/curate-backlog-and-roadmap.md) |
| **Launch Autonomous Workers** | `make backlog-worker` or `./scripts/run-backlog-engine.sh` | [`run-autonomous-backlog-engine.md`](../how-to/run-autonomous-backlog-engine.md) |
| **Run Interactive Visualizer** | `make visualize-project` (port 8787) | [`visualize-project-content.md`](../how-to/visualize-project-content.md) |
| **Run Playwright BDD Suite** | `make test-e2e` or `make test-bdd` | [`test-user-flows-with-playwright-bdd.md`](../how-to/test-user-flows-with-playwright-bdd.md) |
| **Build Static Doc Portal** | `make docs-build` | [`visualize-project-content.md`](../how-to/visualize-project-content.md) |
