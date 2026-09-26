---
id: '0049'
title: "Printable Tabletop Forge: Grid-Calibrated PDFs, Standees and 3D STL Tokens"
status: Accepted
created: 2026-09-26
persona: Rowan (The Chronicler & Worldbuilding Artisan)
feature: FEAT-MAK-01
---

# US-0049 — Printable Tabletop Forge: Grid-Calibrated PDFs, Standees and 3D STL Tokens

## User Story

**As a** hybrid tabletop crafter and worldbuilding artisan hosting in-person sessions,  
**I want** to export 1-inch grid-calibrated multi-page PDF battlemaps, printable folding papercraft miniatures, and 3D-printable STL token rings with status slots,  
**So that** digital assets created in Runefoble can seamlessly materialize into tangible physical props on our physical game table.

## Scenario 1: Multi-Page 1-Inch Grid PDF Battlemap Export
```gherkin
Given a procedural or custom battlemap has been generated in Asset Forge
When Rowan clicks "Export for Print" and selects "Standard Letter (8.5x11), 1-inch grid"
Then the forge splits the high-resolution battlemap into tiled printable pages with alignment marks and cutting guides
And generates a print-ready vector PDF download within 5 seconds
Preserving 300 DPI texture fidelity.
```

## Scenario 2: 3D Printable STL Token Ring Generation
```gherkin
Given a player character or monster with status condition slots
When Rowan requests an STL export for physical token accessories
Then the forge generates a watertight 3D mesh for a 28mm miniature base ring
Featuring snap-fit slots for colored condition clips (e.g. Poisoned, Stunned, Blessed)
And provides an immediate downloadable .STL file compatible with standard slicers.
```
