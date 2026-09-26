---
icon: lucide/network
---

# Project Content & Traceability Visualizer

The **Runefoble Project Content Visualizer** provides an interactive web application to explore, query, and trace relationships across all Architectural Decision Records (ADRs), Product Requirements Documents (PRDs), User Stories, and Backlog Tasks in real time.

<div style="margin: 1.5rem 0; display: flex; gap: 1rem; align-items: center; flex-wrap: wrap;">
  <a href="visualizer/" target="_blank" class="md-button md-button--primary">
    🚀 Launch Fullscreen Visualizer
  </a>
  <a href="how-to/visualize-project-content/" class="md-button">
    📖 Read Visualizer Guide
  </a>
  <a href="project-data.json" target="_blank" class="md-button">
    📦 Raw JSON Graph Data
  </a>
</div>

<div style="position: relative; width: 100%; height: 85vh; min-height: 600px; border-radius: 8px; overflow: hidden; border: 1px solid rgba(127, 127, 127, 0.25); box-shadow: 0 4px 20px rgba(0,0,0,0.15);">
  <iframe src="visualizer/" style="width: 100%; height: 100%; border: none;" allowfullscreen title="Runefoble Project Visualizer"></iframe>
</div>

---

## Interactive Capabilities

### 🌐 Relational Traceability Graph
- **Multiple Layout Engines**: Switch on the fly between **Force-Directed Physics** (Hooke/Coulomb simulation), **Cyber-Flow DAG** (rank-ordered columns), and **Concentric Radar** (architectural tiers).
- **Bidirectional Lineage Traversal**: Selecting any entity illuminates upstream and downstream dependency chains across Personas $\to$ Stories $\to$ PRDs $\to$ Tasks $\to$ ADRs.
- **Search & Auto-Focus**: Jump directly to any task or document with smooth animated camera centering and sonar ripple spotlighting.
- **Minimap Navigator**: Real-time bird's-eye canvas minimap with draggable viewport rectangle and instant spatial orientation.

### 📊 Roadmap Gantt & Delivery Timeline
- **Milestone Horizons**: Chronological roadmap tracking progress from Foundations (M1) and Live Collaborative Alpha (M2) to AI DM (M3) and Studio (M4).
- **Domain Context Filtering**: Group deliverables by bounded context (`the_watcher`, `board_state`, `game_session`, etc.) or milestone horizon.

### 📋 Kanban Backlog Pipeline
- **3-Column Stage Pipeline**: Live tracking of **Complete (Shipped)**, **Refined (JIT Buffer)**, and **Proposed (Candidate Pool)** tasks.
- **Hide Shipped Filter**: Instantly isolate active and upcoming sprint work.
