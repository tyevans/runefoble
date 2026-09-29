# How-To: Decompose PRDs into Vertical Slices and Spikes

## Overview
The Runefoble product-to-engineering pipeline converts high-level user needs in Product Requirement Records (`docs/project/product/`) into actionable, vertically-sliced engineering tasks in `docs/project/backlog/proposed/`.

Autonomous task execution via `scripts/run-backlog-engine.sh` relies on tasks that can be completed within a single `agy -p` pass (under 30 minutes, producing focused source files strictly under 500 lines with frontdoor blackbox tests). When proposed tasks are monolithic or PRDs remain undecomposed, the team runs out of refinable work.

The PRD pipeline utility (`scripts/decompose-prds.sh` and `tools/prd_pipeline/`) automates PRD creation, registry maintenance, and task decomposition.

---

## Task Granularity & Slicing Principles

When decomposing a PRD, tasks adhere strictly to the following principles:

1. **Single `agy -p` Pass Sizing**:
   - Each task must represent a focused unit of work that an autonomous agent can implement, test, and document in one execution pass without hitting file length limits (<500 lines).
2. **Architectural Spikes for Novel Capabilities**:
   - If a feature introduces new frameworks, unknown spatial mathematics, novel WebGL/canvas pipelines, or unfamiliar external APIs, decompose an initial Spike task:
     `TASK-XXXX: SPIKE: Architectural Spike and ADR for ...`
   - Spikes author governing ADRs in `docs/project/adrs/` and verify interface contracts before downstream implementation.
3. **Thin Vertical Slicing**:
   - Rather than massive horizontal layers, split features into thin vertical slices:
     - **Domain & Event Sourcing**: `eventsource-py` domain events and DeclarativeAggregate handlers.
     - **API & Zanzibar Authorization**: FastAPI APIRouter, Zitadel JWT auth, and SpiceDB Zanzibar checks.
     - **Microfrontend Presentation**: Lit Web Component in `services/<bc>/ui/` with Bauhaus design tokens, Storybook stories, and `/ui/manifest`.
     - **Async Stream Engine**: Distributed Redis Streams consumer group worker.
4. **Frontdoor Blackbox Verification & BDD Readiness (Hard Invariant 7 & ADR-0014)**:
   - Every task defines concrete public entrypoint test criteria (HTTP, WebSockets, or CloudEvents) with zero backdoor state manipulation.
   - For user-facing slices and UI journeys, generate or link persona user stories in `docs/project/user_stories/accepted/` specifying executable Gherkin scenarios (`Given ... When ... Then`) whose test setup runs exclusively through public frontdoors (UI forms, Zitadel OIDC tokens, or public REST endpoints).
   - Require passing Playwright BDD test suites executing all acceptance criteria scenarios in headless browser automation as part of the Definition of Done.

---

## Using the PRD Pipeline

### 1. Auditing Backlog and PRD Health
Inspect the health of PRD records, detect undecomposed or underdecomposed PRDs, and identify oversized proposed tasks:

```bash
./scripts/decompose-prds.sh audit
# or:
make prd-audit
```

The audit checks:
- Current ready buffer size (warns if `< 8` tasks).
- Undecomposed accepted PRDs.
- Oversized proposed tasks that should be split into vertical slices.
- Stale task links across PRD files.

### 2. Creating a New PRD
Scaffold a standardized PRD markdown document in `docs/project/product/accepted/` (or `idea/`, `shaped/`):

```bash
./scripts/decompose-prds.sh create \
  --title "Alchemical Laboratory" \
  --persona "Bram the Tinkerer" \
  --bc "character_sheet" \
  --summary "Interactive potion brewing and reagent experimentation workbench."
```

This automatically generates the file with required Diataxis sections, assigns the next canonical ID (`PRD-XXXX`), and registers it in `docs/project/product/REGISTRY.md`.

### 3. Decomposing a PRD into Spikes and Vertical Slices

#### Dry-Run Planning Mode
Preview the proposed spikes and vertical slices without writing any files:

```bash
./scripts/decompose-prds.sh decompose --prd PRD-0014 --plan-only
```

#### Executing Decomposition
Generate the granular proposed tasks and supporting user stories:

```bash
./scripts/decompose-prds.sh decompose --prd PRD-0014
# or via Makefile:
make prd-decompose ARGS="--prd PRD-0014"
```

