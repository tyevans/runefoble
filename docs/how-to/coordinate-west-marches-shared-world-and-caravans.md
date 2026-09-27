# How-To: Coordinate West Marches Shared Persistent Worlds & Caravan Trade

This guide explains how to establish shared West Marches frontiers, synchronize discovery logs across distinct adventuring campaigns, dispatch trade caravans between regional outposts, and enforce multi-tenancy isolation using SpiceDB Zanzibar (TASK-0127 / PRD-0007 / US-0058 / ADR-0001 / ADR-0006 / ADR-0011).

---

## 1. Establishing a West Marches Shared Frontier

A West Marches campaign structure allows multiple adventuring parties to explore the same persistent frontier region, share map pins, trade resources, and build communal settlements.

### Step 1: Create the Shared World

Guild officers establish the shared frontier world via `POST /api/v1/shared-worlds`:

```bash
curl -X POST http://localhost:8004/api/v1/shared-worlds \
  -H "Content-Type: application/json" \
  -H "x-user-id: rowan_officer" \
  -d '{
    "name": "The Sunken Marches",
    "frontier_region": "The Shadowed Fenlands",
    "description": "A vast, dangerous marshland explored by multiple mercenary guilds."
  }'
```

Response:
```json
{
  "shared_world_id": "b17900f3-6a05-498d-8707-4ffdd810a7ba",
  "name": "The Sunken Marches",
  "frontier_region": "The Shadowed Fenlands",
  "registered_campaigns": {},
  "discoveries": [],
  "outposts": {},
  "tavern_board": []
}
```

### Step 2: Register Participating Adventuring Campaigns

Register individual campaigns (e.g. Party Blue and Party Gold) into the shared world:

```bash
curl -X POST http://localhost:8004/api/v1/shared-worlds/b17900f3-6a05-498d-8707-4ffdd810a7ba/campaigns \
  -H "Content-Type: application/json" \
  -H "x-user-id: rowan_officer" \
  -d '{
    "campaign_id": "c1a2b3c4-d5e6-7f8a-9b0c-1d2e3f4a5b6c",
    "party_name": "Party Blue"
  }'
```

---

## 2. Cross-Campaign Discovery Synchronization

When an adventuring party maps a point of interest or dungeon, they record the milestone in the shared frontier ledger.

### Step 1: Record a Discovery Milestone

```bash
curl -X POST http://localhost:8004/api/v1/shared-worlds/b17900f3-6a05-498d-8707-4ffdd810a7ba/discoveries \
  -H "Content-Type: application/json" \
  -H "x-user-id: blue_explorer" \
  -d '{
    "name": "Sunken Crypt of Arnor",
    "discovery_type": "dungeon",
    "coordinates": {"x": 145.0, "y": 280.0},
    "discovered_by_campaign_id": "c1a2b3c4-d5e6-7f8a-9b0c-1d2e3f4a5b6c",
    "discovered_by_party_name": "Party Blue",
    "description": "Flooded ancient crypt entrance guarded by water elementals.",
    "danger_level": 4,
    "metadata": {"entrance": "submerged_tunnel", "biome": "bog"}
  }'
```

This records the waypoint on `SharedWorldAggregate` and broadcasts `CrossCampaignDiscoveryShared` onto the Redis Streams event bus (`runefoble.events.west_marches`).

### Step 2: Query Shared Discoveries

Other adventuring parties (e.g. Party Gold) query the shared discovery log:

```bash
curl -X GET http://localhost:8004/api/v1/shared-worlds/b17900f3-6a05-498d-8707-4ffdd810a7ba/discoveries \
  -H "x-user-id: gold_scout"
```

The response returns all discovered locations with discovery attribution metadata (`"discovered_by_party_name": "Party Blue"`).

---

## 3. Caravan Logistics & Regional Merchant Stock

Caravans carry gathered materials and crafted reagents between outposts, expanding merchant stock for any adventuring party visiting that settlement.

### Step 1: Establish Outposts

```bash
curl -X POST http://localhost:8004/api/v1/shared-worlds/b17900f3-6a05-498d-8707-4ffdd810a7ba/outposts \
  -H "Content-Type: application/json" \
  -H "x-user-id: blue_trader" \
  -d '{
    "name": "Highport",
    "region": "Eastern Coast",
    "contributing_campaign_id": "c1a2b3c4-d5e6-7f8a-9b0c-1d2e3f4a5b6c",
    "facilities": {"harbor": 1, "alchemical_guild": 1}
  }'
```

### Step 2: Dispatch a Caravan

```bash
curl -X POST http://localhost:8004/api/v1/shared-worlds/b17900f3-6a05-498d-8707-4ffdd810a7ba/caravans/dispatch \
  -H "Content-Type: application/json" \
  -H "x-user-id: blue_trader" \
  -d '{
    "origin_outpost": "Fort Rowan",
    "destination_outpost": "Highport",
    "cargo": {"alchemical_reagents": 10, "silver_bloom": 5},
    "dispatched_by_campaign_id": "c1a2b3c4-d5e6-7f8a-9b0c-1d2e3f4a5b6c",
    "transit_turns": 2
  }'
```

