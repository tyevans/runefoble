# How to Forge Print-Ready Battlemaps, Papercraft Standees & 3D STL Tokens

This guide explains how to use the Printable Tabletop Forge in `services/asset_forge` to export multi-page print-ready PDFs calibrated to exact 1-inch tabletop grids, foldable papercraft standee sheets, and 3D printable watertight STL miniature bases.

## Overview

Runefoble bridges digital virtual tabletop play with in-person physical gaming sessions. The Printable Tabletop Forge enables Game Masters and worldbuilders to export physical tabletop props directly from session assets:
1. **Multi-Page Grid-Calibrated PDFs**: Slices high-resolution battlemaps across standard Letter and A4 pages with exact 1-inch (72pt) grid squares, margin cut lines, and alignment crosshairs at 300 DPI.
2. **Foldable Papercraft Standees**: Generates print-and-cut miniature sheets featuring front portraits, mirrored back artwork, nameplates, HP tracking slots, and foldable base tabs.
3. **Watertight 3D Printable STL Tokens**: Procedurally generates 2-manifold binary or ASCII STL meshes for 28mm (medium) and 50mm (large) miniature bases with snap-in status condition clips (Poisoned, Stunned, Blessed, Blinded).

---

## 1. Exporting Multi-Page 1-Inch Grid Battlemaps

To export a tactical battlemap as a multi-page PDF calibrated to 1-inch physical squares:

### Endpoint
`POST /assets/print-pdf` (or `POST /api/v1/forge/print-pdf`)

### Request Payload (`PrintPdfRequest`)
```json
{
  "prompt": "Subterranean dwarven forge with molten canals",
  "width_cells": 16,
  "height_cells": 16,
  "page_size": "letter",
  "theme": "dwarven_forge",
  "title": "Molten Caverns",
  "format": "binary"
}
```

### Response
- **Binary Stream** (`format: "binary"`, default):
  Returns `Content-Type: application/pdf` with `Content-Disposition: attachment; filename="battlemap-...pdf"`.
  - Header `X-Page-Count`: Total number of tiled sheets.
  - Header `X-Grid-Scale`: `1-inch`.
  - Header `X-Asset-Id`: Unique asset identifier in Silo S3.
- **JSON Metadata** (`format: "json"`):
  Returns a `PrintPdfResponse` containing `asset_id`, `download_url`, `total_pages`, `rows`, `cols`, and `grid_calibration`.

### Grid Alignment & Cut Marks
Each printed sheet includes:
- **Exact 72pt (1.0 inch) Grid**: Maps directly to standard 1-inch miniature bases.
- **Dashed Margin Cut Lines**: Slicing boundaries indicating exact trimming lines.
- **Corner Alignment Crosshairs**: Center alignment marks allowing seamless joining of adjacent sheets.
- **Header Banner**: Page numbering, coordinate grid (Col C, Row R), and calibration confirmation.

---

## 2. Generating Foldable Papercraft Standees

To generate a printable sheet of foldable paper miniatures:

### Endpoint
`POST /assets/standees` (or `POST /api/v1/forge/standees`)

### Request Payload (`StandeesRequest`)
```json
{
  "sheet_title": "Goblin Ambush Pack",
  "standees": [
    { "name": "Goblin Scout", "type": "monster", "hp": 7, "color": "#e76f51" },
    { "name": "Goblin Boss", "type": "monster", "hp": 21, "color": "#d62828" },
    { "name": "Valeros Fighter", "type": "pc", "hp": 28, "color": "#2a9d8f" }
  ],
  "page_size": "letter",
  "format": "binary"
}
```

### Physical Assembly
1. **Cut**: Cut along the solid outer border of each standee.
2. **Fold Apex**: Score and fold along the dashed centerline between front and back faces.
3. **Fold Base Tabs**: Fold the top and bottom base tabs outward (or insert into plastic miniature clips).

---

## 3. Generating 3D Printable STL Miniature Bases

To generate watertight STL meshes for physical 3D printers and slicers:

### Endpoint
`POST /assets/stl-token` (or `POST /api/v1/forge/stl-token`)

### Request Payload (`StlTokenRequest`)
```json
{
  "diameter_mm": 28.0,
  "height_mm": 3.5,
  "num_slots": 4,
  "slot_depth_mm": 1.5,
  "condition_label": "Poisoned",
  "binary": true,
  "format": "binary"
}
```

### Mesh Guarantees & Slicer Compatibility
- **2-Manifold Watertightness**: Every triangle edge is shared by exactly two triangles with outward-pointing surface normals.
- **Euler-Poincaré Invariant**: $V - E + F = 2$ for standard closed sphere topology (zero holes or self-intersections).
- **Snap-In Status Clip Slots**: 4 recessed keyway notches spaced evenly around the perimeter for snapping colored condition clips (e.g. Poisoned, Stunned).
- **Format**: Standard 80-byte header binary STL or human-readable ASCII STL.

---

## 4. Frontend Component (`<runefoble-print-forge>`)

The microfrontend is exposed in `services/asset_forge/ui/` and advertised via `/ui/manifest`:

```html
<runefoble-print-forge
  campaignId="camp-123"
  activeTab="tiled-map"
></runefoble-print-forge>
```

### Dispatched Events
- `export-print-pdf`: Dispatched when the user triggers a multi-page PDF export.
- `export-standees`: Dispatched when exporting papercraft standees.
- `export-stl-token`: Dispatched when generating 3D STL meshes.
