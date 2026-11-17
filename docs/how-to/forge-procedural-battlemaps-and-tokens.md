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
  "generator": "deterministic",
  "status": "forged"
}
```

The `generator` field names the layout adapter that made the map. The default is `deterministic` (see section 6).

To get a different layout for the same prompt and size, send a `seed` integer. The same prompt, seed, and size always give the same layout. When `seed` is omitted, the service derives a stable seed from the prompt and the size.

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

## Failure Behaviour

Forged assets are written to Silo before the forge responds. The service never returns a URL for bytes it did not store.

- If Silo is unreachable or returns an error status, the forge route returns `503 Service Unavailable`. The response has no `asset_id` and no `image_url`.
- If the layout generator cannot produce a layout, the route returns `503` with `{"error": "map_generation_unavailable", "generator": "<name>", "message": "..."}`. Nothing is stored.
- Retry the request after Silo recovers. A retry creates a new asset id.
- `GET /api/v1/forge/battlemap/{asset_id}` and `GET /api/v1/forge/token/{asset_id}` read the durable asset index. They return the same metadata before and after a service restart.

### Component Behaviour (`<runefoble-asset-forge>`)

- **Forge Tactical Battlemap** posts the prompt to `POST /api/v1/forge/battlemap`. The preview appears only after the route returns a successful response.
- **Forge Token Portrait** posts the name, type, and prompt to `POST /api/v1/forge/token`. The preview appears only after a successful response.
- If the route returns an error (for example, `503` when Silo is down), the component shows the `detail` text from the response in an error banner. No preview is shown.
- The `forge-battlemap` and `forge-token` events fire only after a successful response. The event detail includes the `asset` field.
- **Place Token on Tactical Board** posts the forged token to `POST /api/v1/boards/{session_id}/tokens`. Set the `sessionId` property and the column and row first. The component shows an error when no session id is set. The board route stores the token name and type. It does not store the portrait image.
- The `token-placed` event fires only after the board route accepts the token.
- The component does not project map geometry to `board_state`. No public route accepts the `board_geometry_payload`. Section 3 is a manual recipe for API clients.
- The header reads "Procedural Battlemap Forge". The component does not use a diffusion model.

## 3. Projecting Geometry to `board_state` (Manual, Not Yet a Public Route)

The `board_geometry_payload` returned by the battlemap generator maps to `board_state` REST endpoints. Client code must make these calls itself. The Asset Forge component does not make them.

1. **Hazard Terrain**: Push each entry in `terrain_mutations` to `POST /api/v1/boards/{session_id}/terrain`.
2. **Solid Obstacles**: Post each item in `obstacle_tokens` to `POST /api/v1/boards/{session_id}/tokens`.
3. **Map Background**: Load the `download_url` into `<runefoble-board>` or `<runefoble-map-uploader>`.

---

## 4. SpiceDB Zanzibar Campaign Access Control

When `campaign_id` is supplied in the request body, the service validates that the authenticated caller holds `play` or `run_session` permissions on the campaign object in SpiceDB. Non-members receive a `403 Forbidden` rejection.

---

## 5. Modular Raster Synthesis Submodules (`asset_forge.raster`)

In accordance with Hard Invariant 6 and ADR-0003/ADR-0007, raster generation is decoupled into focused submodules under `services/asset_forge/src/asset_forge/raster/`:

| Module | Responsibilities | Key Functions |
|---|---|---|
| `png_codec.py` | Low-level PNG chunk encoding (IHDR, IDAT, IEND), scanlines, and hex parsing | `encode_png_rgba`, `parse_hex_color` |
| `battlemap_raster.py` | Procedural tactical battlemap rendering, theme palettes, and grid overlays | `generate_battlemap_png` |
| `token_raster.py` | Circular token portrait generator, border rings, and alpha transparency | `generate_token_portrait_png` |
| `wardrobe_raster.py` | Deterministic placeholder wardrobe raster (flat face colour, flat attire fill). It preserves no face | `generate_wardrobe_portrait_png`, `build_attire_prompt`, `ATTIRE_PROMPTS`, `ATTIRE_PALETTES` |
| `wardrobe_generator.py` | `WardrobeGenerator` port, `WardrobePortrait`, and generator selection (`RUNEFOBLE_WARDROBE_GENERATOR`) | `WardrobeGenerator`, `build_wardrobe_generator` |
| `wardrobe_placeholder.py` | Default placeholder generator that wraps `wardrobe_raster.py` | `PlaceholderWardrobeGenerator` |

Callers import generators directly from these submodules. The package has no aggregator facade and no legacy aliases. The `asset_forge.raster` package root re-exports nothing.

---

## 6. Battlemap Layout Generator (`MapGenerator` Port)

The battlemap route gets its wall, door, hazard, and grid layout from a `MapGenerator` port (`asset_forge.map_generator`). The port takes a prompt, a width, a height, and a seed. It returns a `MapLayout`.

**The default is the deterministic generator.** The `deterministic` generator (`asset_forge.deterministic_map_generator`) does the following:

- Picks a theme and hazard type from keywords in the prompt.
- Draws a perimeter, a central divider, and a left-wing divider. Each divider has a door at a position chosen from the seeded random stream.
- Places pillars on a lattice in the right wing. Each site is an independent seeded draw against `wall_density`.
- Lays a hazard canal whose length follows `hazard_density`.

It uses no diffusion model, no GPU, and no network call. Its output is a rule-based grid, not generated imagery. The raster (PNG) is drawn from that grid by `asset_forge.raster`.

**A configured provider can replace it.** Select the generator with the `RUNEFOBLE_ASSET_FORGE_MAP_GENERATOR` environment variable. The default is `deterministic`, which is the only supported value in this release. A provider adapter must implement `MapGenerator`. It must raise `EngineUnavailableError` with `engine_field="generator"` when it cannot produce a layout. See [Add a Settings-Selected Engine Port Adapter](add-an-engine-port-adapter.md). The route then returns the `503` body shown in section "Failure Behaviour".

| Environment variable | Default | Meaning |
|---|---|---|
| `RUNEFOBLE_ASSET_FORGE_MAP_GENERATOR` | `deterministic` | Layout adapter. `deterministic` is the only supported value. |

Blackbox tests inject a fixed generator (`tests/helpers/fixture_map_generator.py`) through `set_map_generator` at the composition root. They check that the route uses the port, names the generator in the response, and returns `503` with no stored asset when the generator is unavailable. See `tests/test_blackbox_asset_forge_map_generator.py`.
