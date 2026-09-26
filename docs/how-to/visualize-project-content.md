# How-To: Dynamically Visualize Project Content and Traceability

## Overview
Runefoble maintains a rich specification and project management dataset under `docs/project/`, including:
- **Architectural Decision Records (ADRs)** (`docs/project/adrs/`)
- **Product Requirement Documents (PRDs)** and Speculative Capability Matrix (`docs/project/product/`)
- **User Stories & Personas** (`docs/project/user_stories/`)
- **Engineering Backlog & Milestones** (`docs/project/backlog/`)

The **Runefoble Project Content Visualizer** (`tools/project_visualizer/`) provides an interactive, Bauhaus-styled web application to explore, query, and trace relationships across these documents in real time.

---

## 1. Launching the Live Interactive Visualizer

To run the local visualizer with dynamic file synchronization:

```bash
make visualize-project
```

Or using the runner script:
```bash
./scripts/visualize-project.sh
```

By default, the server listens on `http://127.0.0.1:8787/`.
When you edit or save any markdown file in `docs/project/`, the visualizer dynamically re-parses the repository and updates active views in real time.

---

## 2. Generating Standalone Distribution Bundles

To produce an isolated, self-contained single-file HTML dashboard with embedded styles, scripts, and project metadata (suitable for offline sharing, CI artifacts, or documentation portals):

```bash
make visualize-project-build
```

The output file is written to:
```text
dist/project-visualizer.html
```

---

## 3. Building and Publishing via Zensical & GitHub Pages

Runefoble integrates the standalone visualizer bundle with the **Zensical static documentation portal** (the high-performance Material for MkDocs successor). The entire documentation library—including all Diataxis guides, ADRs, PRDs, and user stories—is compiled, rendered, and indexed into client-side search alongside the interactive visualizer.

### Local Compilation

To build the static distribution:
```bash
make docs-build
```

This automates:
1. Generating `dist/project-visualizer.html` from repository specifications.
2. Compiling all Markdown documentation in `docs/` using `zensical build`.
3. Integrating the standalone visualizer into `site/visualizer/index.html` and `site/project-visualizer.html`.
4. Exporting structured relational data to `site/project-data.json`.
5. Generating client-side search index in `site/search.json`.

### Local Live Preview

To preview the combined documentation site and visualizer:
```bash
make docs-serve
```

The portal runs on `http://localhost:8000/`:
- **Documentation Hub**: `http://localhost:8000/`
- **Embedded Visualizer Page**: `http://localhost:8000/project-visualizer/`
- **Fullscreen Visualizer**: `http://localhost:8000/visualizer/`

### Automated Deployment to GitHub Pages

On every merge to `main`, `.github/workflows/deploy-pages.yml` executes `make docs-build` and deploys the generated distribution to GitHub Pages (`https://tyevans.github.io/runefoble/`). Pull requests automatically validate doc compilation integrity via `ci.yml`.

---

## 4. Inspecting Project Statistics via CLI

To inspect high-level coverage, health invariants, and graph edge counts directly from the command line:

```bash
python3 -m tools.project_visualizer.cli stats
```

Example output:
```text
=== Runefoble Project Content Statistics ===
Total Backlog Tasks: 58 (34 Complete, 7 Refined, 17 Proposed)
Accepted User Stories: 40
Accepted PRDs: 12
Governing ADRs: 13
Target Personas: 5
Feature Inventory: 29 (20 MVP P0)
Traceability Graph Edges: 365
Ready Buffer Health: OVER_BUFFERED (7 items)
```

To export the raw structured relational graph as JSON:
```bash
python3 -m tools.project_visualizer.cli export-json --out dist/project-data.json
```

## 5. Bespoke Antigravity (AGY) Agent Launcher (Live Server Only)

When running the visualizer locally with `make visualize-project`, developers can dispatch bespoke Antigravity (`agy`) coding agents directly from the visualizer header or from any backlog task detail drawer.