### Step 3: Complete Caravan Delivery

When the caravan reaches its destination, complete the trade:

```bash
curl -X POST http://localhost:8004/api/v1/shared-worlds/b17900f3-6a05-498d-8707-4ffdd810a7ba/caravans/caravan_1234abcd/complete \
  -H "Content-Type: application/json" \
  -H "x-user-id: blue_trader" \
  -d '{
    "unlocked_stock": {
      "elixir_of_frost_resistance": {
        "name": "Elixir of Frost Resistance",
        "price_gold": 50,
        "quantity": 6,
        "rarity": "rare"
      }
    }
  }'
```

This emits `CaravanTradeCompleted` to Redis Streams and updates Highport's regional merchant stock.

### Step 4: Access Unlocked Regional Stock

Visiting parties (e.g. Party Gold visiting Highport) inspect merchant inventory:

```bash
curl -X GET http://localhost:8004/api/v1/shared-worlds/b17900f3-6a05-498d-8707-4ffdd810a7ba/outposts/Highport/merchant-stock \
  -H "x-user-id: gold_buyer"
```

---

## 4. Communal Tavern Notice Board

Parties post bounties, warnings, and mercenary contracts to the shared tavern board:

```bash
curl -X POST http://localhost:8004/api/v1/shared-worlds/b17900f3-6a05-498d-8707-4ffdd810a7ba/tavern-board/notices \
  -H "Content-Type: application/json" \
  -H "x-user-id: blue_ranger" \
  -d '{
    "campaign_id": "c1a2b3c4-d5e6-7f8a-9b0c-1d2e3f4a5b6c",
    "author_name": "Ranger Laura",
    "title": "Bounty: Cull the Marsh Trolls",
    "content": "Four marsh trolls sighted harassing supply convoys east of the Old Bridge.",
    "notice_type": "bounty",
    "bounty_reward": 150
  }'
```

Retrieve notices:

```bash
curl -X GET http://localhost:8004/api/v1/shared-worlds/b17900f3-6a05-498d-8707-4ffdd810a7ba/tavern-board/notices \
  -H "x-user-id: gold_paladin"
```

---

## 5. SpiceDB Zanzibar Multi-Tenancy Scoping

While world geography, discoveries, and trading posts are shared across participating campaigns, private character sheets, session logs, and DM whisper notes remain strictly isolated:

```
definition shared_world {
    relation guild_officer: user
    relation participant: user
    relation campaign: campaign

    permission manage = guild_officer
    permission view = guild_officer + participant + campaign->view
    permission discover = guild_officer + participant + campaign->play
    permission trade = guild_officer + participant + campaign->play
}
```

A member of Party Gold receives `view`, `discover`, and `trade` permissions on the `shared_world`, but has no `view` or `edit` permissions on Party Blue's `character` or private `campaign` resources.

---

## 6. West Marches Shared World Atlas & Communal Stronghold Microfrontend

The `<runefoble-west-marches-atlas>` Lit Web Component (vendored in `@runefoble/campaign-lore-ui`) provides a unified, interactive collaborative cartography interface (PRD-0007 / PRD-0014 / US-0050 / US-0058 / ADR-0013).

### Component Manifest Registration

The component is advertised via the `/ui/manifest` frontdoor on `campaign_lore`:

```bash
curl http://localhost:8006/ui/manifest
```

```json
{
  "service": "campaign_lore",
  "package": "@runefoble/campaign-lore-ui",
  "version": "0.1.0",
  "components": [
    "runefoble-campaign-atlas",
    "runefoble-campaign-codex",
    "runefoble-handout-viewer",
    "runefoble-relic-inspector",
    "runefoble-west-marches-atlas"
  ]
}
```

### Embedding and Consuming in the Frontend

```html
<runefoble-west-marches-atlas
  sharedWorldId="world-fenlands-01"
  worldName="The Sunken Marches"
  frontierRegion="The Shadowed Fenlands"
  currentPartyId="camp-blue"
  currentPartyName="Party Blue"
  userRole="player"
  activeTab="map"
></runefoble-west-marches-atlas>
```

### Event Contracts

- `pin-selected`: Emitted when clicking a frontier milestone pin (`detail: { discovery, sharedWorldId }`).
- `discovery-create-requested`: Emitted when clicking coordinates on the frontier canvas (`detail: { coordinates: { x, y }, sharedWorldId }`).
- `stronghold-upgrade-requested`: Emitted when investing in a facility upgrade (`detail: { outpost_id, facility_id, new_tier, sharedWorldId }`).
- `tab-changed`: Emitted when switching between `map`, `stronghold`, `tavern`, and `expeditions` (`detail: { tab }`).

