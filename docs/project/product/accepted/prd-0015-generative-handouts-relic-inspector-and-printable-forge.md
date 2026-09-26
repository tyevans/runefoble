---
id: '0015'
title: Generative Diegetic Handouts, 3D Relic Inspector & Printable Tabletop Forge
status: Accepted
created: 2026-09-26
---

# PRD-0015 — Generative Diegetic Handouts, 3D Relic Inspector & Printable Tabletop Forge

## Who this is for

Chroniclers, worldbuilders, and hybrid tabletop crafters (like Rowan) and Game Masters (like Evelyn) who want diegetic, tactile artifacts both on-screen and printed in the physical world.

## What the person cannot do today

- In existing VTTs, finding an in-world letter or clue means reading a plain text box or staring at a static raster image.
- Players cannot interact with handouts—they cannot break wax seals, inspect intricate 3D carvings, or reveal secret invisible ink runes.
- Exporting virtual battlemaps and tokens for physical in-person play requires third-party tools to tile grids onto multi-page PDFs, often resulting in misaligned scales.
- Physical tabletop miniatures lack modular digital accessories like snap-on status rings or custom STL token bases.

## What good looks like

1. **Generative Diegetic In-World Handouts**:
   - Spoken or prompted generation of weathered fantasy letters, royal decrees, bounty posters, and ancient crypt maps.
   - Interactive breakable wax seals with realistic stamp physics, breaking sound effects, and secret UV-reactive invisible ink revealed under simulated torchlight.
2. **Interactive 3D Relic & Artifact Inspector**:
   - WebGL 3D viewer rendering magical items, ornate daggers, and cryptic puzzle boxes.
   - 360-degree rotation, zoomable engravings, interactive mechanical latches, and pulsating attunement lighting.
3. **Printable Tabletop Forge (PDFs & Papercraft)**:
   - One-click export of tactical battlemaps calibrated to exact 1-inch physical grids across multi-page A4/Letter PDFs with alignment marks and cut lines.
   - Printable folding papercraft standees with front/back character portraits and HP tracking slots.
4. **3D Printable STL Miniature Bases & Condition Clips**:
   - Procedural generation of watertight 3D printable 25mm/28mm/50mm token bases and snap-on status rings (Poisoned, Blessed, Blinded) exportable as standard STL files.
5. **Collaborative Living Campaign Atlas**:
   - Multi-layered regional and continental atlas with interactive timeline pins, territory control overlays, and collaborative player journal entries linked to redstring lore graphs.

## What this does not do

- It does not require players to own a 3D printer; all digital 3D models and letters are fully inspectable directly in browser canvas components.
- It does not overwrite the DM's secret world lore without explicit SpiceDB Zanzibar permission checks.

## Checkable Outcomes

1. Generative handout pipeline produces styled, breakable wax-sealed letters within 5 seconds of prompt dispatch.
2. 3D relic inspector renders interactive GLTF/WebGL meshes maintaining 60fps on modern web browsers.
3. Tiled PDF generator produces correctly scaled 1-inch grid printable documents matching battlemap pixel dimensions without scaling distortion.
4. Procedural STL generator outputs valid watertight triangle meshes ready for 3D slicing software without manifold errors.

## Linked User Stories
- [`US-0045: Generative In-World Handouts, Wax Seals and 3D Relic Inspector`](../../user_stories/accepted/us-0045-generative-in-world-handouts-and-relic-inspector.md)
- [`US-0049: Printable Tabletop Forge: Grid-Calibrated PDFs, Standees and 3D STL Tokens`](../../user_stories/accepted/us-0049-printable-tabletop-forge-and-stl-tokens.md)
- [`US-0050: Collaborative Campaign Atlas and Multi-Layered Living Codex`](../../user_stories/accepted/us-0050-collaborative-campaign-atlas-and-living-codex.md)

## Implementing Backlog Tasks
- [`TASK-0101: Generative Diegetic Handouts, Wax Seals & 3D Relic Inspector`](../../backlog/refined/0101-diegetic-handouts-and-relic-inspector-bc.md)
- [`TASK-0105: Printable Tabletop Forge: Grid-Calibrated PDFs, Standees & 3D STL Tokens`](../../backlog/refined/0105-printable-tabletop-forge-and-stl-tokens.md)
- [`TASK-0106: Collaborative Campaign World Atlas & Living Party Codex`](../../backlog/proposed/0106-collaborative-campaign-atlas-and-codex-bc.md)
