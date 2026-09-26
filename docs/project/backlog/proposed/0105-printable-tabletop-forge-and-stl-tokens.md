---
id: '0105'
title: "Printable Tabletop Forge: Grid-Calibrated PDFs, Standees & 3D STL Tokens"
status: Proposed
created: 2026-09-26
dependencies:
- TASK-0023
- TASK-0049
governing_adrs:
- ADR-0003
- ADR-0005
- ADR-0010
- ADR-0013
target_release: 0.4.0
prd_url: docs/project/product/accepted/prd-0015-generative-handouts-relic-inspector-and-printable-forge.md
user_story: US-0049
---

# TASK-0105: Printable Tabletop Forge: Grid-Calibrated PDFs, Standees & 3D STL Tokens

## Status
Proposed

## Summary
Expand `services/asset_forge` to export multi-page print-ready PDFs calibrated to exact 1-inch tabletop grids, foldable papercraft standees, and watertight 3D-printable STL token rings.

## Problem Statement
Bridging digital session assets with in-person physical games is currently arduous (PRD-0015, US-0049). Hybrid crafters like Rowan need instant, perfectly scaled multi-page PDFs to print on standard home printers, along with 3D printable condition accessories.

## Governing Architecture & ADRs
- **ADR-0003**: UV Monorepo Workspace (`services/asset_forge`).
- **ADR-0005**: Helm deployment with Silo S3 presigned asset storage.
- **ADR-0010**: OpenTelemetry Distributed Tracing.
- **ADR-0013**: Microfrontend Architecture (`<runefoble-print-forge>`).

## Scope of Work
1. **Multi-Page Tiled PDF Generator**:
   - Vector/raster PDF generator slicing high-resolution maps across standard Letter/A4 pages with alignment crosshairs and margin cuts at 300 DPI.
2. **Papercraft Standee Formatter**:
   - Generates folding paper miniature sheets with mirrored front/back artwork, nameplates, and base tabs.
3. **Procedural 3D STL Token Generator**:
   - Generates watertight binary/ASCII STL meshes for 28mm/50mm miniature bases with snap-in status condition clips.
4. **Frontdoor Blackbox Verification**:
   - Blackbox test suite validating PDF geometry scaling, page tiling dimensions, and STL mesh validity.
