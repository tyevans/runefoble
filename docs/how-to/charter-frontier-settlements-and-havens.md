# How-To: Charter Cross-Campaign Settlements & Communal Havens

This guide explains how to establish persistent multi-campaign settlements, outposts, and sanctums across shared West Marches frontier regions with SpiceDB Zanzibar fine-grained authorization (TASK-0164 / PRD-0018 / US-0058 / ADR-0001 / ADR-0006 / ADR-0011).

---

## 1. Overview

In shared frontier campaigns, adventuring parties liberate ancient ruins or construct frontier redoubts that serve as shared safe havens. The Settlement and Haven Registry in `services/game_session/` persists these outposts as event-sourced aggregates, allowing multiple distinct campaigns exploring the same shared world to discover, co-upgrade, and shelter within communal strongholds.

---

## 2. Chartering a Frontier Haven

Adventuring parties or guild officers charter a new settlement within a registered shared world:

Each command sends a Zitadel access token for the named user. The token is held in a shell variable `TOKEN_<USER>`, for example `TOKEN_RANGER_LYRA`. Mint the token through the sign-in flow in [Authenticate Users with Zitadel OIDC and JWTs](authenticate-with-zitadel-oidc.md). Identity comes from the token only. An `x-user-id` header has no effect.

```bash
curl -X POST http://localhost:8004/settlements \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${TOKEN_RANGER_LYRA}" \
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
  -H "Authorization: Bearer ${TOKEN_PALADIN_GAWAIN}"
```

Both direct routes (`/settlements/{id}`) and API v1 aliases (`/api/v1/settlements/{id}`) are supported.

---

## 4. Cross-Campaign Co-Upgrading

Other adventuring parties registered in the same shared world can upgrade communal facilities. The request names the facility and the contributing campaign only:

```bash
curl -X POST http://localhost:8004/settlements/8d3e1a90-410a-49bf-9dfb-12d4a2503289/upgrade \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${TOKEN_PALADIN_GAWAIN}" \
  -d '{
    "facility_id": "workshop",
    "contributing_campaign_id": "d2b3c4d5-e6f7-8a9b-0c1d-2e3f4a5b6c7d"
  }'
```

The client cannot set a cost. A request that names `gold_spent` or `materials_spent` answers `422`.

Each upgrade spends the tier price from the haven treasury. The treasury holds gold (`gold_treasury`) and materials (`materials_treasury`). A shortfall answers `409` and records no event. The facility tier does not change.

### Fund the Treasury

A new haven starts with an empty treasury. A manager (`manage` permission: founder, guild officer, or shared-world manager) adds gold and materials:

```bash
curl -X POST http://localhost:8004/settlements/8d3e1a90-410a-49bf-9dfb-12d4a2503289/deposit \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${TOKEN_PALADIN_GAWAIN}" \
  -d '{"gold": 500, "materials": {"timber": 100, "stone": 100}}'
```

A deposit emits `SettlementResourcesDepositedEvent`. A deposit must add gold or materials. Negative amounts answer `400`.

### Settlement Facility Prices

Each cell gives the price to reach that tier. Tier 1 applies only when a facility starts below tier 1. The other facilities already start at tier 1.

| Facility | Tier 1 | Tier 2 | Tier 3 |
|---|---|---|---|
| `workshop` | 50 gold, 10 timber | 100 gold, 20 timber | 250 gold, 30 timber, 40 stone |
| `sanctum` | 60 gold, 10 timber | 120 gold, 20 timber | 280 gold, 30 timber, 40 stone |
| `fortifications` | 60 gold, 15 stone | 150 gold, 30 stone | 350 gold, 60 stone, 20 iron |
| `watchtower` | 40 gold, 10 timber | 90 gold, 20 timber | 220 gold, 25 timber, 30 stone |
| `trading_post` | 75 gold, 15 timber | 150 gold, 25 timber, 10 stone | 320 gold, 40 timber, 40 stone |

The prices live in `services/game_session/src/game_session/settlement/facility_prices.py`. Tier 4 is not available. A request for a tier above 3 answers `400`.

### West Marches Outpost Prices

A West Marches outpost upgrade uses `POST /api/v1/campaigns/{campaign_id}/west-marches/stronghold/upgrade`. It spends from the outpost stored resources. The `gold` key holds the stored gold. A new outpost starts with 100 gold, 20 timber, and 15 stone. An upgrade that names an unknown `outpost_id` answers `404` and changes nothing. An empty `outpost_id` names the first outpost.

