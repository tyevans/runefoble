# How-To: Interact with Campaign World Atlas & Collaborative Party Codex

This guide explains how to navigate the interactive multi-layered world atlas engine, project coordinates across deep-zoom layers (`continental`, `regional`, `municipal`), define geopolitical territory boundaries with contested alerts, filter historical milestones by era, and collaborate on party codex entries under SpiceDB Zanzibar authorization.

---

## 1. Deep-Zoom Atlas Navigation & Layer Projections

The world atlas engine supports three primary hierarchical zoom scales:
- **Continental (1x scale)**: Macro-level geopolitical continents, empires, and realm boundaries.
- **Regional (4x scale)**: Provinces, baronies, mountain passes, and regional trade routes.
- **Municipal (16x scale)**: Town districts, fortress wards, and municipal layout points.

### Querying the Atlas
```bash
curl -X GET "http://localhost:8006/api/v1/campaigns/{campaign_id}/atlas?layer=continental&era=Session%2012" \
  -H "x-user-id: rowan_chronicler"
```

The response includes:
- `active_layers`: Visibility map for continental, regional, municipal, and contested boundary layers.
- `current_layer`: The requested zoom scope.
- `pins`: Milestone pins filtered by the active era and layer.
- `territories`: Geopolitical boundary polygons.
- `contested_zones`: Disputed border highlights with alert cues.
- `layer_extent`: Calculated spatial scale extent for canvas coordinate transformation.

---

## 2. Defining Geopolitical Boundaries & Contested Alerts

Define territory polygons and assign faction ownership:

```bash
curl -X POST "http://localhost:8006/api/v1/campaigns/{campaign_id}/atlas/territories" \
  -H "Content-Type: application/json" \
  -H "x-user-id: rowan_chronicler" \
  -d '{
    "name": "Silverkeep Garrison",
    "layer": "continental",
    "polygon_coordinates": [[100.0, 100.0], [300.0, 100.0], [300.0, 300.0], [100.0, 300.0]],
    "owner_faction": "Silverguard Alliance",
    "is_contested": true,
    "era": "Session 12: Liberation",
    "metadata": {"banner_color": "#4361ee"}
  }'
```

When `is_contested` is `true`, the atlas engine automatically flags the borderlands as a contested zone with dashed red perimeter styling and emits an `AtlasTerritoryUpdated` domain event.

---

## 3. Placing Milestone Pins with Automated Territory Detection

Place a geotagged campaign milestone pin:

```bash
curl -X POST "http://localhost:8006/api/v1/campaigns/{campaign_id}/atlas/pins" \
  -H "Content-Type: application/json" \
  -H "x-user-id: rowan_chronicler" \
  -d '{
    "title": "Silverkeep Garrison Liberation",
    "coordinates": {"x": 200.0, "y": 200.0},
    "layer": "continental",
    "description": "Party liberated the garrison from the shadow legion.",
    "era": "Session 12: Liberation",
    "session_id": "session-12",
    "linked_entity_ids": ["entity-silverguard"]
  }'
```

The engine applies ray-casting point-in-polygon containment against known territories, automatically annotating the pin metadata with its containing realm (`territory_id`, `territory_name`, and `territory_faction`), and emits `AtlasPinCreated`.

---

## 4. Collaborative Party Codex & SpiceDB Zanzibar Access Control

The Living Party Codex stores markdown lore notes and chronicles with automated entity cross-referencing against the campaign's `redstring` knowledge graph.

### Publishing a Codex Entry
```bash
curl -X POST "http://localhost:8006/api/v1/campaigns/{campaign_id}/codex/entries" \
  -H "Content-Type: application/json" \
  -H "x-user-id: rowan_chronicler" \
  -d '{
    "title": "Secret Hypothesis on the Cabal",
    "content": "I suspect the Order of the Obsidian Veil is tunneling into Silverkeep Garrison.",
    "privacy": "private",
    "era": "Session 12",
    "tags": ["theory", "veil"]
  }'
```

### Privacy & Authorization Matrix

| Privacy Status | SpiceDB Zanzibar Relations | Accessible By |
|---|---|---|
| `private` | `codex_entry#author`, `codex_entry#editor` | Author only (other users receive HTTP 403 Forbidden) |
| `party_shared` | `codex_entry#party_shared@campaign#play` | Campaign players, DMs, GMs, and owner |
| `public` | `codex_entry#public@campaign#view` | All campaign members and spectators |

### Sharing with Party
To reveal a private theory to the party:
```bash
curl -X PATCH "http://localhost:8006/api/v1/campaigns/{campaign_id}/codex/entries/{entry_id}" \
  -H "Content-Type: application/json" \
  -H "x-user-id: rowan_chronicler" \
  -d '{"privacy": "party_shared"}'
```

All party players can now view the illuminated markdown body with inline hyperlinks pointing to linked `redstring` NPC and location entities.

---

## 5. Microfrontend Custom Element `<runefoble-campaign-atlas>`

Embed the interactive atlas and codex directly in frontend applications:

```html
<runefoble-campaign-atlas
  campaignId="camp-123"
  activeLayer="continental"
  .territories=${territoriesList}
  .pins=${pinsList}
  .codexEntries=${codexEntriesList}
  .isDM=${true}
></runefoble-campaign-atlas>
```

### Emitted Custom Events
- `pin-selected`: Triggered when a pin marker is clicked (`detail.pin`).
- `pin-create-requested`: Triggered when an empty canvas location is clicked (`detail.coordinates`, `detail.layer`).
- `layer-change`: Triggered when the layer zoom mode is toggled (`detail.layer`).

### Modular Subview Architecture
Per ADR-0004 and Hard Invariant 6, `<runefoble-campaign-atlas>` decomposes its presentation sub-components into modular Lit template functions located under `services/campaign_lore/ui/src/atlas/`:
- **Territory Renderer (`territory-renderer.template.ts`)**: SVG polygon generation for geopolitical borders, contested territory cross-hatching, and faction banner color fills.
- **Pins Layer (`pins-layer.template.ts`)**: Milestone pins, chronological era timeline filtering, and canvas click coordinate mapping.
- **Codex Sidebar (`codex-sidebar.template.ts`)**: Slide-out living party codex notes, illuminated typography, and linked entity chips.

