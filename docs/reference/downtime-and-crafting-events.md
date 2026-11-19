# Reference: Downtime, Crafting & Stronghold Events

This reference details the domain events, aggregates, and REST interfaces introduced for Downtime Activities, Alchemical Crafting, and Persistent Campsite Progression (TASK-0100 / PRD-0014 / US-0044).

## Domain Events (`runefoble_events.downtime`)

All downtime events subclass `BaseRunefobleEvent` and are CloudEvents 1.0-compliant.

### 1. `runefoble.events.downtime.crafting_attempted`
- **Topic**: `runefoble.events.crafting`
- **Aggregate Type**: `Crafting`
- **Payload Fields**:
  - `character_id`: UUID — Artisan character performing the synthesis.
  - `player_id`: Optional[str] — User ID of the player or AI stand-in.
  - `campaign_id`: Optional[UUID] — Campaign context identifier.
  - `session_id`: Optional[UUID] — Active session context identifier.
  - `reagents`: List[str] — List of ingredient names placed in the crucible.
  - `catalyst`: Optional[str] — Stabilizing or amplifying catalyst used (e.g. `purified_water`, `dragon_bile`).
  - `risk_score`: Float — Volatility probability (0.0 to 1.0) computed by the risk matrix.

### 2. `runefoble.events.downtime.crafting_succeeded`
- **Topic**: `runefoble.events.crafting`
- **Aggregate Type**: `Crafting`
- **Payload Fields**:
  - `character_id`: UUID — Artisan character receiving the crafted item.
  - `recipe_name`: str — Discovered recipe title or experimental title.
  - `item_name`: str — Name of the created inventory item (e.g. `Radiant Smoke Pellet`).
  - `quantity`: int — Number of units produced (default 1).
  - `tags`: List[str] — Mechanical tags (e.g. `["consumable", "radiant", "obscurement", "aoe"]`).
  - `reagents_consumed`: List[str] — Ingredients deducted from character inventory.
  - `catalyst_consumed`: Optional[str] — Catalyst consumed in the reaction.
  - `properties`: Dict[str, Any] — Mechanical parameters (radius, duration, damage dice).

### 3. `runefoble.events.downtime.crafting_mishap_occurred`
- **Topic**: `runefoble.events.crafting`
- **Aggregate Type**: `Crafting`
- **Payload Fields**:
  - `character_id`: UUID — Character affected by the mishap.
  - `mishap_type`: str — Mishap identifier (e.g. `minor_explosion`, `caustic_fumes`, `flashbang_stun`).
  - `severity`: str — `minor`, `moderate`, or `severe`.
  - `description`: str — Descriptive narrative outcome.
  - `damage_dealt`: int — Direct damage applied to character HP.
  - `condition_inflicted`: Optional[str] — Status condition applied (e.g. `poisoned`, `blinded`).
  - `reagents_lost`: List[str] — Ruined ingredients.

### 3a. Mishap Health Events
A mishap that deals damage publishes the standard health events on the character stream (`runefoble.events.character`). The events match those of the health route.
- **`CharacterHealthChanged`** (`runefoble.events.character.health_changed`): `delta` is the negative damage. `source` is `crafting_mishap`. `current_hp` and `max_hp` are the saved values. `session_id` is the combine request session, or null.
- **`CharacterDamaged`** (event type `runefoble.events.character.damaged`): same `delta`, `current_hp`, `max_hp`, and `source`.
- **`StandInStabilized`**: published only when the damage stabilizes a stand-in at 0 HP.

These events publish after the character and the crafting history are saved. A mishap with no damage publishes no health event.

### 5. `runefoble.events.downtime.stronghold_created`
- **Topic**: `runefoble.events.stronghold`
- **Aggregate Type**: `Stronghold`
- **Payload Fields**:
  - `campaign_id`: Optional[UUID] — Campaign identifier.
  - `name`: str — Campsite/stronghold name (default `Party Campsite`).
  - `location`: str — Geographic terrain descriptor (e.g. `Wilderness`, `Highland Woods`).

### 6. `runefoble.events.downtime.stronghold_deposited`
- **Topic**: `runefoble.events.stronghold`
- **Aggregate Type**: `Stronghold`
- **Payload Fields**:
  - `campaign_id`: Optional[UUID] — Campaign identifier.
  - `gold`: int — Gold added to the treasury.
  - `materials`: Dict[str, int] — Materials added to the store.

### 7. `runefoble.events.downtime.stronghold_upgraded`
- **Topic**: `runefoble.events.stronghold`
- **Aggregate Type**: `Stronghold`
- **Payload Fields**:
  - `campaign_id`: Optional[UUID] — Campaign identifier.
  - `facility_id`: str — Upgraded facility (`watchtower`, `herbal_rack`, `arcane_forge`).
  - `new_tier`: int — Resulting facility tier (1, 2, or 3).
  - `gold_spent`: int — Gold taken from the treasury. Equals the tier table cost (TASK-0778).
  - `materials_spent`: Dict[str, int] — Resource materials taken from the store (wood, stone, flora, iron). Equals the tier table cost (TASK-0778).
  - `unlocked_boons`: List[str] — Mechanical resting bonuses unlocked for the adventuring party.

