# How-To: Interact with Campaign World Atlas & Collaborative Party Codex

This guide explains how to navigate the interactive multi-layered world atlas engine, project coordinates across deep-zoom layers (`continental`, `regional`, `municipal`), define geopolitical territory boundaries with contested alerts, filter historical milestones by era, and collaborate on party codex entries under SpiceDB Zanzibar authorization.

---

> **Routing.** Clients call the gateway on port `8000`, not `campaign_lore`. The gateway routes `GET` for the atlas and the codex, and `POST` for atlas pins and codex entries (`play` permission). The owner checks the permission. The gateway does not yet route `POST` for atlas territories or `PATCH` for codex entries. Those calls fail through the gateway until the routes are added. Defect: the gateway route gap is not yet tasked.

## 1. Deep-Zoom Atlas Navigation & Layer Projections

The world atlas engine supports three primary hierarchical zoom scales:
- **Continental (1x scale)**: Macro-level geopolitical continents, empires, and realm boundaries.
- **Regional (4x scale)**: Provinces, baronies, mountain passes, and regional trade routes.
- **Municipal (16x scale)**: Town districts, fortress wards, and municipal layout points.

### Querying the Atlas
```bash
curl -X GET "http://localhost:8000/api/v1/campaigns/{campaign_id}/atlas?layer=continental&era=Session%2012" \
  -H "Authorization: Bearer $RUNEFOBLE_TOKEN"
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
curl -X POST "http://localhost:8000/api/v1/campaigns/{campaign_id}/atlas/territories" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $RUNEFOBLE_TOKEN" \
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

When `is_contested` is `true`, the atlas engine automatically flags the borderlands as a contested zone with dashed red perimeter styling and emits an `runefoble.events.lore.atlas_territory_updated` domain event.

---

## 3. Placing Milestone Pins with Automated Territory Detection

Place a geotagged campaign milestone pin:

```bash
curl -X POST "http://localhost:8000/api/v1/campaigns/{campaign_id}/atlas/pins" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $RUNEFOBLE_TOKEN" \
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

The engine applies ray-casting point-in-polygon containment against known territories, automatically annotating the pin metadata with its containing realm (`territory_id`, `territory_name`, and `territory_faction`), and emits `runefoble.events.lore.atlas_pin_created`.

Atlas permissions: viewing needs `view`. Placing a pin needs `play` (players and DMs). Layer toggles and territory updates need `run_session` (DM, GM, or owner). A spectator or an anonymous caller cannot change the atlas.

---

## 4. Collaborative Party Codex & SpiceDB Zanzibar Access Control

The Living Party Codex stores markdown lore notes and chronicles with automated entity cross-referencing against the campaign's `redstring` knowledge graph.

### Publishing a Codex Entry
```bash
curl -X POST "http://localhost:8000/api/v1/campaigns/{campaign_id}/codex/entries" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $RUNEFOBLE_TOKEN" \
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
| `private` | `codex_entry#author`, `codex_entry#editor` | Author and editors (other users receive HTTP 403 Forbidden) |
| `party_shared` | `codex_entry#party_shared@campaign` | Campaign players, DMs, GMs, and owner (`play`) |
| `public` | `codex_entry#public@campaign` | Campaign members and spectators (`view`) |

The `privacy` field accepts only `private`, `party_shared`, and `public`. Any other value returns `422`. Publishing requires the `play` permission on the campaign. An entry that belongs to another campaign returns `404` when it is read or edited through a different campaign path.

### Sharing with Party
To reveal a private theory to the party:
```bash
curl -X PATCH "http://localhost:8000/api/v1/campaigns/{campaign_id}/codex/entries/{entry_id}" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $RUNEFOBLE_TOKEN" \
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

### Live Data Source (TASK-0646)
The App Shell's Codex & Lore tab shows two sub-tabs. Each sub-tab loads its data through the gateway with the signed-in user's bearer token. The gateway forwards the verified user id to the campaign-lore service.

| Gateway route | Used by | Notes |
|---|---|---|
| `GET /api/v1/campaigns/{campaign_id}/atlas` | `<runefoble-campaign-atlas>` (`.pins`, `.territories`) | Returns the campaign-lore atlas view. |
| `GET /api/v1/campaigns/{campaign_id}/codex` | `<runefoble-campaign-codex>` (`.entries`) | Returns a list of codex entries. The shell maps `entry_id` to `id`, `content` to `text`, and `linked_entities` names to `entities`. |

An empty dataset shows the element's empty state. A failed read shows the App Shell error state with retry. The App Shell never shows sample pins or entries.

### Emitted Custom Events
- `pin-selected`: Triggered when a pin marker is clicked (`detail.pin`).
- `pin-create-requested`: Triggered when the user submits the pin form after clicking an empty canvas location (`detail.title`, `detail.coordinates`, `detail.layer`, `detail.campaignId`). The App Shell posts the pin to `POST /api/v1/campaigns/{campaign_id}/atlas/pins`, then reloads the atlas. A refused write shows `pinError` on the element and leaves the pin list unchanged.
- `codex-entry-create-requested` (`<runefoble-campaign-codex>`): Triggered when the user submits the new entry form (`detail.title`, `detail.content`, `detail.privacy`, `detail.campaignId`). The App Shell posts the entry to `POST /api/v1/campaigns/{campaign_id}/codex/entries`, then reads the codex again. A refused write shows `entryError` on the element and leaves the entry list unchanged.
- `layer-change`: Triggered when the layer zoom mode is toggled (`detail.layer`).