This action:
1. Generates ADR spikes and vertical slice task files in `docs/project/backlog/proposed/`.
2. Generates supporting persona user stories in `docs/project/user_stories/accepted/` if missing.
3. Updates `## Linked User Stories` and `## Implementing Backlog Tasks` in the PRD.
4. Appends the new tasks to `docs/project/backlog/PRIORITY.md`.
5. Reconciles all registries.

### 4. Agent-Assisted Semantic Decomposition
For deep contextual decomposition of complex narrative PRDs, invoke Antigravity directly with full architectural awareness:

```bash
./scripts/decompose-prds.sh agent PRD-0014
```

This generates an invariant-enforcing prompt containing all repository constraints and launches `agy` to author custom vertical slices.

### 5. Synchronizing Registries & Repairing Links
Reconcile all documentation registries and repair any links pointing to tasks that have transitioned between `proposed/`, `refined/`, and `complete/`:

```bash
./scripts/decompose-prds.sh sync
# or:
make prd-sync
```

---

## Integration in the Development Cycle

The PRD pipeline completes the three-tier autonomous engineering loop:

```
[PRD Pipeline]          ./scripts/decompose-prds.sh   (PRDs -> Spikes + Vertical Slices in proposed/)
       ↓
[Backlog Curator]       ./scripts/curate-backlog.sh    (JIT Refinement -> refined/ buffer ~10)
       ↓
[Backlog Worker Engine] ./scripts/run-backlog-engine.sh (Parallel worktrees -> single agy -p pass -> main)
```

---

## Architecture & Modular Decomposition

The decomposition engine in `tools/prd_pipeline/` is structured to adhere to Hard Invariant 6 (< 500 lines per file):

- **Manager & Scanner Modules (`tools/prd_pipeline/manager/` & `prd_manager.py`)**:
  - `PRDManager` facade orchestrates stage directory scanning via `PRDScanner` (`scanner.py`), INVEST criteria auditing via `RequirementAuditor` (`auditor.py`), and document creation/link updates via `PRDLifecycle` (`lifecycle.py`), operating on `PRDRecord`, `PRDStage`, and `AuditSummary` models (`models.py`).
- **Orchestrator Facade (`tools/prd_pipeline/decomposer.py`)**:
  - `PRDDecomposer` provides the public API for counting tasks/stories (`get_max_task_number`, `get_max_story_number`), generating plans (`plan_decomposition`), and persisting tasks (`execute_decomposition`).
- **Planning & Dependency Engine (`tools/prd_pipeline/planner.py`)**:
  - `DecompositionPlanner` and heuristics (`requires_architectural_spike`, `requires_ui_component`, `requires_worker_slice`) sequence vertical slices and build dependency graphs.
- **Templating & Metadata Serialization (`tools/prd_pipeline/templates.py` & `slice_templates.json`)**:
  - `format_task_markdown` and `format_user_story_markdown` render YAML frontmatter, INVEST criteria, and acceptance criteria.
- **Disk Persistence (`tools/prd_pipeline/writer.py`)**:
  - `PlanWriter` creates directories and writes task files to `docs/project/backlog/proposed/` and user story files to `docs/project/user_stories/accepted/`.

### Modular Test Suite

The test suite is decomposed into single-responsibility modules adhering to the file length limit (< 250 lines per module):

- **Manager & Registry Suite (`tests/test_prd_pipeline_manager.py`)**: Tests for `PRDManager`, auto-increment canonical ID generation, directory initialization, buffer health audits, and registry reconciliation.
- **Planner & Slice Analysis Suite (`tests/test_prd_pipeline_planner.py`)**: Tests for `DecompositionPlanner`, keyword-based architectural spike detection, UI component detection, worker slice heuristics, and slice dependency graphs.
- **Decomposer & Task Writer Suite (`tests/test_prd_pipeline_decomposer.py`)**: Tests for `PRDDecomposer` execution facade, counter resolution, `PlanWriter` disk serialization, and task markdown formatting.
- **CLI & Smoke Suite (`tests/test_prd_pipeline_cli.py`)**: Tests for CLI subcommands (`audit`, `create`, `decompose`, `prompt`, `sync`), error exit codes on missing records, and shell script wrappers (`scripts/decompose-prds.sh`).

