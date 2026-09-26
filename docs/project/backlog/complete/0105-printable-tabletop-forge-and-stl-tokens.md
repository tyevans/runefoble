---
id: '0105'
title: 'Printable Tabletop Forge: Grid-Calibrated PDFs, Standees & 3D STL Tokens'
status: Complete
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
governing_prds:
- PRD-0015
governing_stories:
- US-0049
pr_url: https://github.com/tyevans/runefoble/pull/122
---
# TASK-0105: Printable Tabletop Forge: Grid-Calibrated PDFs, Standees & 3D STL Tokens

## Status
Refined

## Summary
Expand `services/asset_forge` to export multi-page print-ready PDFs calibrated to exact 1-inch tabletop grids, foldable papercraft standees, and watertight 3D-printable STL token rings.

## Problem Statement
Bridging digital session assets with in-person physical games is currently arduous (PRD-0015, US-0049). Hybrid crafters like Rowan need instant, perfectly scaled multi-page PDFs to print on standard home printers, along with 3D printable condition accessories.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Domain logic in `services/asset_forge`.
- **ADR-0005: Kubernetes-First Infrastructure with Helm and Kind**: Silo S3 presigned asset storage.
- **ADR-0010: OpenTelemetry Distributed Tracing & Metrics**: Trace calibration rendering.
- **ADR-0013: Microfrontend Architecture and Service Component Vendoring**: Lit Web Component `<runefoble-print-forge>` in `services/asset_forge/ui/src/`.

## Product & User Story References
- **Product Requirement**: [`prd-0015-generative-handouts-relic-inspector-and-printable-forge.md`](../../product/accepted/prd-0015-generative-handouts-relic-inspector-and-printable-forge.md)
- **User Story**: [`us-0049-printable-tabletop-forge-and-stl-tokens.md`](../../user_stories/accepted/us-0049-printable-tabletop-forge-and-stl-tokens.md)

## Detailed Specification & Implementation Plan
1. **Multi-Page Tiled PDF Generator (`services/asset_forge/src/asset_forge/pdf_tiler.py`)**:
   - Vector/raster PDF generator slicing high-resolution maps across standard Letter/A4 pages with alignment crosshairs and margin cuts at 300 DPI (< 160 lines).
2. **Papercraft Standee Formatter (`services/asset_forge/src/asset_forge/standees.py`)**:
   - Generates folding paper miniature sheets with mirrored front/back artwork, nameplates, and base tabs (< 140 lines).
3. **Procedural 3D STL Token Generator (`services/asset_forge/src/asset_forge/stl_generator.py`)**:
   - Generates watertight binary/ASCII STL meshes for 28mm/50mm miniature bases with snap-in status condition clips (< 150 lines).
4. **Microfrontend Components & Storybook (`services/asset_forge/ui/src/`)**:
   - Web component `<runefoble-print-forge>` in Lit with print previews and SVG/STL download triggers.
5. **Frontdoor Blackbox Verification**:
   - Blackbox test suite validating PDF geometry scaling, page tiling dimensions, and STL mesh validity.

## INVEST Criteria Evaluation
- **Independent (I)**: Generates static physical formats without touching live active grid simulation.
- **Negotiable (N)**: STL mesh polygon density and standard paper sheet layouts.
- **Valuable (V)**: Bridges virtual play to physical tabletop sessions with zero friction.
- **Estimable (E)**: Pure geometry math and PDF document generation.
- **Small (S)**: Partitioned into focused generators strictly under 200 lines each.
- **Testable (T)**: Frontdoor API routes returning binary PDFs and STLs validated for headers and watertight meshes.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Microfrontend Vendoring**:
   - `<runefoble-print-forge>` built and vendored in `services/asset_forge/ui/` with `/ui/manifest`.
2. **Strict Line Limit**:
   - All created files strictly under 300 lines in compliance with Hard Invariant 6 (< 500 lines).
3. **Frontdoor Test Verification**:
   - All scenarios verified through public HTTP routes (`POST /assets/print-pdf`, `POST /assets/stl-token`).
4. **Documentation Integrity**:
   - Diataxis how-to guide authored and documented in `docs/how-to/`.