### Capabilities
- **Direct CLI Execution**: Spawns non-blocking background processes executing:
  ```bash
  agy --dangerously-skip-permissions -p "<prompt>"
  ```
  with optional session continuation (`-c`).
- **Context-Aware Task Dispatch**: Clicking **Launch AGY** inside any task card automatically compiles a bespoke prompt containing the task ID, title, specification path, target bounded context, governing ADRs, and the Runefoble Definition of Done.
- **Workflow Presets**: Quick-fill buttons for routine engineering tasks:
  - **Task Spec**: Direct implementation prompt aligned with blackbox TDD and file length invariants.
  - **Curator**: Autonomous JIT backlog curation and ready buffer maintenance (`scripts/curate-backlog.sh`).
  - **Health & Invariants**: Codebase file length audit (<500 lines limit) and modularization proposals.
  - **TDD Verification**: End-to-end verification gate execution (`pytest`, entrypoints, Helm lint).
- **Live Agent Console**: Monospace terminal viewer streaming real-time `stdout`/`stderr` logs, process exit status, elapsed time counter, and termination controls.

### Strict GitHub Pages Build Isolation
To prevent exposing local execution tooling in published public documentation:
- In static compilation mode (`make docs-build`, `make visualize-project-build`, and GitHub Pages deployment workflow), the AGY modal HTML and `agy_launcher.js` script are completely omitted from generated HTML bundles.
- Task drawers and navigation headers in static documentation render without any launcher buttons or references.
- Backend execution endpoints (`/api/agy/*`) are only registered on the local dynamic development server.

---

## 6. Key Interactive Capabilities

### 🌐 Relationship Graph & Traceability Network
- **Interactive 2D Relationship Graph**: Real 2D node-link network visualization connecting Personas, User Stories, PRDs, Backlog Tasks, and ADRs with directional relationship edges (`desires`, `specifies`, `implements`, `governed_by`, `deploys_to`, `depends_on`).
- **Multiple Layout Engines**: Switch seamlessly on the fly between:
  - **Force-Directed Physics**: Coulomb node repulsion, Hooke's Law spring tension, and centering gravity.
  - **Cyber-Flow DAG**: Layered rank-based columns for top-to-bottom or left-to-right lineage.
  - **Concentric Radar**: Radial orbits grouping entities by architectural tier (Personas -> Stories -> PRDs -> Tasks -> ADRs).
- **Live Physics Engine (`ForceSimulation`)**: Smooth 60 FPS particle dynamics with live drag-to-pin, freeze/unfreeze simulation toggle, and dynamic reheat shuffle.
- **Cyber-Rune Aesthetics & Animated Energy Flow**: Bauhaus geometric node styling with neon halo rings, status badges, linked PR chips, and animated SVG pulse currents flowing along active dependency edges.
- **Mouse-Anchored Focal Zoom & Tactile Panning**: Smooth exponential wheel zoom and double-click zoom anchored strictly to the cursor position without drift, 1:1 pixel canvas panning, and zero-jump tactile node dragging with grab offset preservation.
- **Dynamic Minimap with Real-Time Node Tracking**: Synchronized bird's-eye radar view rendering colored node positions that update continuously during physics simulations, layout switches, and node drags, featuring an interactive viewport camera window supporting click-to-center and drag-to-pan camera navigation.
- **Search Auto-Focus & Concentric Ripple Ping**: Searching or selecting an entity smoothly centers the camera and emits an animated sonar ripple ping to spotlight the target.
- **Glassmorphism Detail Tooltips & Fullscreen Mode**: Rich floating hover preview cards with node status, linked PRs, and quick actions, plus full-canvas immersion mode.
- **Bidirectional Lineage Traversal**: Clicking any node illuminates its entire upstream and downstream dependency chain while dimming unrelated entities.
- **Traceability Multi-Column Flow**: Visual column layout displaying end-to-end lineage across documents with live breadcrumb trails.
- **Hide Done Toggle**: Instantly filters out completed tasks and their isolated edges from the graph.

