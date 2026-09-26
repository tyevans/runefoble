# How-To: Forge Procedural Battlemaps & Token Assets

This guide explains how to generate tactical battlemaps with pre-calculated wall collisions and hazard grids, synthesize circular character and monster tokens with alpha transparency, and project spatial geometry directly into `board_state`.

---

## 1. Procedural Battlemap Generation

To synthesize a tactical grid battlemap from natural language descriptions:

```bash
curl -X POST http://localhost:8008/api/v1/forge/battlemap \
  -H "Content-Type: application/json" \
  -H "X-User-Id: dm-evelyn" \
  -d '{
    "prompt": "Subterranean dwarven forge with lava canals and broken anvil statues",
    "width_cells": 20,
    "height_cells": 20,
    "cell_size_px": 64,
    "wall_density": 0.25,
    "hazard_density": 0.15
  }'
```

### Response
```json
{
  "asset_id": "map-7f89ab12cd34",
  "image_url": "http://silo:9000/runefoble-assets/battlemaps/map-7f89ab12cd34.png?expires=3600",
  "download_url": "http://silo:9000/runefoble-assets/battlemaps/map-7f89ab12cd34.png?expires=3600",
  "width_cells": 20,
  "height_cells": 20,
  "cell_size_px": 64,
  "theme": "dwarven_forge",
  "wall_segments": [
    { "x1": 0, "y1": 0, "x2": 20, "y2": 0, "is_door": false, "wall_type": "perimeter" },
    { "x1": 10, "y1": 1, "x2": 10, "y2": 9, "is_door": false, "wall_type": "stone" }
  ],
  "hazard_cells": [
    { "x": 15, "y": 4, "hazard_type": "lava", "damage_dice": "2d10", "terrain_type": "difficult" }
  ],
  "doors": [
    { "x1": 10, "y1": 10, "x2": 11, "y2": 10, "state": "closed" }
  ],
  "board_geometry_payload": {
    "terrain_mutations": [
      { "x": 15, "y": 4, "elevation": 0, "terrain_type": "difficult", "hazard": "lava", "damage_dice": "2d10" }
    ],
    "obstacle_tokens": [
      { "name": "Obstacle Wall (14,4)", "token_type": "obstacle", "x": 14, "y": 4, "hp": null, "is_friendly": false }
    ],
    "wall_segments": [...],
    "doors": [...]
  },
  "status": "forged"
}
```

---

## 2. Character & Monster Token Portrait Generation

To synthesize a circular token with transparent background for player characters, NPCs, or monsters:

```bash
curl -X POST http://localhost:8008/api/v1/forge/token \
  -H "Content-Type: application/json" \
  -H "X-User-Id: player-marcus" \
  -d '{
    "token_name": "Thorin Ironbreaker",
    "prompt": "Dwarven paladin with glowing runic warhammer",
    "token_type": "pc",
    "size_px": 256,
    "crop_style": "circular",
    "border_color": "#e63946",
    "border_width": 8,
    "transparent_background": true
  }'
```

### Response
```json
{
  "asset_id": "tok-9c8e23f0a12b",
  "image_url": "http://silo:9000/runefoble-assets/tokens/tok-9c8e23f0a12b.png?expires=3600",
  "download_url": "http://silo:9000/runefoble-assets/tokens/tok-9c8e23f0a12b.png?expires=3600",
  "token_name": "Thorin Ironbreaker",
  "token_type": "pc",
  "crop_style": "circular",
  "size_px": 256,
  "has_transparency": true,
  "status": "forged"
}
```

---

## 3. Projecting Geometry to `board_state`

The `board_geometry_payload` returned by the battlemap generator maps directly to `board_state` REST endpoints:

1. **Hazard Terrain**: Push each entry in `terrain_mutations` to `POST /api/v1/boards/{session_id}/terrain`.
2. **Solid Obstacles**: Post each item in `obstacle_tokens` to `POST /api/v1/boards/{session_id}/tokens`.
3. **Map Background**: Load the `download_url` into `<runefoble-board>` or `<runefoble-map-uploader>`.

---

## 4. SpiceDB Zanzibar Campaign Access Control

When `campaign_id` is supplied in the request body, the service validates that the authenticated caller holds `play` or `run_session` permissions on the campaign object in SpiceDB. Non-members receive a `403 Forbidden` rejection.
