# How-To: Charter Cross-Campaign Settlements & Communal Havens

This guide explains how to establish persistent multi-campaign settlements, outposts, and sanctums across shared West Marches frontier regions with SpiceDB Zanzibar fine-grained authorization (TASK-0164 / PRD-0018 / US-0058 / ADR-0001 / ADR-0006 / ADR-0011).

---

## 1. Overview

In shared frontier campaigns, adventuring parties liberate ancient ruins or construct frontier redoubts that serve as shared safe havens. The Settlement and Haven Registry in `services/game_session/` persists these outposts as event-sourced aggregates, allowing multiple distinct campaigns exploring the same shared world to discover, co-upgrade, and shelter within communal strongholds.

---

## 2. Chartering a Frontier Haven

Adventuring parties or guild officers charter a new settlement within a registered shared world:

```bash
curl -X POST http://localhost:8004/settlements \
  -H "Content-Type: application/json" \
  -H "x-user-id: ranger_lyra" \
  -d '{
    "name": "Haven of the Silver Stag",
    "shared_world_id": "b17900f3-6a05-498d-8707-4ffdd810a7ba",
    "settlement_type": "haven",
    "region": "The Deep Woods",
    "coordinates": {"x": 120.5, "y": 340.2},
    "founded_by_campaign_id": "c1a2b3c4-d5e6-7f8a-9b0c-1d2e3f4a5b6c",
    "defense_rating": 12,
    "facilities": {
      "workshop": 1,
      "sanctum": 1,
      "fortifications": 1,
      "watchtower": 1
    },
    "metadata": {
      "biome": "ancient_forest",
      "water_source": "crystal_spring"
    }
  }'
```

Response:
```json
{
  "settlement_id": "8d3e1a90-410a-49bf-9dfb-12d4a2503289",
  "name": "Haven of the Silver Stag",
  "settlement_type": "haven",
  "region": "The Deep Woods",
  "level": 1,
  "defense_rating": 12,
  "facilities": {
    "workshop": 1,
    "sanctum": 1,
    "fortifications": 1,
    "watchtower": 1
  },
  "contributing_campaigns": ["c1a2b3c4-d5e6-7f8a-9b0c-1d2e3f4a5b6c"],
  "active_boons": {
    "sanctum": "Sanctuary Rest: Advantage on death saves and bonus hit dice on campfire rest.",
    "workshop": "Mastercraft: Reagent crafting costs reduced by 25% for visiting parties."
  }
}
```

This publishes `SettlementCharteredEvent` onto Redis Stream `runefoble.events.west_marches` and registers SpiceDB relationships for the founder, shared world, and discovering campaign.

---

## 3. Querying Haven Status

Visiting parties query the haven's facility tiers, defense rating, and active perks:

```bash
curl -X GET http://localhost:8004/settlements/8d3e1a90-410a-49bf-9dfb-12d4a2503289 \
  -H "x-user-id: paladin_gawain"
```

Both direct routes (`/settlements/{id}`) and API v1 aliases (`/api/v1/settlements/{id}`) are supported.

---

## 4. Cross-Campaign Co-Upgrading

Other adventuring parties registered in the same shared world can contribute gold and gathered reagents to upgrade communal facilities:

```bash
curl -X POST http://localhost:8004/settlements/8d3e1a90-410a-49bf-9dfb-12d4a2503289/upgrade \
  -H "Content-Type: application/json" \
  -H "x-user-id: paladin_gawain" \
  -d '{
    "facility_id": "workshop",
    "contributing_campaign_id": "d2b3c4d5-e6f7-8a9b-0c1d-2e3f4a5b6c7d",
    "gold_spent": 200,
    "materials_spent": {
      "iron_ingots": 10,
      "mithril": 2
    }
  }'
```

Key facility tiers:
- **`workshop`**: Tier 1 (Field Forge) -> Tier 2 (Master Guildhall) -> Tier 3 (Arcane Crucible).
- **`sanctum`**: Tier 1 (Resting Shrine) -> Tier 2 (Hallowed Chapel) -> Tier 3 (Ascendant Grove).
- **`fortifications`**: Tier 1 (Wooden Palisades) -> Tier 2 (Stone Ramparts) -> Tier 3 (Adamantine Citadel). Upgrading fortifications permanently increases settlement defense rating (+5 per tier).
- **`watchtower`**: Tier 1 (Scout Perch) -> Tier 2 (Signal Spire) -> Tier 3 (Celestial Beacon).

Emits `SettlementUpgradedEvent` and automatically records the contributing party's discovery relationship in SpiceDB Zanzibar.

---

## 5. Claiming Sanctum Resting Boons

Adventuring parties sheltering within a haven claim sanctum rest perks before setting out on dangerous frontier journeys:

```bash
curl -X POST http://localhost:8004/settlements/8d3e1a90-410a-49bf-9dfb-12d4a2503289/claim-boon \
  -H "Content-Type: application/json" \
  -H "x-user-id: paladin_gawain" \
  -d '{
    "campaign_id": "d2b3c4d5-e6f7-8a9b-0c1d-2e3f4a5b6c7d",
    "character_id": "char_998877",
    "facility_id": "sanctum"
  }'
```

Emits `SettlementRestBoonClaimedEvent` and activates resting perks in the settlement state.

---

## 6. SpiceDB Zanzibar Multi-Tenancy Scoping

Settlements enforce strict Zanzibar relationships defined in `libs/runefoble_auth/schema/runefoble.zed`:

```zed
definition settlement {
    relation shared_world: shared_world
    relation founder: user
    relation discovering_campaign: campaign
    relation guild_officer: user

    permission view = founder + guild_officer + discovering_campaign->view + shared_world->view
    permission upgrade = founder + guild_officer + discovering_campaign->play + shared_world->trade
    permission use = founder + guild_officer + discovering_campaign->play + shared_world->discover
    permission manage = founder + guild_officer + shared_world->manage
}
```

- Any adventuring party linked to the `shared_world` inherits `view`, `upgrade`, and `use` access.
- Non-participating outsider subjects are denied with `403 Forbidden`.

---

## 7. Blackbox Testing

Run the frontdoor blackbox test suite:

```bash
uv run pytest tests/test_blackbox_settlements/
```