| Facility | Tier 1 | Tier 2 | Tier 3 |
|---|---|---|---|
| `alchemical_workshop` | 20 gold, 3 timber | 40 gold, 8 timber | 100 gold, 20 timber, 10 stone |
| `watchtower` | 20 gold, 3 timber | 40 gold, 8 timber | 100 gold, 20 timber, 10 stone |
| `trading_post` | 25 gold, 4 timber | 50 gold, 8 timber, 4 stone | 120 gold, 20 timber, 10 stone |
| `arcane_forge` | 30 gold, 4 stone | 60 gold, 8 stone | 150 gold, 15 stone, 15 timber |
| `herbal_rack` | 20 gold, 3 timber | 40 gold, 8 timber | 100 gold, 15 timber, 8 stone |

The prices live in `services/campaign_lore/src/campaign_lore/west_marches_prices.py`. A new outpost can afford two tier-2 upgrades. A shortfall answers `409` and changes nothing.

### Fund an Outpost from a Stronghold Treasury

A contributing campaign moves gold from its stronghold treasury into an outpost store. The command is `POST /api/v1/campaigns/{campaign_id}/west-marches/stronghold/contribute` with the body `{"gold": 120, "outpost_id": ""}`. Send the body fields only. The server sets no other cost.

The contribution has two steps:

1. `campaign_lore` checks that the caller can play the frontier. It resolves the outpost. An unknown `outpost_id` answers `404` before any debit.
2. `campaign_lore` calls `game_session` at `POST /api/v1/campaigns/{campaign_id}/stronghold/treasury/contribute`. It sends the caller's bearer and the service credential. `game_session` checks `stronghold.manage` and debits the treasury. It emits `runefoble.events.downtime.stronghold_treasury_contributed`.
3. `campaign_lore` credits the outpost gold and emits `runefoble.events.west_marches.outpost_resources_contributed`.

A missing `stronghold.manage` permission answers `403`. A treasury that cannot pay answers `409`. Both refusals change no store and emit no event. An unreachable `game_session` answers `503` and credits nothing.

Key facility tiers:
- **`workshop`**: Tier 1 (Field Forge) -> Tier 2 (Master Guildhall) -> Tier 3 (Arcane Crucible).
- **`sanctum`**: Tier 1 (Resting Shrine) -> Tier 2 (Hallowed Chapel) -> Tier 3 (Ascendant Grove).
- **`fortifications`**: Tier 1 (Wooden Palisades) -> Tier 2 (Stone Ramparts) -> Tier 3 (Adamantine Citadel). Upgrading fortifications permanently increases settlement defense rating (+5 per tier).
- **`watchtower`**: Tier 1 (Scout Perch) -> Tier 2 (Signal Spire) -> Tier 3 (Celestial Beacon).

Emits `SettlementUpgradedEvent` and automatically records the contributing party's discovery relationship in SpiceDB Zanzibar. The event carries the table cost in `gold_spent` and `materials_spent`.

---

## 5. Claiming Sanctum Resting Boons

Adventuring parties sheltering within a haven claim sanctum rest perks before setting out on dangerous frontier journeys:

```bash
curl -X POST http://localhost:8004/settlements/8d3e1a90-410a-49bf-9dfb-12d4a2503289/claim-boon \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${TOKEN_PALADIN_GAWAIN}" \
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

Per ADR-0001, ADR-0005, and ADR-0013, authorization logic in `services/game_session/src/game_session/settlement/auth/` is decomposed into dedicated submodules strictly under 130 lines:
- **`tokens.py`**: Zitadel OIDC Bearer token decoding, header parsing, and dev-mode fallback.
- **`permissions.py`**: SpiceDB Zanzibar object authorization helpers for havens, establishments, and workers.
- **`relationships.py`**: Zanzibar relationship tuple writers.
- **`dependencies.py`**: FastAPI route dependency injectors (`get_current_settlement_user`, `require_haven_builder`, `require_establishment_manager`).
- **`auth/` / `__init__.py`**: Authorization package. The former `auth.py` facade is removed (TASK-0793).

---

## 7. Blackbox Testing

Run the frontdoor blackbox test suite:

```bash
uv run pytest tests/test_blackbox_settlements_integration/ tests/test_blackbox_settlements/
```