Replay note: The handler subtracts gold and materials. A `runefoble.events.downtime.stronghold_upgraded` event stored before TASK-0774 therefore replays with the corrected arithmetic. Dev campsites that were upgraded before the fix can show a negative treasury. Reset dev data to clear them.

### 8. `runefoble.events.downtime.stronghold_treasury_contributed`
- **Topic**: `runefoble.events.stronghold`
- **Aggregate Type**: `Stronghold`
- **Payload Fields**:
  - `campaign_id`: Optional[UUID] — Campaign identifier.
  - `gold`: int — Gold debited from the treasury for a frontier outpost (TASK-0795).
  - `destination_outpost_id`: str — Receiving outpost id, recorded for the audit trail. `game_session` does not read it.

The credit to the outpost store is the `runefoble.events.west_marches.outpost_resources_contributed` event in `campaign_lore` (see [Events Catalog: Platform](events-catalog-platform.md)).

---

## Public REST Endpoints

| Endpoint | Method | Service | Zanzibar Permission | Description |
|---|---|---|---|---|
| `/api/v1/crafting/recipes` | `GET` | `character_sheet` | — | Lists canonical known alchemical recipes. |
| `/api/v1/crafting/reagents` | `GET` | `character_sheet` | — | Lists available reagents, catalysts, and mishap tables. |
| `/api/v1/crafting/recipes/combine` | `POST` | `character_sheet` (gateway proxy) | `character:edit` or `campaign:play` | Transmutes crucible reagents and updates inventory. Answers `404` when the character does not exist and `503` when the event store fails. A failed request saves nothing. |
| `/api/v1/crafting/{char_id}/history` | `GET` | `character_sheet` | `character:view` | Retrieves crafting attempts and discovered recipes. Answers an empty state only when no crafting history exists. Answers `503` when the event store fails. |
| `/api/v1/sessions/{id}/rest/prompts` | `GET` | `game_session` | — | Retrieves collaborative storytelling prompts. |
| `/api/v1/sessions/{id}/rest/campfire` | `POST` | `game_session` (gateway proxy) | `campaign:play` | Executes campfire rest sequence and applies boons. Accepts a campaign session id (`session-<hex>`). The campaign link is read from SpiceDB. A session with no campaign link answers `403`. |
| `/api/v1/campaigns/{id}/stronghold` | `GET` | `game_session` (gateway proxy) | `campaign:view` | Inspects campsite facility tiers and treasury. |
| `/api/v1/campaigns/{id}/stronghold/deposit` | `POST` | `game_session` (gateway proxy) | `stronghold.manage` (DM and managers) | Adds gold and materials to the treasury and the store. Answers `400` for a negative value or an empty deposit. Answers `403` to players. |
| `/api/v1/campaigns/{id}/stronghold/upgrade` | `POST` | `game_session` (gateway proxy) | `stronghold.upgrade` (players and managers) | Upgrades a facility by one tier. Body: `facility_id` only. The tier table sets the cost. Spends gold and materials from the stores. Answers `409` on any shortfall and `422` when the body names a cost. Records no event on either refusal. |
| `/api/v1/campaigns/{id}/stronghold/boons` | `GET` | `game_session` | `campaign:view` | Queries currently active team resting boons. |
| `/api/v1/campaigns/{id}/stronghold/treasury/contribute` | `POST` | `game_session` (called by `campaign_lore`) | `stronghold.manage` | Debits the treasury for a frontier outpost. Body: `gold` (> 0), `destination_outpost_id`. Answers `409` on shortfall and records no event. Answers `403` without the manage permission. |

---

## Microfrontend Component

- **Tag**: `<runefoble-campfire-crafting>`
- **Package**: `@runefoble/game-session-ui`
- **Manifest**: Exposed via `GET /ui/manifest` on `game_session`.
- **Custom Events**:
  - `campfire-rest-requested`: Fired on campfire rest trigger (`sessionId`, `restType`, `prompt`).
  - `reagents-combined`: Fired when reagents are transmuted in the crucible.
  - `stronghold-upgrade-requested`: Fired when a facility upgrade button is pressed.

---

## Domain Submodules & Architecture

Under TASK-0153 (ADR-0003, ADR-0007, ADR-0011), the crafting domain logic within `character_sheet` is decomposed into modular submodules:

| Submodule | Path | Responsibilities |
|---|---|---|
| `recipes.py` | `services/character_sheet/src/character_sheet/crafting/recipes.py` | Reagents catalogue, catalysts catalogue, known recipes, `Recipe` model, `CraftingState`, and DC calculation (`calculate_crafting_dc`). |
| `mishaps.py` | `services/character_sheet/src/character_sheet/crafting/mishaps.py` | Volatile mishap tables, `calculate_volatile_risk`, and `MishapResolver` consequence generators. |
| `engine.py` | `services/character_sheet/src/character_sheet/crafting/engine.py` | `CraftingEngine` orchestration (proficiency bonuses, recipe evaluation, attempt resolution) and `CraftingAggregate` event-sourced aggregate. |
| `__init__.py` | `services/character_sheet/src/character_sheet/crafting/__init__.py` | Package export of `CraftingEngine`, `Recipe`, `MishapResolver`, and `CraftingAggregate`. |

