# Reference: Downtime, Crafting & Stronghold Events

This reference details the domain events, aggregates, and REST interfaces introduced for Downtime Activities, Alchemical Crafting, and Persistent Campsite Progression (TASK-0100 / PRD-0014 / US-0044).

## Domain Events (`runefoble_events.downtime`)

All downtime events subclass `BaseRunefobleEvent` and are CloudEvents 1.0-compliant.

### 1. `CraftingAttempted`
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

### 2. `CraftingSucceeded`
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

### 3. `CraftingMishapOccurred`
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

### 4. `CampfireRestCompleted`
- **Topic**: `runefoble.events.session`
- **Aggregate Type**: `GameSession`
- **Payload Fields**:
  - `session_id`: UUID | str — Session identifier.
  - `campaign_id`: Optional[UUID] — Campaign identifier.
  - `rest_type`: str — `short` or `long`.
  - `storytelling_prompt`: str — Collaborative roleplay prompt posed to participants.
  - `boons_applied`: List[str] — All rest boons granted (including active stronghold buffs).
  - `participants_healed`: List[str] — Character names or IDs recovering HP and spell slots.

### 5. `StrongholdCreated`
- **Topic**: `runefoble.events.stronghold`
- **Aggregate Type**: `Stronghold`
- **Payload Fields**:
  - `campaign_id`: Optional[UUID] — Campaign identifier.
  - `name`: str — Campsite/stronghold name (default `Party Campsite`).
  - `location`: str — Geographic terrain descriptor (e.g. `Wilderness`, `Highland Woods`).

### 6. `StrongholdUpgraded`
- **Topic**: `runefoble.events.stronghold`
- **Aggregate Type**: `Stronghold`
- **Payload Fields**:
  - `campaign_id`: Optional[UUID] — Campaign identifier.
  - `facility_id`: str — Upgraded facility (`watchtower`, `herbal_rack`, `arcane_forge`).
  - `new_tier`: int — Resulting facility tier (1, 2, or 3).
  - `gold_spent`: int — Gold invested into construction.
  - `materials_spent`: Dict[str, int] — Resource materials consumed (wood, stone, flora, iron).
  - `unlocked_boons`: List[str] — Mechanical resting bonuses unlocked for the adventuring party.

---

## Public REST Endpoints

| Endpoint | Method | Service | Zanzibar Permission | Description |
|---|---|---|---|---|
| `/api/v1/crafting/recipes` | `GET` | `character_sheet` | — | Lists canonical known alchemical recipes. |
| `/api/v1/crafting/reagents` | `GET` | `character_sheet` | — | Lists available reagents, catalysts, and mishap tables. |
| `/api/v1/crafting/recipes/combine` | `POST` | `character_sheet` / `gateway` | `character:edit` or `campaign:play` | Transmutes crucible reagents and updates inventory. |
| `/api/v1/crafting/{char_id}/history` | `GET` | `character_sheet` | `character:view` | Retrieves crafting attempts and discovered recipes. |
| `/api/v1/sessions/{id}/rest/prompts` | `GET` | `game_session` | — | Retrieves collaborative storytelling prompts. |
| `/api/v1/sessions/{id}/rest/campfire` | `POST` | `game_session` / `gateway` | `campaign:play` | Executes campfire rest sequence and applies boons. |
| `/api/v1/campaigns/{id}/stronghold` | `GET` | `game_session` / `gateway` | `campaign:view` | Inspects campsite facility tiers and treasury. |
| `/api/v1/campaigns/{id}/stronghold/upgrade` | `POST` | `game_session` / `gateway` | `campaign:play` | Upgrades campsite facilities with gold and materials. |
| `/api/v1/campaigns/{id}/stronghold/boons` | `GET` | `game_session` | `campaign:view` | Queries currently active team resting boons. |

---

## Microfrontend Component

- **Tag**: `<runefoble-campfire-crafting>`
- **Package**: `@runefoble/game-session-ui`
- **Manifest**: Exposed via `GET /ui/manifest` on `game_session`.
- **Custom Events**:
  - `campfire-rest-requested`: Fired on campfire rest trigger (`sessionId`, `restType`, `prompt`).
  - `reagents-combined`: Fired when reagents are transmuted in the crucible.
  - `stronghold-upgrade-requested`: Fired when a facility upgrade button is pressed.
