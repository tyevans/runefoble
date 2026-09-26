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

## 3. Inspecting Project Statistics via CLI

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

---

## 4. Key Interactive Capabilities

### 🌐 Traceability Network & Redstring Lineage
- Visual multi-column layout showing the flow: **Personas ➔ User Stories ➔ PRDs ➔ Backlog Tasks ➔ ADRs**.
- **Interactive Click to Trace**: Clicking any node illuminates its entire upstream and downstream lineage thread while dimming unrelated records.
- Live breadcrumb trail showing the active dependency path.
- Filters by Persona, Task Status, and Bounded Context.

### 🗺️ Milestones & Roadmap Horizon
- Tracks progress across Milestones 1 to 4:
  - **Milestone 1**: Platform Foundation & Core Loop (100% Complete)
  - **Milestone 2**: Live Collaborative Alpha (Current)
  - **Milestone 3**: AI DM & Ecosystem Expansion (Planned)
  - **Milestone 4**: Broadcast Studio & Community Platform (Planned)
- Circular progress gauges, task burn-up numbers, and interactive enabler checklists.

### 📋 Kanban Backlog Pipeline
- 3-column workflow board: **Complete (Shipped)**, **Refined (JIT Ready Buffer)**, and **Proposed (Candidate Pool)**.
- Filter by target bounded context (`the_watcher`, `board_state`, `game_session`, `character_sheet`, `voice_agent`, `gateway_api`, `gateway_mcp`).
- Displays microfrontend tags (`<runefoble-...>`), target releases, and governing ADR references.

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
- Press `⌘K` or `/` (or click the search button) to open the global Omnibar and search across all 120+ entities.
- Click any card or node anywhere in the interface to slide out the reader drawer, displaying full rendered Markdown, metadata chips, and the exact local file path with one-click copy.
- Seamless Dark / Light theme toggle.
