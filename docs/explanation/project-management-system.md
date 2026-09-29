# Project Management as Code & Autonomous Execution Rationale

This document explains the architectural principles, trade-offs, and design rationale behind Runefoble's project management system housed in `docs/project/`.

---

## 1. Why Project Management as Code?

Traditional software development frequently isolates requirements and task tracking inside external SaaS platforms (e.g. Jira, Linear, Notion). While convenient for manual entry, this externalization introduces critical failure modes:

1. **Specification Drift**: Code evolves in git while tickets remain static in external silos. Within months, ticket descriptions contradict running reality.
2. **Context Blindness for Coding Agents**: Autonomous coding agents (`agy`) have direct access to the repository filesystem. Storing specifications in external web APIs requires cumbersome network authentication, lacks git worktree isolation, and prevents version-locking specifications with code branches.
3. **Loss of Atomic State Transitions**: In external systems, moving a ticket to "Done" happens independently of merging the PR, leading to phantom "Done" tickets whose code failed CI or was reverted.

By storing Personas, PRDs, User Stories, Backlog Tasks, and ADRs as version-controlled Markdown documents with YAML frontmatter:
- **Specifications branch and merge with code**: A task specification reflects the state of the codebase at that exact commit.
- **Agents parse documents natively**: Autonomous workers read task definitions, dependency graphs, and governing ADRs using standard filesystem tools.
- **Traceability is machine-verifiable**: Linters and visualizers compute graph lineages (`Persona → Story → PRD → Task → ADR`) without external API calls.

---

## 2. Why Just-In-Time (JIT) Refinement & Lean Buffers?

In traditional waterfall or over-planned agile systems, teams refine dozens of tasks weeks in advance. When underlying architecture changes (e.g. adopting a new Zanzibar authorization pattern or decomposing an aggregate), previously refined tasks become stale, requiring massive re-estimation and editing.

Runefoble prevents inventory waste by maintaining a **lean ready buffer of ~10 tasks** in `docs/project/backlog/refined/`:
- **Unrefined tasks remain lightweight problem statements** in `docs/project/backlog/proposed/`.
- **Refinement occurs just before execution**: When the ready buffer drops below ~8 items, the automated Backlog Curator (`scripts/curate-backlog.sh`) qualifies the highest-priority proposed items against the Definition of Ready.
- **Freshness guarantee**: Tasks in `refined/` reflect the latest architectural decisions, event schemas, and test harnesses.

---

## 3. Why Thin Vertical Slices & Single-Pass Sizing?

Autonomous agents and human developers alike perform best with bounded, single-responsibility scopes:
- **Single `agy -p` Pass**: Tasks are sized to be implementable, verifiable, and documentable within a single autonomous workstream session (<30 minutes), without violating Hard Invariant 6 (<500 lines per file).
- **Vertical over Horizontal**: Instead of massive horizontal layers (e.g., building all database tables for the entire system at once), tasks slice vertically:
  - Domain events and aggregate state handlers (`eventsource-py`).
  - Public REST / WebSocket APIs with SpiceDB authorization.
  - Microfrontend Lit custom elements with Storybook verification (`services/<bc>/ui/`).
  - Redis Streams async event consumers.
- **Architectural Spikes**: High-uncertainty areas (such as novel WebGL physics or custom audio DSP filters) are isolated into explicit spike tasks (`TASK-XXXX: SPIKE: ...`) that author governing ADRs and test harness prototypes before downstream feature slices are refined.

---

## 4. Why Strict Backlog Isolation on Feature Branches?

When multiple autonomous workers run concurrently (`make backlog-worker`), parallel workers create separate git worktrees (`feat/<task-slug>`).

If worker branches were permitted to modify backlog state (such as moving task files or updating `docs/project/backlog/PRIORITY.md`), parallel pull requests would constantly conflict upon merge, causing CI failures and worker stalls.

**The Solution: Strict Backlog Isolation**:
1. **Zero Diff Invariant**: Feature branches must never modify `docs/project/backlog/`. The worker git hook automatically reverts any unintentional backlog changes prior to pushing.
2. **Parallel PRs Merge Cleanly**: Because feature branches only touch service code, microfrontend packages, tests, and Diataxis guides, PRs merge cleanly into `main` without contention.
3. **Atomic Main Integration**: Backlog state transitions (moving the task from `refined/` to `complete/` and updating `PRIORITY.md`) are executed exclusively by the orchestrator under `MERGE_LOCK` directly on `main` upon PR merge.

---

## 5. Why Blackbox Testing with Frontdoor-Only Setup?

Unit tests and mock-heavy tests frequently verify implementation details rather than observable behavior. When private internal methods are refactored, mock-heavy tests break even if user behavior remains correct. Worse, tests with backdoor state manipulation (`INSERT INTO database`) bypass domain aggregate validation, masking critical schema and authorization bugs.

**The Frontdoor Rule (Hard Invariant 7 & ADR-0014)**:
- **Setup (`Given`)**: Prepared strictly through public frontdoors: public HTTP APIs (`POST /api/v1/campaigns`), Zitadel OIDC tokens injected into `localStorage`, or published standard CloudEvents.
- **Actions (`When`)**: Real browser interactions via Playwright (clicking buttons, entering text, navigating routes) or public HTTP calls.
- **Verification (`Then`)**: Observable outputs in the DOM (piercing Shadow DOM via Playwright locators), live WebSocket state reflections, or persisted query projections.

This guarantees that tests simulate real users and external clients, providing genuine confidence in system stability.

---

## 6. How Git Metadata Harvesting Closes the Loop

To bridge the gap between static Markdown records and living repository history:
1. **Commit Convention**: Every commit references its canonical task (`feat(task-0259): Title (#292)`).
2. **PR Automation**: Pull request descriptions embed task specifications, dependencies, and governing ADRs.
3. **Automated Harvesting**: `GitMetadataHarvester` (`tools/project_visualizer/git_metadata.py`) continuously scans `git log`, parsing task IDs and PR tags.
4. **Living Traceability**: The Project Content Visualizer dynamically displays linked commits, commit authors, timestamps, and PR chips on task cards and graph nodes, closing the loop between planning and production code without manual bookkeeping.

For complete architectural specifications, see [`docs/project/README.md`](../project/README.md).