### 📊 Roadmap Gantt & Delivery Timeline
- **Milestone Delivery Horizons**: Chronological timeline tracking phases from Milestone 1 (Foundations) and Milestone 2 (Live Collaborative Alpha) to Milestone 3 (AI DM) and Milestone 4 (Studio).
- **Interactive Gantt Bars**: Color-coded by status (Emerald for Complete, Amber for Refined/In-Flight, Indigo for Proposed) with progress fill, duration markers, and dependency indicators (`⛓️`).
- **Group By Toggle**: Switch between grouping by Milestone (M1 - M4) or by Target Bounded Context (`the_watcher`, `board_state`, `game_session`, etc.).
- **Hide Done Toggle**: Filter out completed work to focus strictly on active sprint deliverables.

### 📋 Kanban Backlog Pipeline
- **3-Column Workflow Board**: **Complete (Shipped)**, **Refined (JIT Ready Buffer)**, and **Proposed (Candidate Pool)**.
- **Hide Done Filter**: Toggle checkbox to hide the Complete column and focus directly on active and candidate work.
- **Git Commits & PR Badges**: Displays tagged Pull Requests (`PR #30`) and commit counts directly on task cards.
- **Context & Search Filters**: Filter by target bounded context, target release, or live keyword search.

### 🔗 Git Commits & Pull Request Tracking
- **Automated Git Harvesting**: The visualizer automatically inspects git commit history (`git log`) and parses conventional task references (e.g. `feat(task-0041): ... (#30)`) to link commits and PR numbers to backlog tasks.
- **Frontmatter & Markdown Support**: Tasks can also declare explicit PRs and commits in YAML frontmatter (`prs: ["#30"]`) or a `## Pull Requests` section.
- **Detail Drawer Git History**: Inspect full commit hashes, authors, timestamps, and commit messages with one-click copy.

### 🔄 Scroll-Preserving Dynamic Live Sync
- **Intelligent Fingerprint Caching**: Uses SHA256 content hashing (`data_hash`) across `docs/project/`. Polling occurs without re-rendering or flickering if files have not changed.
- **Zero Scroll Disruption**: When changes do occur, the visualizer preserves `window.scrollY` and viewport container scroll positions, keeping your place intact.
- **Pause/Resume Toggle**: Click the Dynamic Sync pill in the header at any time to pause or resume automatic background reloads.

### 🎯 Product Requirements & Speculative Feature Inventory
- Browse PRD problem statements and checkable user outcomes.
- Interactive capability matrix table from `FEATURE_INVENTORY.md` categorized across 6 functional domains with P0 (MVP), P1 (Beta), and P2 (Horizon) badges.

### 👥 Personas & User Stories Studio
- Dossiers for all 5 Runefoble personas: **Evelyn** (DM), **Marcus** (Adventurer), **Sarah** (Absent Player), **Devon** (Streamer), and **Alex** (Developer).
- Clicking a persona filters the 40 user stories down to their specific perspective.
- Full "As a... I want to... So that..." user stories with formatted acceptance criteria.

### 🏛️ ADR Architecture Radar
- Categorized architectural decisions (Security & SpiceDB Auth, Event Sourcing & Redis Streams, Lit Microfrontends, Infrastructure & Helm, Quality & Hypothesis).
- Direct traceability from ADRs to the implementing backlog tasks.

### 📖 Slide-Over Detail Drawer & Omnibar Search
- Press `⌘K` or `/` (or click the search button) to open the global Omnibar and search across all tasks, PR numbers, commit hashes, stories, PRDs, and ADRs.
- Click any card or node anywhere in the interface to slide out the reader drawer, displaying full rendered Markdown, metadata chips, and the exact local file path with one-click copy.
- Seamless Dark / Light theme toggle with local storage persistence.
